"""acquire-readonly: bounded, reviewed SELECT reads of the producer database.

Runs only in the private workspace, only with explicit activation, and only the
closed query set below. Values are validated against closed lists before they
are placed in the SQL text (the CLI client used does not bind parameters).
Every query, its digest, timing, client version, row count and the database
metadata are logged. A read that wrote, changed the database, failed, or
returned fewer rows than the independent count is rejected: it never becomes an
empty or partial export.

Counters are aggregates that may be updated while the producer is live. Only
closed past days are read, and the per-day checksums are read before and after
the extraction; any difference rejects the acquisition. This does not make the
extraction a transactional snapshot.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .common import DwrError, SITE_IDS, load_json, sha256_bytes, write_json
from .dates import Window, last_closed_day

ROLLUP_COLUMNS = (
    "event_date", "domain", "path", "category", "method", "status",
    "actor_family", "actor_name", "actor_type", "confidence", "hits",
)
TABLES_FOR_SCHEMA = (
    "governance_daily_rollups",
    "governance_artifact_registry",
    "ai_actor_classifier_versions",
    "deployment_history_evidence",
)


def _quote(value: str) -> str:
    if "'" in value or "\\" in value or "\x00" in value:
        raise DwrError("sql_literal_refused", value[:40])
    return f"'{value}'"


def _domains_sql(domains) -> str:
    for domain in domains:
        if domain not in SITE_IDS:
            raise DwrError("site_not_allowed", domain)
    return ",".join(_quote(domain) for domain in domains)


def planned_queries(window: Window, domains=SITE_IDS) -> list[dict]:
    domain_list = _domains_sql(domains)
    start, end = window.start.isoformat(), window.end_exclusive.isoformat()
    history_end = (window.end_exclusive + timedelta(days=2)).isoformat()
    queries = [{
        "query_id": "q00_schema",
        "sql": ("SELECT name, sql FROM sqlite_master WHERE type='table' AND name IN ("
                + ",".join(_quote(name) for name in TABLES_FOR_SCHEMA) + ") ORDER BY name"),
    }]
    checksum = (f"SELECT event_date, COUNT(*) AS cells, SUM(hits) AS hits FROM governance_daily_rollups "
                f"WHERE domain IN ({domain_list}) AND event_date >= {_quote(start)} "
                f"AND event_date < {_quote(end)} GROUP BY event_date ORDER BY event_date")
    queries.append({"query_id": "q01_checksum_before", "sql": checksum})
    for day in window.dates():
        queries.append({
            "query_id": f"q02_rollups_{day.isoformat()}",
            "day": day.isoformat(),
            "sql": (f"SELECT {', '.join(ROLLUP_COLUMNS)} FROM governance_daily_rollups "
                    f"WHERE domain IN ({domain_list}) AND event_date = {_quote(day.isoformat())} "
                    "ORDER BY domain, path, method, status, actor_family, actor_name, confidence"),
        })
    queries.append({
        "query_id": "q03_registry",
        "sql": (f"SELECT domain, path, category, expected, substr(first_seen, 1, 10) AS first_seen_date "
                f"FROM governance_artifact_registry WHERE domain IN ({domain_list}) ORDER BY domain, path"),
    })
    queries.append({
        "query_id": "q04_classifier_versions",
        "sql": "SELECT version, rules_sha256 FROM ai_actor_classifier_versions ORDER BY version",
    })
    queries.append({
        "query_id": "q05_deployment_history",
        "sql": (f"SELECT observed_at, first_deployed_at, history_json FROM deployment_history_evidence "
                f"WHERE observed_at >= {_quote(start)} AND observed_at < {_quote(history_end)} "
                "ORDER BY observed_at"),
    })
    queries.append({"query_id": "q06_checksum_after", "sql": checksum})
    for query in queries:
        sql = query["sql"].lstrip().upper()
        if not sql.startswith("SELECT ") or ";" in query["sql"]:
            raise DwrError("query_not_single_select", query["query_id"])
        query["sql_sha256"] = sha256_bytes(query["sql"].encode("utf-8"))
    return queries


def _run_client(config: dict, sql: str) -> tuple[list, dict, float]:
    client_dir = Path(config["client_dir"])
    npx = shutil.which("npx.cmd") or shutil.which("npx")
    if not npx:
        raise DwrError("client_unavailable", "npx")
    env = dict(os.environ)
    # The account resolved from the producer configuration always wins over an inherited value.
    env["CLOUDFLARE_ACCOUNT_ID"] = config["account_id"]
    started = time.monotonic()
    completed = subprocess.run(
        [npx, "--no-install", "wrangler", "d1", "execute", config["database_name"],
         "--remote", "--json", "--command", sql],
        cwd=client_dir, env=env, capture_output=True, text=True, encoding="utf-8",
        timeout=180, check=False,
    )
    elapsed = time.monotonic() - started
    if completed.returncode != 0:
        raise DwrError("source_unavailable", f"client exit {completed.returncode}")
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise DwrError("client_output_invalid_or_truncated", str(error)) from error
    if not isinstance(payload, list) or len(payload) != 1 or not payload[0].get("success"):
        raise DwrError("query_failed")
    result = payload[0]
    meta = result.get("meta") or {}
    if meta.get("rows_written", 0) != 0 or meta.get("changed_db", False):
        raise DwrError("read_wrote_to_database")
    return result.get("results") or [], meta, elapsed


def client_version(config: dict) -> str:
    npx = shutil.which("npx.cmd") or shutil.which("npx")
    completed = subprocess.run([npx, "--no-install", "wrangler", "--version"], cwd=config["client_dir"],
                               capture_output=True, text=True, timeout=60, check=False)
    return completed.stdout.strip().splitlines()[-1] if completed.returncode == 0 else "unknown"


def acquire(private: Path, window: Window, *, execute: bool, confirm_scope: str | None,
            now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    if window.last_included > last_closed_day(now):
        raise DwrError("window_not_closed", window.last_included.isoformat())
    queries = planned_queries(window)
    expected_scope = f"{window.start.isoformat()}..{window.end_exclusive.isoformat()}"
    if not execute:
        return {"mode": "dry_run", "scope": expected_scope, "queries": queries}
    if confirm_scope != expected_scope:
        raise DwrError("scope_confirmation_mismatch", f"expected --confirm-scope {expected_scope}")
    config = load_json(private / "lock" / "acquisition-config.json")
    for key in ("database_name", "account_id", "client_dir"):
        if not config.get(key):
            raise DwrError("acquisition_config_incomplete", key)
    acquisition_id = "acq-" + now.strftime("%Y%m%dT%H%M%SZ")
    target = private / "acquisition" / acquisition_id
    (target / "raw").mkdir(parents=True, exist_ok=False)
    log = {"acquisition_id": acquisition_id, "scope": expected_scope,
           "client": client_version(config), "started_at": now.isoformat(), "queries": []}
    results = {}
    try:
        for query in queries:
            query_started = datetime.now(timezone.utc).isoformat()
            rows, meta, elapsed = _run_client(config, query["sql"])
            raw = json.dumps(rows, ensure_ascii=False, sort_keys=True).encode("utf-8")
            (target / "raw" / f"{query['query_id']}.json").write_bytes(raw)
            results[query["query_id"]] = rows
            log["queries"].append({
                "query_id": query["query_id"], "sql": query["sql"], "sql_sha256": query["sql_sha256"],
                "started_at": query_started, "elapsed_seconds": round(elapsed, 3), "rows": len(rows),
                "result_sha256": sha256_bytes(raw),
                "meta": {key: meta.get(key) for key in ("rows_read", "rows_written", "changed_db", "duration",
                                                        "served_by_region", "served_by_primary")},
            })
    except DwrError as error:
        log["status"] = "source_unavailable" if error.code == "source_unavailable" else "validation_failed"
        log["error"] = error.code
        write_json(target / "acquisition-log.json", log)
        raise
    before = {row["event_date"]: (row["cells"], row["hits"]) for row in results["q01_checksum_before"]}
    after = {row["event_date"]: (row["cells"], row["hits"]) for row in results["q06_checksum_after"]}
    problems = []
    if before != after:
        problems.append("checksum_changed_during_extraction")
    for day in window.dates():
        key = day.isoformat()
        rows = results[f"q02_rollups_{key}"]
        if key not in before:
            problems.append(f"day_without_rows:{key}")
            continue
        cells, hits = before[key]
        if len(rows) != cells or sum(int(row["hits"]) for row in rows) != hits:
            problems.append(f"pagination_or_truncation:{key}")
    log["ended_at"] = datetime.now(timezone.utc).isoformat()
    log["checksums"] = {day: {"cells": value[0], "hits": value[1]} for day, value in sorted(before.items())}
    log["status"] = "validation_failed" if problems else "new_data"
    log["problems"] = problems
    write_json(target / "acquisition-log.json", log)
    if problems:
        raise DwrError("acquisition_rejected", ";".join(problems))
    return log

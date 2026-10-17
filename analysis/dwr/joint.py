"""Joint aggregate (private): load, validate and cross-check an accepted acquisition.

The joint rows (day x site x path x method x status x actor x tier) are checked
against the exports of the initial report: per path, per actor group, per day
and per method/status. Agreement shows that the two readings of the same
producer table are consistent; it is not an independent validation of the
collection.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from .common import ACTOR_ROLES, DwrError, HTTP_METHODS, IDENTITY_TIERS, load_json, validate_path, validate_site
from .dates import Window, parse_date
from .reconcile import AI_ROLES, PROVIDER, in_historical_scope

KEY = ("date_utc", "site_id", "path", "http_method", "http_status", "actor_family", "actor_name", "stored_identity_tier")


def load_rows(acquisition_dir: Path, window: Window) -> list[dict]:
    log = load_json(acquisition_dir / "acquisition-log.json")
    if log.get("status") != "new_data" or log.get("problems"):
        raise DwrError("acquisition_not_accepted", acquisition_dir.name)
    rows, keys = [], set()
    for day in window.dates():
        path = acquisition_dir / "raw" / f"q02_rollups_{day.isoformat()}.json"
        if not path.is_file():
            raise DwrError("source_unavailable", path.name)
        for raw in json.loads(path.read_text(encoding="utf-8")):
            if parse_date(raw["event_date"]) != day:
                raise DwrError("joint_row_outside_day", raw["event_date"])
            method = raw["method"]
            if method not in HTTP_METHODS:
                raise DwrError("http_method_unknown", str(method))
            status = int(raw["status"])
            if not 100 <= status <= 599:
                raise DwrError("http_status_unknown", str(status))
            if raw["actor_type"] not in ACTOR_ROLES:
                raise DwrError("actor_role_unknown", str(raw["actor_type"]))
            if raw["confidence"] not in IDENTITY_TIERS:
                raise DwrError("identity_tier_unknown", str(raw["confidence"]))
            hits = raw["hits"]
            if not isinstance(hits, int) or hits < 0:
                raise DwrError("count_negative_or_not_integer", repr(hits))
            row = {"date_utc": day.isoformat(), "site_id": validate_site(raw["domain"]),
                   "path": validate_path(raw["path"]), "producer_category": raw["category"],
                   "http_method": method, "http_status": status, "actor_family": raw["actor_family"],
                   "actor_name": raw["actor_name"], "actor_role": raw["actor_type"],
                   "stored_identity_tier": raw["confidence"], "request_count": hits}
            key = tuple(row[k] for k in KEY)
            if key in keys:
                raise DwrError("joint_duplicate_key", repr(key)[:120])
            keys.add(key)
            rows.append(row)
    total = sum(r["request_count"] for r in rows)
    expected = sum(v["hits"] for v in log["checksums"].values())
    if total != expected:
        raise DwrError("joint_total_differs_from_checksums", f"{total} vs {expected}")
    return sorted(rows, key=lambda r: tuple(str(r[k]) for k in KEY))


def path_counts(rows: list[dict]) -> dict[tuple, dict]:
    counts = defaultdict(lambda: {"requests": 0, "get200": 0, "head": 0, "not_modified": 0, "errors": 0,
                                  "provider_ai_get200": 0, "_days": set(), "_get_days": set(), "_provider_days": set()})
    for r in rows:
        c = counts[(r["site_id"], r["path"])]
        n = r["request_count"]
        c["requests"] += n
        c["_days"].add(r["date_utc"])
        if r["http_method"] == "GET" and r["http_status"] == 200:
            c["get200"] += n
            c["_get_days"].add(r["date_utc"])
            if r["stored_identity_tier"] == PROVIDER and r["actor_role"] in AI_ROLES:
                c["provider_ai_get200"] += n
                c["_provider_days"].add(r["date_utc"])
        if r["http_method"] == "HEAD":
            c["head"] += n
        if r["http_status"] == 304:
            c["not_modified"] += n
        if r["http_status"] >= 400:
            c["errors"] += n
    out = {}
    for key, c in counts.items():
        out[key] = {k: v for k, v in c.items() if not k.startswith("_")}
        out[key].update({"days": len(c["_days"]), "get200_days": len(c["_get_days"]),
                         "provider_ai_get200_days": len(c["_provider_days"])})
    return out


def cross_check(rows: list[dict], marginals: dict) -> dict:
    checks = []
    joint_paths = path_counts(rows)
    export_paths = {(r["site_id"], r["path"]): r for r in marginals["files"]}
    fields = ("requests", "get200", "head", "not_modified", "errors", "days", "get200_days", "provider_ai_get200")
    mismatched = [key for key in set(joint_paths) | set(export_paths)
                  if key not in joint_paths or key not in export_paths
                  or any(joint_paths[key][f] != export_paths[key][f] for f in fields)]
    checks.append({"check": "per_path_marginals", "compared": len(export_paths), "mismatches": len(mismatched)})
    groups = defaultdict(lambda: {"requests": 0, "get200": 0, "_paths": set(), "_days": set()})
    for r in rows:
        if not in_historical_scope(r):
            continue
        g = groups[(r["site_id"], r["actor_name"], r["actor_role"], r["stored_identity_tier"])]
        g["requests"] += r["request_count"]
        g["_paths"].add(r["path"])
        g["_days"].add(r["date_utc"])
        if r["http_method"] == "GET" and r["http_status"] == 200:
            g["get200"] += r["request_count"]
    export_actors = {(a["site_id"], a["actor_name"], a["actor_role"], a["stored_identity_tier"]): a for a in marginals["actors"]}
    bad_actors = [k for k in set(groups) | set(export_actors)
                  if k not in groups or k not in export_actors
                  or groups[k]["requests"] != export_actors[k]["requests"] or groups[k]["get200"] != export_actors[k]["get200"]
                  or len(groups[k]["_paths"]) != export_actors[k]["paths"] or len(groups[k]["_days"]) != export_actors[k]["days"]]
    checks.append({"check": "per_actor_group_marginals", "compared": len(export_actors), "mismatches": len(bad_actors)})
    daily = defaultdict(lambda: [0, 0, 0, 0])
    for r in rows:
        d = daily[(r["date_utc"], r["site_id"])]
        d[0] += r["request_count"]
        if in_historical_scope(r):
            d[1] += r["request_count"]
            if r["http_method"] == "GET" and r["http_status"] == 200:
                d[2] += r["request_count"]
                if r["stored_identity_tier"] == PROVIDER and r["actor_role"] in AI_ROLES:
                    d[3] += r["request_count"]
    bad_days = [row for row in marginals["daily"] if daily.get((row["date_utc"], row["site_id"])) != [
        row["all_requests"], row["governance_requests"], row["governance_get200"], row["provider_ai_get200"]]]
    checks.append({"check": "per_day_site_totals", "compared": len(marginals["daily"]), "mismatches": len(bad_days)})
    http = defaultdict(int)
    for r in rows:
        if in_historical_scope(r):
            http[(r["site_id"], r["http_method"], r["http_status"])] += r["request_count"]
    export_http = {(h["site_id"], h["http_method"], h["http_status"]): h["requests"] for h in marginals["http"]}
    bad_http = [k for k in set(http) | set(export_http) if http.get(k, 0) != export_http.get(k, 0)]
    checks.append({"check": "per_site_method_status", "compared": len(export_http), "mismatches": len(bad_http)})
    # The per-path method/status split deduced from zero mass in the export must match the joint split.
    deduced_bad = 0
    combos = defaultdict(int)
    for r in rows:
        if in_historical_scope(r):
            combos[(r["site_id"], r["path"], r["http_method"], r["http_status"])] += r["request_count"]
    for (site, path, method, status), value in combos.items():
        export = export_paths[(site, path)]
        expected = {("GET", 200): export["get200"], ("HEAD", 200): export["head"], ("GET", 304): export["not_modified"],
                    ("POST", 405): export["errors"]}.get((method, status))
        if expected is None or expected != value:
            deduced_bad += 1
    checks.append({"check": "deduced_method_status_split_confirmed", "compared": len(combos), "mismatches": deduced_bad})
    return {"nature": "two readings of the same producer table; consistency, not independent validation",
            "checks": checks, "all_consistent": all(c["mismatches"] == 0 for c in checks)}


def deployment_timeline(acquisition_dir: Path, window: Window) -> dict:
    history = json.loads((acquisition_dir / "raw" / "q05_deployment_history.json").read_text(encoding="utf-8"))
    if not history:
        return {"status": "source_unavailable", "deployments": []}
    deployments = {}
    observed = []
    for row in history:
        observed.append(row["observed_at"])
        body = json.loads(row["history_json"])
        for deployment in body.get("deployments", []):
            deployments.setdefault(deployment["deployment_id"], deployment)
    times = sorted(datetime.fromisoformat(t.replace("Z", "+00:00")) for t in observed)
    max_gap = max(((b - a).total_seconds() / 3600 for a, b in zip(times, times[1:])), default=None)
    ordered = sorted(deployments.values(), key=lambda d: d["effective_at"])
    return {"status": "observed", "observations": len(history), "first_observed_at": min(observed),
            "last_observed_at": max(observed), "max_gap_hours": round(max_gap, 1) if max_gap is not None else None,
            "deployments": [{"deployment_id": d["deployment_id"], "effective_at": d["effective_at"],
                             "versions": [{"version_id": v["version_id"], "source_commit": v["source_commit"],
                                           "percentage": v["percentage"]} for v in d["versions"]]} for d in ordered]}

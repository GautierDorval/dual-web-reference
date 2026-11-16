"""Private inputs for the calendar cursor, without registering a public edition.

The joint rows and the SQL marginals are separate reads of the same producer.
Their agreement establishes consistency, not independent measurement validity.
Missing archives and unqualified classification epochs remain explicit.
"""
from contextlib import contextmanager
from collections import defaultdict
from datetime import datetime, timezone
import os
from pathlib import Path

from . import acquire, archive, dates, joint, pipeline, qualify
from .common import DwrError, REPO_ROOT, SITE_IDS, load_json, sha256_file, write_json
from .write_guard import checked_path


def window(private):
    """Use the same pending cursor as prepare-next; never skip an old window."""
    state_path = checked_path(private, private / "preparation/status.json")
    state = load_json(state_path) if state_path.is_file() else load_json(REPO_ROOT / "data/status.json")
    base = pipeline.edition_entry(None)
    start = (state.get("pending_window_start") or state.get("last_processed_window_end_exclusive")
             or base["period_end_exclusive"])
    calendar = load_json(REPO_ROOT / "config/edition-calendar.json")
    return dates.monthly_window(dates.parse_date(start), calendar["monthly_anchor_day"])


def marginal_queries(period, domains=SITE_IDS):
    domains_sql = acquire._domains_sql(domains)
    where = (f"domain IN ({domains_sql}) AND event_date >= '{period.start}' "
             f"AND event_date < '{period.end_exclusive}'")
    scope = "path NOT IN ('/robots.txt','/.well-known/__undeclared__') AND category != 'well-known-probe'"
    get = "method='GET' AND status=200"
    head = "method='HEAD'"
    ai = "confidence='provider_origin_verified_actor' AND actor_type IN ('ai_training','ai_search','user_initiated_fetch')"
    total = lambda condition: f"SUM(CASE WHEN {condition} THEN hits ELSE 0 END)"
    return [
        {"query_id": "q07_files", "sql":
         f"SELECT domain AS site_id,path,MIN(category) AS producer_category,COUNT(DISTINCT category) AS category_count,"
         f"SUM(hits) AS requests,{total(get)} AS get200,{total(head)} AS head,"
         f"{total('status=304')} AS not_modified,{total('status>=400')} AS errors,"
         f"COUNT(DISTINCT event_date) AS days,COUNT(DISTINCT CASE WHEN {get} THEN event_date END) AS get200_days,"
         f"{total(get+' AND '+ai)} AS provider_ai_get200 FROM governance_daily_rollups WHERE {where} "
         "GROUP BY domain,path ORDER BY domain,path"},
        {"query_id": "q08_actors", "sql":
         f"SELECT domain AS site_id,actor_name,actor_type AS actor_role,confidence AS stored_identity_tier,"
         f"SUM(hits) AS requests,{total(get)} AS get200,COUNT(DISTINCT path) AS paths,COUNT(DISTINCT event_date) AS days "
         f"FROM governance_daily_rollups WHERE {where} AND {scope} "
         "GROUP BY domain,actor_name,actor_type,confidence ORDER BY domain,actor_name,actor_type,confidence"},
        {"query_id": "q09_daily", "sql":
         f"SELECT event_date AS date_utc,domain AS site_id,SUM(hits) AS all_requests,"
         f"{total(scope)} AS governance_requests,{total(scope+' AND '+get)} AS governance_get200,"
         f"{total(scope+' AND '+get+' AND '+ai)} AS provider_ai_get200 "
         f"FROM governance_daily_rollups WHERE {where} GROUP BY event_date,domain ORDER BY event_date,domain"},
        {"query_id": "q10_http", "sql":
         f"SELECT domain AS site_id,method AS http_method,status AS http_status,SUM(hits) AS requests "
         f"FROM governance_daily_rollups WHERE {where} AND {scope} "
         "GROUP BY domain,method,status ORDER BY domain,method,status"},
        {"query_id": "q11_path_http", "sql":
         f"SELECT domain AS site_id,path,method AS http_method,status AS http_status,SUM(hits) AS requests "
         f"FROM governance_daily_rollups WHERE {where} "
         "GROUP BY domain,path,method,status ORDER BY domain,path,method,status"},
    ]


@contextmanager
def input_lock(private):
    private = Path(private).absolute()
    if private.resolve() == REPO_ROOT.resolve() or private.resolve().is_relative_to(REPO_ROOT.resolve()):
        raise DwrError("private_root_inside_public_repository")
    lock = checked_path(private, private / "inputs.lock")
    private.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise DwrError("private_inputs_busy") from exc
    os.close(fd)
    try:
        yield
    finally:
        lock.unlink()


def acquire_next(private, *, execute=False, confirm_scope=None, now=None):
    period = window(private)
    if not execute:
        return acquire.acquire(private, period, execute=False, confirm_scope=None, include_marginals=True)
    calendar = load_json(REPO_ROOT / "config/edition-calendar.json")
    if not dates.consolidation_ready(period, now or datetime.now(timezone.utc), calendar["consolidation_delay_hours"]):
        raise DwrError("next_window_not_consolidated")
    with input_lock(private):
        return acquire.acquire(private, period, execute=True, confirm_scope=confirm_scope,
                               include_marginals=True, now=now)


def accepted_acquisition(private, period):
    logs = sorted(checked_path(private, private / "acquisition").glob("acq-*/acquisition-log.json"))
    matches = []
    for path in logs:
        log = load_json(checked_path(private, path))
        if log.get("status") == "new_data" and log.get("scope") == f"{period.start}..{period.end_exclusive}":
            matches.append((path, log))
    if len(matches) != 1:
        raise DwrError("next_acquisition_missing_or_ambiguous", str(len(matches)))
    path, log = matches[0]
    config_path = checked_path(private, private / "lock/acquisition-config.json")
    config = load_json(config_path)
    if log.get("source_identity") != {"account_id": config["account_id"],
                                     "database_name": config["database_name"],
                                     "config_sha256": sha256_file(config_path)}:
        raise DwrError("acquisition_source_identity_mismatch")
    plan = acquire.planned_queries(period, include_marginals=True)
    receipts = log.get("queries", [])
    if log.get("problems") or not log.get("includes_marginals") or len(receipts) != len(plan):
        raise DwrError("next_acquisition_incomplete")
    data = {}
    for expected, receipt in zip(plan, receipts):
        name = expected["query_id"]
        if any(receipt.get(key) != expected[key] for key in ("query_id", "sql", "sql_sha256")):
            raise DwrError("acquisition_query_identity_mismatch", name)
        meta = receipt.get("meta", {})
        if meta.get("rows_written") != 0 or meta.get("changed_db") is not False:
            raise DwrError("acquisition_readonly_evidence_missing", name)
        raw = checked_path(private, path.parent / "raw" / f"{name}.json")
        if sha256_file(raw) != receipt.get("result_sha256"):
            raise DwrError("acquisition_result_changed", name)
        rows = load_json(raw)
        if not isinstance(rows, list) or len(rows) != receipt.get("rows"):
            raise DwrError("acquisition_result_truncated", name)
        data[name] = rows
    before, after = data["q01_checksum_before"], data["q06_checksum_after"]
    expected_days = {day.isoformat() for day in period.dates()}
    if before != after or len(before) != period.days or {r["event_date"] for r in before} != expected_days:
        raise DwrError("acquisition_checksums_inconsistent")
    for check in before:
        rows = data["q02_rollups_" + check["event_date"]]
        if len(rows) != check["cells"] or sum(r["hits"] for r in rows) != check["hits"]:
            raise DwrError("acquisition_checksum_mismatch")
    return path.parent, log, data


def write_once(private, target, value):
    target = checked_path(private, target)
    if target.is_file():
        if load_json(target) != value:
            raise DwrError("private_input_changed_requires_revision", target.name)
        return
    write_json(target, value)


def normalize(private, *, verify_only=False):
    with input_lock(private):
        period = window(private)
        edition = period.edition_id(1)
        source = load_json(checked_path(private, private / "lock/sources-config.json"))
        acquisition, log, data = accepted_acquisition(private, period)
        rows = joint.load_rows(acquisition, period)
        if any(r["category_count"] != 1 for r in data["q07_files"]):
            raise DwrError("producer_category_changed_within_window")
        files = [{k: v for k, v in r.items() if k != "category_count"} for r in data["q07_files"]]
        seen = {(r["site_id"], r["path"]) for r in files}
        marginals = {
            "mode": "independent_sql_marginals_same_producer",
            "window": {"start_inclusive": str(period.start), "end_exclusive": str(period.end_exclusive)},
            "extracted_at": [log["started_at"], log["ended_at"]],
            "files": files, "actors": data["q08_actors"], "daily": data["q09_daily"],
            "http": data["q10_http"], "path_http": data["q11_path_http"],
            "registered_without_window_rows": [
                {"site_id": r["domain"], "path": r["path"], "producer_category": r["category"], "window_rows": 0}
                for r in data["q03_registry"] if (r["domain"], r["path"]) not in seen],
        }
        expected_daily = {(str(day), site) for day in period.dates() for site in SITE_IDS}
        if (len(marginals["daily"]) != len(expected_daily)
                or {(r["date_utc"], r["site_id"]) for r in marginals["daily"]} != expected_daily):
            raise DwrError("daily_rows_incomplete")
        cross = joint.cross_check(rows, marginals)
        if not cross["all_consistent"]:
            raise DwrError("joint_acquisition_inconsistent_with_exports")
        spec = source["archive"]
        folder = checked_path(private, private / spec["tables_directory"])
        inventory = archive.snapshot_inventory(folder, spec["commit"], period, repository=spec.get("repository"))
        by_day = defaultdict(int)
        by_site_day = defaultdict(lambda: defaultdict(int))
        for row in rows:
            by_day[row["date_utc"]] += row["request_count"]
            by_site_day[row["date_utc"]][row["site_id"]] += row["request_count"]
        for day in inventory["days"]:
            if day["archive_status"] == "archived" and day["aggregate_count"] != by_day[day["date_utc"]]:
                raise DwrError("archive_joint_daily_mismatch", day["date_utc"])
            if day["archive_status"] == "archived" and day["site_counts"] != dict(by_site_day[day["date_utc"]]):
                raise DwrError("archive_joint_site_daily_mismatch", day["date_utc"])
        digest = sha256_file(acquisition / "acquisition-log.json")
        normalized = {
            "edition_id": edition, "source_mode": "joint_acquisition", "joint_acquisition": log["acquisition_id"],
            "joint_extracted_at": {"start": log["started_at"], "end": log["ended_at"]},
            "joint_rows": rows, "joint_cross_check": cross, "marginals": marginals,
            "archive_inventory": inventory, "deployment_timeline": joint.deployment_timeline(acquisition, period),
            "measurement_provenance": source.get("measurement_provenance", {}),
            "source_provenance_contract": "private-next-inputs/1.0.0",
            "source_inputs": {"acquisition_log_sha256": digest,
                              "sources_config_sha256": sha256_file(private / "lock/sources-config.json"),
                              "archive_manifest_sha256": sha256_file(folder / "manifest.json")},
            "normalized_at": log["ended_at"], "nature": "observed_aggregates_private_unapproved",
        }
        if verify_only:
            return normalized
        import_id = "imp-" + digest[:12]
        write_once(private, private / "import" / import_id / "marginals.json", marginals)
        write_once(private, private / "import" / import_id / "receipt.json",
                   {"import_id": import_id, "acquisition_log_sha256": digest, "scope": cross["nature"]})
        target = private / "working" / edition / "normalized.json"
        write_once(private, target, normalized)
        return {"edition_id": edition, "rows": len(rows), "archive_days": len(inventory["days"]),
                "unavailable_archive_days": sum(d["archive_status"] != "archived" for d in inventory["days"]),
                "cross_checks": cross, "written": str(target)}


def qualify_next(private):
    expected = normalize(private, verify_only=True)
    with input_lock(private):
        period = window(private)
        target = checked_path(private, private / "working" / period.edition_id(1))
        normalized = load_json(target / "normalized.json")
        if normalized != expected:
            raise DwrError("normalized_inputs_differ_from_sources")
        result = qualify.qualify(normalized, private)
        from .maintenance import validate_inputs
        validate_inputs(normalized, result, period)
        write_once(private, target / "qualified.json", result)
        return {"edition_id": period.edition_id(1), "resources": len(result["resources"]),
                "graphs": {site: item["status"] for site, item in result["graphs"].items()},
                "written": str(target / "qualified.json")}


def verify_preparation_inputs(private, normalized, qualified):
    """Recompute this contract's inputs before preparing a private candidate."""
    if normalized != normalize(private, verify_only=True):
        raise DwrError("normalized_inputs_differ_from_sources")
    if qualified != qualify.qualify(normalized, private):
        raise DwrError("qualified_inputs_differ_from_sources")

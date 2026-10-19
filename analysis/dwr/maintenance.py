"""Manual, offline next-edition preparation. Outputs stay outside the public repo.

Inputs are the local normalized/qualified results of the existing pipeline.
No acquisition, scheduler, promotion or public-write capability is imported.
A blocked disclosure decision is kept in the private review package, never bypassed.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from . import dates, disclosure, edition_rules, joint, metrics, pipeline, project, render
from .common import (REPO_ROOT, DwrError, load_json, write_json, write_text, csv_text, sha256_file,
                     sha256_bytes, canonical_json, validate_path, validate_site, ACTOR_ROLES, IDENTITY_TIERS, HTTP_METHODS)


def validate_inputs(normalized, qualified, window):
    rows = normalized.get("joint_rows", [])
    if not rows or normalized.get("source_mode") != "joint_acquisition":
        raise DwrError("joint_aggregate_required")
    keys = set()
    for row in rows:
        validate_site(row["site_id"]); validate_path(row["path"])
        if not window.contains(dates.parse_date(row["date_utc"])):
            raise DwrError("joint_row_outside_window")
        if row["actor_role"] not in ACTOR_ROLES or row["stored_identity_tier"] not in IDENTITY_TIERS:
            raise DwrError("joint_classification_unknown")
        if row["http_method"] not in HTTP_METHODS or type(row["http_status"]) is not int or not 100 <= row["http_status"] <= 599:
            raise DwrError("joint_http_invalid")
        if type(row["request_count"]) is not int or row["request_count"] < 1:
            raise DwrError("joint_count_invalid")
        key = tuple(row[k] for k in joint.KEY) + (row.get("classifier_version"),)
        if key in keys:
            raise DwrError("joint_duplicate_key")
        keys.add(key)
    archive = normalized["archive_inventory"]["days"]
    if sorted(d["date_utc"] for d in archive) != [d.isoformat() for d in window.dates()]:
        raise DwrError("coverage_window_incomplete_or_duplicate")
    from collections import defaultdict
    daily = defaultdict(int)
    for row in rows:
        daily[row["date_utc"]] += row["request_count"]
    marginal = defaultdict(int)
    for row in normalized["marginals"]["daily"]:
        if not window.contains(dates.parse_date(row["date_utc"])) or type(row["all_requests"]) is not int or row["all_requests"] < 0:
            raise DwrError("marginal_daily_invalid")
        marginal[row["date_utc"]] += row["all_requests"]
    for day in archive:
        stamp = day["date_utc"]
        if day.get("archive_status") == "archived":
            count = day.get("aggregate_count")
            if type(count) is not int or count < 0 or count != daily[stamp]:
                raise DwrError("archive_joint_daily_mismatch")
        if marginal[stamp] != daily[stamp]:
            raise DwrError("marginal_joint_daily_mismatch")
    counts = joint.path_counts(rows)
    actual = {(r["site_id"], r["path"]): r.get("counts") for r in qualified["resources"] if r.get("counts")}
    if actual != counts:
        raise DwrError("qualified_counts_differ_from_joint")
    return rows


def prepare(private: Path, now=None):
    private = private.resolve()
    if private == REPO_ROOT or private.is_relative_to(REPO_ROOT):
        raise DwrError("private_root_inside_public_repository")
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise DwrError("naive_datetime_refused")
    timestamp = now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    state_path = private / "preparation/status.json"
    previous = load_json(state_path) if state_path.is_file() else load_json(REPO_ROOT / "data/status.json")
    calendar = load_json(REPO_ROOT / "config/edition-calendar.json")
    # An awaiting-review candidate stays the target; do not jump to the newest window.
    start = previous.get("pending_window_start") or (dates.parse_date(previous["latest_available_data_date"]) + timedelta(days=1)).isoformat()
    window = dates.monthly_window(dates.parse_date(start), calendar["monthly_anchor_day"])
    edition_id = window.edition_id(1)
    state = {**previous, "pending_window_start": start, "planning_activated": False}

    def finish(outcome, **extra):
        result = edition_rules.apply_run(state, outcome, run_at=timestamp)
        result.update(extra)
        write_json(state_path, result)
        return {"edition_id": edition_id, "outcome": outcome, "run_at": timestamp,
                "public_mutation": False, "planning_activated": False, **extra}

    if not dates.consolidation_ready(window, now, calendar["consolidation_delay_hours"]):
        return finish("unchanged", reason="next_window_not_consolidated")
    inputs = private / "working" / edition_id
    names = ("normalized.json", "qualified.json")
    if not all((inputs / name).is_file() for name in names):
        return finish("source_unavailable", reason="local_normalized_or_qualified_source_missing")
    target = private / "preparation/candidates" / edition_id
    try:
        normalized, qualified = (load_json(inputs / name) for name in names)
        if normalized.get("edition_id") != edition_id or qualified.get("edition_id") != edition_id:
            raise DwrError("source_edition_mismatch")
        validate_inputs(normalized, qualified, window)
        manifest = {name: sha256_file(inputs / name) for name in names}
        manifest.update({p.relative_to(REPO_ROOT).as_posix(): sha256_file(p) for folder in ("analysis/dwr", "config")
                         for p in (REPO_ROOT / folder).rglob("*") if p.is_file() and p.suffix in (".py", ".json", ".csv")})
        digest = sha256_bytes(canonical_json(manifest).encode("utf-8"))
        receipt_path = target / "preparation-receipt.json"
        if receipt_path.is_file():
            receipt = load_json(receipt_path)
            if receipt["input_digest"] != digest:
                raise DwrError("existing_candidate_changed_inputs_requires_revision")
            if any(not (target / name).is_file() or sha256_file(target / name) != value for name, value in receipt["files"].items()):
                raise DwrError("existing_candidate_bytes_changed")
            return finish("unchanged", candidate_state="awaiting_review", distribution_status=receipt["distribution_status"])
        if target.exists():
            raise DwrError("incomplete_candidate_requires_inspection")
        entry = {"edition_id": edition_id, "window": window, "edition_type": "monthly_reference", "revision": 1,
                 "status": "candidate_not_reviewed", "availability_status": "private_candidate", "reference_release_status": "not_approved",
                 "scientific_review_status": "not_independently_scientifically_reviewed", "supersedes": None, "superseded_by": None,
                 "source_mode": "joint_acquisition", "source_mode_note": "Existing local inputs; this command makes no acquisition.",
                 "generated_at": timestamp, "published_at": None, "revised_at": None}
        result = project.project(qualified, normalized, entry, "local-preparation")
        policy = load_json(REPO_ROOT / "config/small-cell-policy.json")
        candidate = disclosure.coarsen({k: result[k] for k in disclosure.TABLES}, policy)
        decision = disclosure.assess(candidate, disclosure.inventory(), policy)
        result.update(candidate)
        target.mkdir(parents=True)
        payload = target / "payload"; payload.mkdir()
        for key, name in disclosure.TABLES.items():
            field_name = {"consultations":"CONSULTATION", "resources":"RESOURCE", "daily":"DAILY", "coverage":"COVERAGE",
                          "family_daily":"FAMILY_DAILY", "resource_summary":"RESOURCE_SUMMARY", "actors":"ACTOR", "exclusions":"EXCLUSION"}[key]
            write_text(payload / name, csv_text(getattr(project, field_name + "_FIELDS"), result[key]))
        write_text(payload / "links.csv", csv_text(project.LINK_FIELDS, result["links"]))
        from . import public_checks, verify
        schema_report = verify.Report()
        verify.check_tables(schema_report, payload)
        identities = public_checks.reconcile_tables(payload)
        if not schema_report.result()["passed"] or not all(identities.values()):
            raise DwrError("prepared_projection_schema_or_reconciliation_failed")
        catalog = {"edition_id": edition_id, "edition_type": "monthly_reference", "source_mode": "joint_acquisition",
                   "metrics_version": "dwr-metrics/2.0.0", "coverage_status": result["measurement"]["coverage_status"],
                   "versions": {**pipeline.rule_versions(), "scope_registry_sha256": sha256_file(REPO_ROOT / "config/scope-registry.csv"),
                                "measurement_epoch_id": result["measurement"]["measurement_epoch_id"],
                                "classifier_recorded": result["measurement"]["epochs"]},
                   "source_provenance": normalized.get("source_provenance_contract", "unknown"), "input_digest": digest, "time_granularity": "edition", "graph_snapshots": result["graph_snapshots"],
                   "dates": {"period_start_inclusive": start, "period_end_exclusive": window.end_exclusive.isoformat(),
                             "calendar_days": window.days, "generated_at": timestamp, "extracted_at": normalized["joint_extracted_at"]},
                   "labels": {"period_en": window.label_en(), "period_fr": window.label_fr()},
                   "nature": normalized.get("nature", "local_private_candidate")}
        write_json(payload / "catalog.json", edition_rules.strip_operational_state(catalog))
        write_json(payload / "metrics.json", metrics.compute(payload))
        render.render_figures(render.Edition(edition_id, payload, entry), target / "figures")
        base = load_json(pipeline.edition_dir(pipeline.edition_entry(None)["edition_id"]) / "catalog.json")
        comparable, reasons = edition_rules.comparable(base, catalog)
        write_json(target / "delta-report.json", {"compared_with": base["edition_id"], "comparable": comparable,
                   "reasons": reasons, "growth": None, "is_growth": False, "new_window": True})
        write_json(target / "disclosure-report.json", decision)
        write_json(target / "measurement-report.json", result["measurement"])
        files = {p.relative_to(target).as_posix(): sha256_file(p) for p in sorted(target.rglob("*")) if p.is_file()}
        write_json(receipt_path, {"input_digest": digest, "input_manifest": manifest, "files": files,
                   "distribution_status": decision["status"], "state": "awaiting_review", "public_mutation": False})
        state["latest_available_data_date"] = max(r["date_utc"] for r in normalized["joint_rows"])
        return finish("awaiting_review", candidate_state="awaiting_review", distribution_status=decision["status"],
                      candidate_id=edition_id, source_state="local_inputs_available")
    except (DwrError, KeyError, TypeError, ValueError, OSError) as error:
        return finish("validation_failed", reason=error.code if isinstance(error, DwrError) else "local_input_or_output_invalid")

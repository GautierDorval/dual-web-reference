"""Manual, offline next-edition preparation. Outputs stay outside the public repo.

Inputs are the local normalized/qualified results of the existing pipeline.
No acquisition, scheduler, promotion or public-write capability is imported.
A blocked disclosure decision is kept in the private review package, never bypassed.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import os
import shutil
import tempfile
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
        key = tuple(row[k] for k in joint.KEY) + (row.get("classifier_version"), row.get("measurement_epoch_id"))
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
    """Exclusive local preparation. A completed candidate is installed by rename."""
    private = private.resolve()
    if private == REPO_ROOT or private.is_relative_to(REPO_ROOT):
        raise DwrError("private_root_inside_public_repository")
    from .write_guard import checked_path
    folder = checked_path(private, private / "preparation")
    folder.mkdir(parents=True, exist_ok=True)
    lock = checked_path(private, folder / "preparation.lock")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise DwrError("preparation_incomplete_or_busy") from exc
    os.close(fd)
    try:
        return _prepare_locked(private, now)
    finally:
        lock.unlink()


def atomic_json(path, value):
    """Replace a complete JSON file; never leave a truncated state document."""
    from .write_guard import checked_path
    checked_path(path.parent, path)
    fd, name = tempfile.mkstemp(prefix=".state-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(canonical_json(value))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _prepare_locked(private, now):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise DwrError("naive_datetime_refused")
    timestamp = now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    state_path = private / "preparation/status.json"
    from .write_guard import checked_path, fingerprint
    checked_path(private, state_path)
    previous = load_json(state_path) if state_path.is_file() else load_json(REPO_ROOT / "data/status.json")
    state = {**previous, "planning_activated": False}
    edition_id, stage = None, None

    def finish(outcome, **extra):
        result = edition_rules.apply_run(state, outcome, run_at=timestamp)
        result.update(extra)
        atomic_json(state_path, result)
        return {"edition_id": edition_id, "outcome": outcome, "run_at": timestamp,
                "public_mutation": False, "planning_activated": False, **extra}

    try:
        calendar = load_json(REPO_ROOT / "config/edition-calendar.json")
        # Window cursor and source freshness answer different questions.
        base_entry = pipeline.edition_entry(None)
        start = (previous.get("pending_window_start") or previous.get("last_processed_window_end_exclusive")
                 or base_entry["period_end_exclusive"])
        window = dates.monthly_window(dates.parse_date(start), calendar["monthly_anchor_day"])
        edition_id = window.edition_id(1)
        state["pending_window_start"] = start
        if not dates.consolidation_ready(window, now, calendar["consolidation_delay_hours"]):
            return finish("unchanged", reason="next_window_not_consolidated")
        inputs = checked_path(private, private / "working" / edition_id)
        names = ("normalized.json", "qualified.json")
        if not all(checked_path(private, inputs / name).is_file() for name in names):
            return finish("source_unavailable", reason="local_normalized_or_qualified_source_missing")
        target = checked_path(private, private / "preparation/candidates" / edition_id)
        normalized, qualified = (load_json(inputs / name) for name in names)
        if normalized.get("edition_id") != edition_id or qualified.get("edition_id") != edition_id:
            raise DwrError("source_edition_mismatch")
        validate_inputs(normalized, qualified, window)
        manifest = {name: sha256_file(inputs / name) for name in names}
        manifest.update({p.relative_to(REPO_ROOT).as_posix(): sha256_file(p) for folder in ("analysis/dwr", "config")
                         for p in (REPO_ROOT / folder).rglob("*") if p.is_file() and p.suffix in (".py", ".json", ".csv")})
        digest = sha256_bytes(canonical_json(manifest).encode("utf-8"))
        receipt_path = checked_path(private, target / "preparation-receipt.json")
        if receipt_path.is_file():
            receipt = load_json(receipt_path)
            if receipt["input_digest"] != digest:
                raise DwrError("existing_candidate_changed_inputs_requires_revision")
            actual = fingerprint(target)
            actual.pop("preparation-receipt.json")
            if actual != receipt["files"]:
                raise DwrError("existing_candidate_bytes_changed")
            # Recover the cursor if the process stopped between candidate rename and state replace.
            restoring = any(state.get(k) != v for k, v in receipt["cursor"].items())
            state.update(receipt["cursor"])
            return finish(receipt["state"] if restoring else "unchanged", recovered_existing_candidate=restoring,
                          preparation_status="complete_private",
                          candidate_state=receipt["state"], distribution_status=receipt["distribution_status"])
        if target.exists():
            raise DwrError("incomplete_candidate_requires_inspection")
        entry = {"edition_id": edition_id, "window": window, "edition_type": "monthly_reference", "revision": 1,
                 "status": "candidate_not_reviewed", "availability_status": "private_candidate", "reference_release_status": "not_approved",
                 "scientific_review_status": "no_independent_scientific_review_documented", "supersedes": None, "superseded_by": None,
                 "source_mode": "joint_acquisition", "source_mode_note": "Existing local inputs; this command makes no acquisition.",
                 "generated_at": timestamp, "published_at": None, "revised_at": None}
        result = project.project(qualified, normalized, entry, "local-preparation")
        policy = load_json(REPO_ROOT / "config/small-cell-policy.json")
        candidate = disclosure.coarsen({k: result[k] for k in disclosure.TABLES}, policy)
        decision = disclosure.assess(candidate, disclosure.inventory(REPO_ROOT), policy)
        result.update(candidate)
        target.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix=".staging-", dir=target.parent))
        payload = stage / "payload"; payload.mkdir()
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
                                "public_schema": "dwr-public/2.0.0",
                                "classifier_recorded": result["measurement"]["classifier_versions"]},
                   "measurement": {k: v for k, v in result["measurement"].items() if k != "rows"},
                   "resource_summary_grain": "union across epochs; distinct paths and days are not additive",
                   "source_provenance": normalized.get("source_provenance_contract", "unknown"), "input_digest": digest, "time_granularity": "edition", "graph_snapshots": result["graph_snapshots"],
                   "dates": {"period_start_inclusive": start, "period_end_exclusive": window.end_exclusive.isoformat(),
                             "calendar_days": window.days, "generated_at": timestamp, "extracted_at": normalized["joint_extracted_at"]},
                   "labels": {"period_en": window.label_en(), "period_fr": window.label_fr()},
                   "nature": normalized.get("nature", "local_private_candidate")}
        catalog["files"] = [{"path": p.name, "sha256": sha256_file(p), "bytes": p.stat().st_size,
                             "rows": len(p.read_text(encoding="utf-8").splitlines()) - 1,
                             "empty_reason": "no qualifying rows in this local window" if len(p.read_text(encoding="utf-8").splitlines()) == 1 else None}
                            for p in sorted(payload.glob("*.csv"))]
        catalog["files_not_listed_here"] = ["catalog.json (self reference excluded)",
            "metrics.json, figures.json, ../figures/* and private reports: sealed by preparation-receipt.json after derivation"]
        write_json(payload / "catalog.json", edition_rules.strip_operational_state(catalog))
        write_json(payload / "metrics.json", metrics.compute(payload))
        render.render_figures(render.Edition(edition_id, payload, entry), stage / "figures")
        base = load_json(pipeline.edition_dir(pipeline.edition_entry(None)["edition_id"]) / "catalog.json")
        comparable, reasons = edition_rules.comparable(base, catalog)
        write_json(stage / "delta-report.json", {"compared_with": base["edition_id"], "comparable": comparable,
                   "classifier_adapters": [edition_rules.classifier_adapter(c) for c in (base, catalog)],
                   "reasons": reasons, "growth": None, "is_growth": False, "new_window": True})
        write_json(stage / "disclosure-report.json", decision)
        write_json(stage / "measurement-report.json", result["measurement"])
        outcome = "distribution_blocked_pending_policy_approval" if decision["allowed"] else "distribution_blocked_pending_contract"
        cursor = {"latest_available_data_date": max(r["date_utc"] for r in normalized["joint_rows"]),
                  "last_processed_window_end_exclusive": window.end_exclusive.isoformat(),
                  "pending_window_start": start}
        files = fingerprint(stage)
        write_json(stage / "preparation-receipt.json", {"input_digest": digest, "input_manifest": manifest, "files": files,
                   "distribution_status": decision["status"], "state": outcome, "preparation_status": "complete_private",
                   "cursor": cursor, "public_mutation": False})
        os.rename(stage, target)
        stage = None
        state.update(cursor)
        return finish(outcome, preparation_status="complete_private", candidate_state=outcome, distribution_status=decision["status"],
                      candidate_id=edition_id, source_state="local_inputs_available")
    except (DwrError, KeyError, TypeError, ValueError, OSError) as error:
        return finish("validation_failed", reason=error.code if isinstance(error, DwrError) else "local_input_or_output_invalid")
    finally:
        if stage is not None:
            shutil.rmtree(stage)

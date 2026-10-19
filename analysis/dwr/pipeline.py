"""Stage orchestration. Private stages write under the private workspace only;
public stages read and write repository files only and never touch the network.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import archive, importer, reconcile, edition_rules
from .common import REPO_ROOT, DwrError, load_json, write_json
from .dates import window_from_strings


RULE_FILES = {"scope_rules": ("scope-rules.json", "rules_id"),
              "attribution_rules": ("attribution-rules.json", "rules_id"),
              "small_cell_policy": ("small-cell-policy.json", "policy_id")}


def rule_versions(edition_id=None) -> dict:
    """Versions of the rules applied to an edition, read from their configuration files."""
    from .frozen import rule_path
    return {key: load_json(rule_path(edition_id, name))[field] for key, (name, field) in RULE_FILES.items()}


def editions_config() -> dict:
    return load_json(REPO_ROOT / "config" / "editions.json")


def edition_entry(edition_id: str | None) -> dict:
    config = editions_config()
    edition_id = edition_id or config["candidate"]
    for entry in config["editions"]:
        if entry["edition_id"] == edition_id:
            window = window_from_strings(entry["period_start_inclusive"], entry["period_end_exclusive"])
            if window.edition_id(entry["revision"]) != edition_id:
                raise DwrError("edition_id_inconsistent_with_window", edition_id)
            return {**entry, "window": window}
    raise DwrError("edition_unknown", edition_id)


def working_dir(private: Path, edition_id: str) -> Path:
    return private / "working" / edition_id


def sources_config(private: Path) -> dict:
    return load_json(private / "lock" / "sources-config.json")


def cmd_import(package: Path, private: Path, edition_id: str | None) -> dict:
    entry = edition_entry(edition_id)
    window = entry["window"]
    result = importer.import_existing(package, private, window.start.isoformat(), window.end_exclusive.isoformat())
    marginals = load_json(Path(result["marginals"]))
    expected = load_json(package / "REFERENCE-CHIFFRES.json")["computed"]
    computed = reconcile.historical_figures(marginals)
    comparison = reconcile.compare(computed, expected)
    daily = reconcile.daily_reconciliation(marginals)
    report = {
        "nature": "offline reproduction of arithmetic on the same exports; not an independent audit",
        "import_id": result["import_id"],
        "comparison": comparison,
        "by_site_provider_origin_ai_get200": computed["_by_site_provider_origin_ai_get200"],
        "daily": daily,
        "daily_all_match_archive_aggregate": all(row["export_matches_archive_aggregate"] for row in daily),
    }
    write_json(working_dir(private, entry["edition_id"]) / "reconciliation.json", report)
    if not comparison["all_match"]:
        raise DwrError("reconciliation_mismatch", "stop: same inputs gave a different result")
    return {**result, "reconciliation": "all_match", "daily_match": report["daily_all_match_archive_aggregate"]}


def cmd_acquire(private: Path | None, edition_id: str | None, execute: bool, confirm_scope: str | None) -> dict:
    from . import acquire
    entry = edition_entry(edition_id)
    if not execute:
        return acquire.acquire(Path("."), entry["window"], execute=False, confirm_scope=None)
    return acquire.acquire(private, entry["window"], execute=True, confirm_scope=confirm_scope)


def cmd_normalize(private: Path, edition_id: str | None) -> dict:
    entry = edition_entry(edition_id)
    window = entry["window"]
    sources = sources_config(private)
    imports = sorted((private / "import").glob("imp-*/marginals.json"))
    if len(imports) != 1:
        raise DwrError("import_ambiguous_or_missing", f"{len(imports)} imports")
    marginals = load_json(imports[0])
    if marginals["window"] != {"start_inclusive": window.start.isoformat(), "end_exclusive": window.end_exclusive.isoformat()}:
        raise DwrError("import_window_mismatch")
    archive_info = sources["archive"]
    inventory = archive.inventory(Path(archive_info["repository_path"]), archive_info["commit"], window)
    acquisitions = sorted((private / "acquisition").glob("acq-*/acquisition-log.json"))
    accepted = [path for path in acquisitions if load_json(path).get("status") == "new_data"
                and load_json(path).get("scope") == f"{window.start.isoformat()}..{window.end_exclusive.isoformat()}"]
    joint_rows, cross, timeline = None, None, None
    if accepted:
        from . import joint
        acquisition_dir = accepted[-1].parent
        joint_rows = joint.load_rows(acquisition_dir, window)
        cross = joint.cross_check(joint_rows, marginals)
        if not cross["all_consistent"]:
            raise DwrError("joint_acquisition_inconsistent_with_exports",
                           "; ".join(f"{c['check']}={c['mismatches']}" for c in cross["checks"] if c["mismatches"]))
        timeline = joint.deployment_timeline(acquisition_dir, window)
    normalized = {
        "edition_id": entry["edition_id"],
        "source_mode": "joint_acquisition" if accepted else "export_marginals",
        "joint_acquisition": accepted[-1].parent.name if accepted else None,
        "joint_extracted_at": ({"start": load_json(accepted[-1]).get("started_at"), "end": load_json(accepted[-1]).get("ended_at")}
                               if accepted else None),
        "joint_rows": joint_rows,
        "joint_cross_check": cross,
        "deployment_timeline": timeline,
        "measurement_provenance": sources.get("measurement_provenance", {}),
        "marginals": marginals,
        "archive_inventory": inventory,
        "normalized_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    target = working_dir(private, entry["edition_id"]) / "normalized.json"
    write_json(target, normalized)
    return {"edition_id": entry["edition_id"], "source_mode": normalized["source_mode"],
            "archive_days": len(inventory["days"]), "written": str(target)}


# ---------------------------------------------------------------- private qualify


def cmd_qualify(private: Path, edition_id: str | None) -> dict:
    from . import qualify
    entry = edition_entry(edition_id)
    normalized = load_json(working_dir(private, entry["edition_id"]) / "normalized.json")
    qualified = qualify.qualify(normalized, private)
    target = working_dir(private, entry["edition_id"]) / "qualified.json"
    write_json(target, qualified)
    classes = {}
    for resource in qualified["resources"]:
        classes[resource["scope_class"]] = classes.get(resource["scope_class"], 0) + 1
    return {"edition_id": entry["edition_id"], "resources": len(qualified["resources"]), "classes": classes,
            "graphs": {site: g["status"] for site, g in qualified["graphs"].items()}, "written": str(target)}


# ---------------------------------------------------------------- public projection


def edition_dir(edition_id: str) -> Path:
    return REPO_ROOT / "data" / "editions" / edition_id


EMPTY_REASONS = {
    "daily-family-summary.csv": "no automated provider-origin AI GET 200 to the main population in the window",
}


def cmd_project_public(private: Path, edition_id: str | None) -> dict:
    from . import project
    from .common import csv_text, write_text
    entry = edition_entry(edition_id)
    from .frozen import refuse_write
    refuse_write(entry["edition_id"])
    work = working_dir(private, entry["edition_id"])
    normalized = load_json(work / "normalized.json")
    qualified = load_json(work / "qualified.json")
    reconciliation = load_json(work / "reconciliation.json")
    imports = sorted((private / "import").glob("imp-*/receipt.json"))
    import_id = load_json(imports[0])["import_id"]
    result = project.project(qualified, normalized, entry, import_id)
    from . import disclosure
    policy = load_json(REPO_ROOT / "config/small-cell-policy.json")
    candidate = disclosure.coarsen({k: result[k] for k in disclosure.TABLES}, policy)
    decision = disclosure.enforce(candidate, disclosure.inventory(), policy)
    result.update(candidate)
    target = edition_dir(entry["edition_id"])
    tables = {
        "resources.csv": (project.RESOURCE_FIELDS, result["resources"]),
        "links.csv": (project.LINK_FIELDS, result["links"]),
        "consultations.csv": (project.CONSULTATION_FIELDS, result["consultations"]),
        "resource-summary.csv": (project.RESOURCE_SUMMARY_FIELDS, result["resource_summary"]),
        "daily-summary.csv": (project.DAILY_FIELDS, result["daily"]),
        "actor-summary.csv": (project.ACTOR_FIELDS, result["actors"]),
        "coverage.csv": (project.COVERAGE_FIELDS, result["coverage"]),
        "exclusions.csv": (project.EXCLUSION_FIELDS, result["exclusions"]),
        "daily-family-summary.csv": (project.FAMILY_DAILY_FIELDS, result["family_daily"]),
    }
    for name, (fields, rows) in tables.items():
        write_text(target / name, csv_text(fields, rows))
    write_json(target / "reconciliation.json", {
        "nature": reconciliation["nature"],
        "historical_figures": reconciliation["comparison"],
        "historical_by_site_provider_origin_ai_get200": reconciliation["by_site_provider_origin_ai_get200"],
        "daily_all_match_archive_aggregate": reconciliation["daily_all_match_archive_aggregate"],
        "joint_aggregate_vs_exports": normalized["joint_cross_check"],
    })
    write_json(target / "case-checks.json", {
        "nature": "excerpts verified verbatim (whitespace-normalized) in the private source snapshot; path steps verified as relations of the snapshot graph",
        "checks": qualified["case_checks"],
        "all_verified": all(check["verified"] for check in qualified["case_checks"]),
    })
    write_json(target / "disclosure.json", decision)
    write_json(target / "catalog.json", build_catalog(entry, normalized, result, tables, target, private))
    return {"edition_id": entry["edition_id"], "rows": {name: len(rows) for name, (_, rows) in tables.items()}}


def build_catalog(entry, normalized, result, tables, target, private) -> dict:
    from .common import sha256_file
    from . import SCHEMA_VERSION, CODE_VERSION
    window = entry["window"]
    from .dates import next_monthly_window
    calendar = load_json(REPO_ROOT / "config/edition-calendar.json")
    following = next_monthly_window(window, calendar["monthly_anchor_day"])
    ready = datetime.combine(following.end_exclusive, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=calendar["consolidation_delay_hours"])
    exports_extracted = sorted(normalized["marginals"]["extracted_at"])
    joint_extracted = normalized["joint_extracted_at"]
    timeline = normalized.get("deployment_timeline") or {}
    files = []
    for name in sorted(tables) + ["reconciliation.json", "case-checks.json"]:
        path = target / name
        rows = len(tables[name][1]) if name in tables else None
        files.append({"path": name, "bytes": path.stat().st_size, "sha256": sha256_file(path), "rows": rows,
                      "status": "empty_with_reason" if rows == 0 else "published_candidate",
                      "empty_reason": EMPTY_REASONS.get(name) if rows == 0 else None})
    lock = private / "lock" / "private-lock.json"
    graphs = result["graph_snapshots"]
    return edition_rules.strip_operational_state({
        "schema_version": "dwr-catalog/1.0.0",
        "edition_id": entry["edition_id"],
        "edition_type": entry["edition_type"],
        "revision": entry["revision"],
        "status": entry["status"],
        "supersedes": entry["supersedes"],
        "superseded_by": entry["superseded_by"],
        "source_mode": entry["source_mode"],
        "source_mode_note": entry["source_mode_note"],
        "versions": {"code": CODE_VERSION, "public_schema": SCHEMA_VERSION, **rule_versions(),
                     "classifier_recorded": result.get("measurement", {}).get("epochs", []),
                     "measurement_epoch_id": result.get("measurement", {}).get("measurement_epoch_id", "unknown"),
                     "scope_registry_sha256": sha256_file(REPO_ROOT / "config/scope-registry.csv")},
        "metrics_version": "dwr-metrics/2.0.0",
        "coverage_status": result.get("measurement", {}).get("coverage_status", "coverage_unknown"),
        "source_provenance": normalized.get("source_provenance_contract", "unknown"),
        "time_granularity": "edition",
        "dates": {
            "period_start_inclusive": window.start.isoformat(),
            "period_end_exclusive": window.end_exclusive.isoformat(),
            "last_included_date": window.last_included.isoformat(),
            "timezone": "UTC",
            "calendar_days": window.days,
            "extracted_at": {"start": joint_extracted["start"].replace("+00:00", "Z"), "end": joint_extracted["end"].replace("+00:00", "Z")},
            "exports_extracted_at": {"start": exports_extracted[0], "end": exports_extracted[-1]},
            "source_snapshot_at": normalized["marginals"]["source"]["archive_commit_at"],
            "graph_snapshot_at": {site: info["graph_snapshot_at"] for site, info in graphs.items()},
            "generated_at": entry["generated_at"],
            "published_at": entry["published_at"],
            "revised_at": entry["revised_at"],
            "latest_available_data_date": window.last_included.isoformat(),
            "next_review_target": {
                "weekly_review": None,
                "next_monthly_window": {"start_inclusive": following.start.isoformat(), "end_exclusive": following.end_exclusive.isoformat(), "days": following.days},
                "earliest_monthly_preparation": ready.isoformat().replace("+00:00", "Z"),
                "guarantee": "none: planned target; manual preparation until automation is authorized and proven",
            },
        },
        "labels": {"period_en": window.label_en(), "period_fr": window.label_fr()},
        "graph_snapshots": graphs,
        "producer_deployments": result["deployments"],
        "producer_deployment_history": {key: timeline.get(key) for key in (
            "status", "observations", "first_observed_at", "last_observed_at", "max_gap_hours")},
        "method_status_split": "joint_exact; the split deduced from the exports by zero mass was confirmed on every path",
        "source_snapshot_id": result["source_snapshot_id"],
        "provenance_public": [
            "Producer: private collector writing daily aggregate counters; classifier provenance is recorded in versions, never inferred from current code.",
            "Joint aggregate: bounded read-only SELECT of the producer daily aggregate table (day x site x path x method x status x actor x tier), read between the extraction times above, checksums identical before and after, zero rows written.",
            "Exports of the initial internal report (read earlier the same day, exports_extracted_at): used for reconciliation; the joint aggregate reproduces them exactly.",
            "Producer deployment history: captured by the producer from the Cloudflare control plane; deployment labels replace private identifiers.",
            "Archive: private daily-report archive, read at a pinned commit dated source_snapshot_at.",
            "Graphs: private source repositories of the three sites, read at pinned commits dated graph_snapshot_at.",
        ],
        "not_reproducible_from_public_files": [
            "The collection itself (requests received by the sites) and the producer classification.",
            "The joint aggregate, the exports and the archive (private): a reader can recompute every published number from the public tables, not re-run the extraction.",
            "The graph snapshots (private repositories): links.csv records each relation with its file and line.",
        ],
        "private_lock_sha256": sha256_file(lock) if lock.is_file() else None,
        "files": files,
        "files_not_listed_here": ["catalog.json (this file)", "metrics.json and figures.json (derived after the catalog)",
                                  "SHA256SUMS.txt (does not include itself)"],
    })


# ---------------------------------------------------------------- public render


def cmd_render(edition_id: str | None) -> dict:
    from . import render
    entry = edition_entry(edition_id)
    from .frozen import verify as verify_frozen
    historical = verify_frozen(entry["edition_id"])
    if historical:
        return historical
    return render.cmd(entry["edition_id"])


def cmd_verify(edition_id: str | None) -> dict:
    import os
    from . import verify
    entry = edition_entry(edition_id)
    lock = None
    if os.environ.get("DWR_PRIVATE_ROOT"):
        candidate = Path(os.environ["DWR_PRIVATE_ROOT"]) / "lock" / "private-lock.json"
        lock = candidate if candidate.is_file() else None
    result = verify.cmd(entry["edition_id"], lock)
    result["private_lock_used"] = lock is not None
    return result


def cmd_prepare_edition(edition_id: str | None) -> dict:
    """Candidate package: SHA256SUMS.txt over the edition files (never itself) and a delta report."""
    from .common import sha256_file, write_text
    entry = edition_entry(edition_id)
    from .frozen import refuse_write
    refuse_write(entry["edition_id"])
    target = edition_dir(entry["edition_id"])
    figure_dir = REPO_ROOT / "figures" / entry["edition_id"]
    figure_files = sorted(p for p in figure_dir.iterdir() if p.is_file())
    from .edition_rules import latest_pointer
    if entry.get("supersedes"):
        delta = load_json(target / "delta-report.json")
        if delta.get("cause") != "privacy_revision" or delta.get("is_growth") is not False:
            raise DwrError("revision_delta_missing_or_inconsistent")
    else:
        previous = latest_pointer(editions_config()["editions"])
        delta = {"schema_version": "dwr-delta/2.0.0", "edition_id": entry["edition_id"],
                 "compared_with": previous, "status": "no_previous_approved_edition" if previous is None else "comparison_required",
                 "is_growth": False}
        write_json(target / "delta-report.json", delta)
    lines =[f"{sha256_file(p)}  data/editions/{entry['edition_id']}/{p.name}" for p in sorted(
        p for p in target.iterdir() if p.is_file() and p.name != "SHA256SUMS.txt")] + [
        f"{sha256_file(p)}  figures/{entry['edition_id']}/{p.name}" for p in figure_files]
    text = "\n".join(lines) + "\n"
    write_text(target / "SHA256SUMS.txt", text)
    from .common import sha256_bytes
    return {"edition_id": entry["edition_id"], "files": len(lines), "sha256sums_digest": sha256_bytes(text.encode("utf-8")),
            "excluded": ["SHA256SUMS.txt (does not include itself)", "figures/<edition>/png/* (optional, not bit-reproducible)"],
            "delta": delta.get("status", delta.get("cause")), "note": "archive checksum manifest; approval uses edition_rules.payload_manifest and its external receipt, including PNG bytes"}


def cmd_status(edition_id: str | None) -> dict:
    from datetime import date
    status = load_json(REPO_ROOT / "data" / "status.json")
    calendar = load_json(REPO_ROOT / "config" / "edition-calendar.json")
    today = datetime.now(timezone.utc).date()
    last_review = date.fromisoformat(status["last_review"]["date"])
    overdue = (today - last_review).days > calendar["freshness_thresholds"]["weekly_review_overdue_after_days"]
    return {**status, "checked_on": today.isoformat(), "weekly_review_overdue": overdue,
            "note": "status.json is not real time; checked_on is the date of this command, not a data date"}


def cmd_build_site(edition_id: str | None) -> dict:
    from . import site_build
    entry = edition_entry(edition_id)
    return site_build.cmd(entry["edition_id"])


# ---------------------------------------------------------------- public analyze


def cmd_analyze(edition_id: str | None) -> dict:
    from . import metrics
    entry = edition_entry(edition_id)
    from .frozen import verify as verify_frozen
    historical = verify_frozen(entry["edition_id"])
    if historical:
        return historical
    target = edition_dir(entry["edition_id"])
    result = {"schema_version": "dwr-metrics/1.0.0", "edition_id": entry["edition_id"], **metrics.compute(target)}
    write_json(target / "metrics.json", result)
    headline = {m["metric_id"]: m["value"] for m in result["metrics"] if m["metric_id"].count(".") == 1
                and m["metric_id"].startswith("main.")}
    return {"edition_id": entry["edition_id"], "metrics": len(result["metrics"]), "headline": headline}

"""Offline privacy revision of an inventoried public edition, without new acquisition.

This explicit transformer replaces ad hoc copying: it preserves observation cells,
changes the edition key, coarsens distribution and regenerates the catalog. It
cannot revise an approved/public target or change the observed time window.
"""
from copy import deepcopy
from . import disclosure, frozen, pipeline, edition_rules
from .common import REPO_ROOT, DwrError, load_json, write_json, write_text, csv_text, read_csv, sha256_file


def prepare(edition_id=None):
    entry = pipeline.edition_entry(edition_id)
    frozen.refuse_write(entry["edition_id"])
    if entry.get("availability_status") != "local_candidate" or entry.get("reference_release_status") != "not_approved":
        raise DwrError("revision_target_not_local_unapproved")
    from .write_guard import transaction
    with transaction(REPO_ROOT, entry["edition_id"], fresh_payload=True, fresh_figures=True) as stage:
        result = _prepare_into(entry, stage / "payload")
        pipeline.derive_stage(entry, stage)
        return result


def _prepare_into(entry, target):
    source = entry.get("supersedes")
    if not source or not frozen.verify(source):
        raise DwrError("revision_requires_frozen_source")
    previous = pipeline.edition_entry(source)
    if (previous["period_start_inclusive"], previous["period_end_exclusive"]) != (entry["period_start_inclusive"], entry["period_end_exclusive"]):
        raise DwrError("revision_window_changed")
    original = pipeline.edition_dir(source)
    policy = load_json(REPO_ROOT / "config/small-cell-policy.json")
    tables = disclosure.tables(original)
    for rows in tables.values():
        for row in rows:
            if "edition_id" in row:
                row["edition_id"] = entry["edition_id"]
    tables = disclosure.coarsen(tables, policy)
    report = disclosure.enforce(tables, disclosure.inventory(REPO_ROOT), policy)
    # All checks precede the first write; the internal brief is never an input.
    for key, name in disclosure.TABLES.items():
        header = (original / name).read_text(encoding="utf-8").splitlines()[0].split(",")
        write_text(target / name, csv_text(header, tables[key]))
    for name in ("links.csv", "reconciliation.json", "case-checks.json"):
        write_text(target / name, (original / name).read_text(encoding="utf-8"))
    catalog = deepcopy(load_json(original / "catalog.json"))
    catalog.update(edition_id=entry["edition_id"], revision=entry["revision"], supersedes=source,
                   metrics_version="dwr-metrics/2.0.0", availability_status="local_candidate",
                   reference_release_status="not_approved", scientific_review_status=entry["scientific_review_status"],
                   revision_kind="privacy_revision_same_observations", observation_source_edition=source)
    catalog["dates"].update(generated_at=entry["generated_at"], revised_at=entry["revised_at"])
    catalog["versions"].update(small_cell_policy=policy["policy_id"], scope_registry_sha256=sha256_file(REPO_ROOT / "config/scope-registry.csv"))
    for item in catalog["files"]:
        path = target / item["path"]
        item.update(sha256=sha256_file(path), bytes=path.stat().st_size)
        if path.suffix == ".csv":
            item["rows"] = len(read_csv(path))
    write_json(target / "disclosure.json", report)
    write_json(target / "delta-report.json", {"schema_version": "dwr-delta/2.0.0", "edition_id": entry["edition_id"],
               "compared_with": source, "cause": "privacy_revision", "additional_changes": ["presentation", "metadata", "derived_metrics"],
               "observations_changed": False, "is_growth": False, "protected_daily": "withheld_not_zero",
               "coverage_daily_margins": "withheld_not_zero", "source_payload_status": "frozen_original_bytes_preserved"})
    catalog["files"] = [{"path": p.name, "sha256": sha256_file(p), "bytes": p.stat().st_size,
                          "rows": len(read_csv(p)) if p.suffix == ".csv" else None,
                          "empty_reason": "no rows after minimization" if p.suffix == ".csv" and not read_csv(p) else None}
                         for p in sorted(target.iterdir()) if p.is_file() and p.name not in
                         ("catalog.json", "metrics.json", "figures.json", "SHA256SUMS.txt")]
    catalog["files_not_listed_here"] = ["catalog.json (self reference excluded)",
        "metrics.json, figures.json, figures/* (derived after catalog; SHA256SUMS.txt seals deterministic outputs)",
        "SHA256SUMS.txt (self reference excluded); PNG (optional non-bit-reproducible fallback)"]
    write_json(target / "catalog.json", edition_rules.strip_operational_state(catalog))
    from . import verify, public_checks
    checked = verify.Report()
    verify.check_tables(checked, target)
    if not checked.result()["passed"] or not all(public_checks.reconcile_tables(target).values()):
        raise DwrError("prepared_projection_schema_or_reconciliation_failed")
    return {"edition_id": entry["edition_id"], "source": source, "status": "local_candidate",
            "cause": "privacy_revision", "disclosure": report["status"], "new_acquisition": False}

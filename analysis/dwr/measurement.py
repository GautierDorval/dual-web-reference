"""Measurement provenance and coverage, without historical defaults or synthetic splits."""
from .common import DwrError

REQUIRED_EPOCH = ("classifier_version", "attribution_rules", "deployment_evidence")


def epoch(row, provenance):
    """Only a version recorded on the row or a uniquely attested segment qualifies it."""
    day = row["date_utc"]
    known = provenance.get("days", {}).get(day, {})
    versions = known.get("epochs", [])
    recorded = row.get("classifier_version")
    if recorded:
        matches = [e for e in versions if e.get("classifier_version") == recorded]
    elif known.get("separable") is False and len(versions) > 1:
        return {"measurement_epoch_id": "mixed_epoch_unresolved", "classifier_version": "mixed_epoch_unresolved", "comparable": False}
    elif len(versions) == 1:
        matches = versions
    else:
        matches = []
    if len(matches) != 1 or any(not matches[0].get(k) for k in REQUIRED_EPOCH):
        return {"measurement_epoch_id": "unknown", "classifier_version": recorded or "unknown", "comparable": False}
    item = matches[0]
    return {"measurement_epoch_id": item.get("epoch_id") or "classifier-" + item["classifier_version"],
            "classifier_version": item["classifier_version"], "comparable": True}


def coverage(day):
    if day.get("archive_status") != "archived":
        return "observation_unavailable"
    state = day.get("report_status")
    if state in ("complete", "complete_declared"):
        return "complete_declared"
    if state in ("partial", "partial_declared"):
        return "partial_declared"
    return "coverage_unknown"


def combined_coverage(states):
    states = set(states)
    if not states or "coverage_unknown" in states:
        return "coverage_unknown"
    if states == {"observation_unavailable"}:
        return "observation_unavailable"
    if "observation_unavailable" in states:
        return "mixed_coverage"
    return "partial_declared" if "partial_declared" in states else "complete_declared"


def qualify(rows, archive_days, provenance):
    by_day = {d["date_utc"]: d for d in archive_days}
    if len(by_day) != len(archive_days):
        raise DwrError("coverage_duplicate_day")
    qualified = []
    for row in rows:
        cov = coverage(by_day.get(row["date_utc"], {}))
        if cov == "observation_unavailable":
            raise DwrError("rows_on_unavailable_day")
        qualified.append({**row, **epoch(row, provenance), "coverage_status": cov})
    epochs = sorted({r["measurement_epoch_id"] for r in qualified})
    return {"rows": qualified, "epochs": epochs,
            "measurement_epoch_id": epochs[0] if len(epochs) == 1 else "mixed_epoch_unresolved" if epochs else "unknown",
            "coverage_status": combined_coverage(coverage(d) for d in archive_days),
            "days": {day: {"coverage_status": coverage(record),
                           "epochs": sorted({r["measurement_epoch_id"] for r in qualified if r["date_utc"] == day}),
                           "attribution_comparable": coverage(record) != "observation_unavailable" and any(r["date_utc"] == day for r in qualified) and all(r["comparable"] for r in qualified if r["date_utc"] == day)}
                     for day, record in by_day.items()}}

"""Measurement provenance and coverage, without historical defaults or synthetic splits."""
from .common import DwrError
import re

REQUIRED_EPOCH = ("classifier_version", "attribution_rules", "deployment_evidence")
TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
UNRESOLVED = ("unknown", "mixed_epoch_unresolved")
RESOLUTIONS = (*UNRESOLVED, "single_epoch_resolved", "multiple_epochs_resolved")
COVERAGE_STATES = ("observation_unavailable", "complete_declared", "partial_declared", "coverage_unknown", "mixed_coverage")


def recorded_classifiers(rows):
    """State markers are not versions; retained row values remain explicit."""
    return sorted({r["classifier_version"] for r in rows if r["classifier_version"] not in UNRESOLVED})


def token(value):
    if not isinstance(value, str) or not TOKEN.fullmatch(value):
        raise DwrError("measurement_token_invalid")
    return value


def epoch_summary(epochs):
    epochs = sorted(set(epochs))
    if "mixed_epoch_unresolved" in epochs:
        return "mixed_epoch_unresolved"
    if not epochs or "unknown" in epochs:
        return "unknown"
    return epochs[0] if len(epochs) == 1 else "multiple_epochs_resolved"


def resolution(epochs):
    summary = epoch_summary(epochs)
    return summary if summary in ("unknown", "mixed_epoch_unresolved", "multiple_epochs_resolved") else "single_epoch_resolved"


def epoch(row, provenance):
    """Only a version recorded on the row or a uniquely attested segment qualifies it."""
    day = row["date_utc"]
    known = provenance.get("days", {}).get(day, {})
    versions = known.get("epochs", [])
    if not isinstance(versions, list) or any(not isinstance(e, dict) for e in versions):
        raise DwrError("measurement_provenance_invalid")
    for item in versions:
        for key in ("classifier_version", "epoch_id"):
            if item.get(key) is not None:
                token(item[key])
    recorded = row.get("classifier_version")
    if recorded is not None:
        token(recorded)
    explicit_epoch = row.get("measurement_epoch_id")
    if explicit_epoch:
        token(explicit_epoch)
        matches = [e for e in versions if e.get("epoch_id") == explicit_epoch
                   and (not recorded or e.get("classifier_version") == recorded)]
    elif recorded:
        token(recorded)
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
    definitions = {}
    for record in provenance.get("days", {}).values():
        for item in record.get("epochs", []):
            if not isinstance(item, dict) or not item.get("classifier_version"):
                raise DwrError("measurement_provenance_invalid")
            identifier = token(item.get("epoch_id") or "classifier-" + token(item["classifier_version"]))
            definition = {"classifier_version": token(item["classifier_version"]),
                          "attribution_rules": item.get("attribution_rules"),
                          "deployment_evidence_present": bool(item.get("deployment_evidence"))}
            if identifier in definitions and definitions[identifier] != definition:
                raise DwrError("measurement_epoch_definition_conflict")
            definitions[identifier] = definition
    qualified = []
    for row in rows:
        cov = coverage(by_day.get(row["date_utc"], {}))
        if cov == "observation_unavailable":
            raise DwrError("rows_on_unavailable_day")
        qualified.append({**row, **epoch(row, provenance), "coverage_status": cov})
    epochs = sorted({r["measurement_epoch_id"] for r in qualified})
    classifiers = recorded_classifiers(qualified)
    return {"rows": qualified, "epochs": epochs, "classifier_versions": classifiers,
            "epoch_definitions": {key: definitions[key] for key in sorted(definitions) if key in epochs},
            "measurement_epoch_id": epoch_summary(epochs), "epoch_resolution": resolution(epochs),
            "coverage_status": combined_coverage(coverage(d) for d in archive_days),
            "days": {day: {"coverage_status": coverage(record),
                           "epochs": sorted({r["measurement_epoch_id"] for r in qualified if r["date_utc"] == day}),
                           "classifier_versions": recorded_classifiers(r for r in qualified if r["date_utc"] == day),
                           "epoch_resolution": resolution(r["measurement_epoch_id"] for r in qualified if r["date_utc"] == day),
                           "attribution_comparable": coverage(record) != "observation_unavailable" and any(r["date_utc"] == day for r in qualified) and all(r["comparable"] for r in qualified if r["date_utc"] == day)}
                     for day, record in sorted(by_day.items())}}

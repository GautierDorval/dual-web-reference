"""Operating rules of editions, expressed as small pure functions (tested).

- A correction creates a new revision; the previous one is kept and linked.
- latest points only to a reviewed, published edition.
- An unchanged run never advances the data date; a failed source keeps the last
  valid edition and records the unavailability, never zeros.
- Rolling windows overlap and are never added.
- Two editions are compared only when their definitions allow it.
- A review approves a candidate digest; any later change invalidates it.
"""

from __future__ import annotations

import re

from .common import DwrError

EDITION_ID = re.compile(r"^(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})-r(\d+)$")
CORRECTION_CAUSES = ("late_observations", "classifier_correction", "scope_change", "transformation_correction",
                     "privacy_revision")
COMPARABILITY_KEYS = ("edition_type", "source_mode", "scope_rules", "attribution_rules", "small_cell_policy",
                      "classifier_recorded", "measurement_epoch_id")


def parse_edition_id(edition_id: str) -> tuple[str, str, int]:
    match = EDITION_ID.match(edition_id or "")
    if not match:
        raise DwrError("edition_id_invalid", str(edition_id))
    return match.group(1), match.group(2), int(match.group(3))


def correction(previous: dict, cause: str, delta: dict, author: str, reviewer: str) -> dict:
    if cause not in CORRECTION_CAUSES:
        raise DwrError("correction_cause_unknown", cause)
    if not delta:
        raise DwrError("correction_without_delta")
    if not author or not reviewer:
        raise DwrError("correction_needs_author_and_reviewer")
    start, end, revision = parse_edition_id(previous["edition_id"])
    return {"edition_id": f"{start}_{end}-r{revision + 1}", "supersedes": previous["edition_id"], "cause": cause,
            "delta": delta, "author": author, "reviewer": reviewer, "status": "candidate_not_reviewed",
            "published_at": None, "is_growth": False}


def latest_pointer(editions: list[dict]) -> str | None:
    published = [e for e in editions if e.get("status") == "published" and e.get("published_at") and e.get("reviewed")]
    if not published:
        return None
    current = [e for e in published if not e.get("superseded_by")]
    chosen = sorted(current or published, key=lambda e: (e["period_end_exclusive"], parse_edition_id(e["edition_id"])[2]))
    return chosen[-1]["edition_id"]


def apply_run(status: dict, outcome: str, *, new_data_date: str | None = None) -> dict:
    """Return the new operation status after a preparation run."""
    allowed = ("new_data", "unchanged", "source_unavailable", "validation_failed", "awaiting_review")
    if outcome not in allowed:
        raise DwrError("operation_state_unknown", outcome)
    updated = dict(status)
    updated["last_run_state"] = outcome
    if outcome == "new_data":
        if not new_data_date or new_data_date <= (status.get("latest_available_data_date") or ""):
            raise DwrError("new_data_without_newer_date")
        updated["latest_available_data_date"] = new_data_date
        updated["candidate_state"] = "awaiting_review"
    elif outcome in ("unchanged", "source_unavailable", "validation_failed"):
        updated["latest_available_data_date"] = status.get("latest_available_data_date")
        updated["latest_published_edition"] = status.get("latest_published_edition")
        if outcome == "source_unavailable":
            updated["source_state"] = "source_unavailable"
    return updated


def series_for_failed_source(previous_series: list[dict]) -> list[dict]:
    """A failed source never becomes zeros: the previous values are kept and flagged."""
    return [{**row, "observation_status": row.get("observation_status", "observed"), "source_state": "source_unavailable"}
            for row in previous_series]


def add_windows(windows: list[dict]) -> int:
    if any(w.get("type") == "rolling_30d" for w in windows) and len(windows) > 1:
        raise DwrError("rolling_windows_not_additive")
    ordered = sorted(windows, key=lambda w: w["start"])
    for first, second in zip(ordered, ordered[1:]):
        if second["start"] < first["end_exclusive"]:
            raise DwrError("overlapping_windows_not_additive")
    return sum(w["count"] for w in windows)


def comparable(first: dict, second: dict) -> tuple[bool, list[str]]:
    reasons = []
    for key in COMPARABILITY_KEYS:
        a = first.get("versions", {}).get(key, first.get(key))
        b = second.get("versions", {}).get(key, second.get(key))
        if a != b:
            reasons.append(f"{key}: {a} vs {b}")
    for edition in (first, second):
        if edition.get("coverage_status") not in (None, "partial_declared", "complete_declared"):
            reasons.append(f"coverage {edition.get('coverage_status')}")
    return not reasons, reasons


def growth(previous_count, current_count, comparable_editions: bool):
    if previous_count in (None, 0) or not comparable_editions:
        return {"value": None, "status": "not_calculable"}
    return {"value": (current_count - previous_count) / previous_count, "status": "calculated"}


def receipt_valid(approved_digest: str, candidate_digest: str) -> bool:
    return bool(approved_digest) and approved_digest == candidate_digest

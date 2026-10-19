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
                      "classifier_recorded", "measurement_epoch_id", "scope_registry_sha256", "source_provenance", "time_granularity")


def parse_edition_id(edition_id: str) -> tuple[str, str, int]:
    if not isinstance(edition_id, str):
        raise DwrError("edition_id_invalid", "expected text")
    match = EDITION_ID.match(edition_id)
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


def payload_manifest(edition_id: str, root=None) -> dict:
    """Seal edition payload and figure bytes. Receipts/pointers are outside this scope.

    SHA256SUMS is a derived manifest, not signed content. Operational states and
    repository landing pages are not included and must not claim payload approval.
    """
    from .common import REPO_ROOT, sha256_file, canonical_json, sha256_bytes
    root = root or REPO_ROOT
    parse_edition_id(edition_id)
    files = {}
    for prefix in (f"data/editions/{edition_id}", f"figures/{edition_id}"):
        directory = root / prefix
        if not directory.is_dir():
            raise DwrError("approval_payload_missing")
        for path in sorted(directory.rglob("*")):
            if path.is_symlink():
                raise DwrError("approval_symlink_refused")
            if path.is_file() and path.name != "SHA256SUMS.txt":
                files[path.relative_to(root).as_posix()] = sha256_file(path)
    if not files:
        raise DwrError("approval_payload_empty")
    return {"scope": "edition_payload_and_figures", "files": files,
            "digest": sha256_bytes(canonical_json(files).encode("utf-8"))}


def approved(entry: dict, digest_of=None) -> bool:
    if not isinstance(entry, dict):
        return False
    receipt = entry.get("approval_receipt")
    if not isinstance(receipt, dict) or entry.get("reference_release_status") != "approved":
        return False
    if entry.get("availability_status") != "publicly_accessible" or not entry.get("approved_release_at"):
        return False
    if not isinstance(receipt.get("decisions"), dict):
        return False
    if (receipt.get("edition_id") != entry.get("edition_id") or
            receipt.get("scope") != "edition_payload_and_figures" or not receipt.get("reviewer") or
            not receipt.get("evidence") or not receipt.get("reviewed_at") or
            any(receipt.get("decisions", {}).get(k) != "approved" for k in ("technical", "editorial", "distribution"))):
        return False
    if not isinstance(receipt.get("reviewer"), str) or not receipt["reviewer"].strip():
        return False
    evidence = receipt.get("evidence")
    if not isinstance(evidence, list) or not evidence or any(not isinstance(v, str) or not v.strip() for v in evidence):
        return False
    try:
        start, end, revision = parse_edition_id(entry["edition_id"])
        reviewed = review_date(receipt["reviewed_at"])
        released = review_date(entry["approved_release_at"])
        if reviewed < review_date(end) or released < reviewed:
            return False
        if entry.get("generated_at") and reviewed < review_date(entry["generated_at"]):
            return False
        from .dates import window_from_strings
        window_from_strings(start, end)
        if revision < 1 or entry.get("period_end_exclusive") != end:
            return False
        actual = digest_of(entry["edition_id"]) if digest_of else payload_manifest(entry["edition_id"])["digest"]
        return receipt_valid(receipt.get("content_digest"), actual)
    except (DwrError, OSError, KeyError, TypeError, ValueError):
        return False


def latest_pointer(editions: list[dict], digest_of=None) -> str | None:
    eligible = [e for e in editions if approved(e, digest_of)]
    if not eligible:
        return None
    # A proposed superseding candidate does not hide the last valid approved edition.
    superseded = {e.get("supersedes") for e in eligible}
    current = [e for e in eligible if e["edition_id"] not in superseded]
    chosen = max(current or eligible, key=lambda e: (e["period_end_exclusive"], parse_edition_id(e["edition_id"])[2]))
    return chosen["edition_id"]


def apply_run(status: dict, outcome: str, *, new_data_date: str | None = None, run_at: str | None = None) -> dict:
    """Return the new operation status after a preparation run."""
    allowed = ("new_data", "unchanged", "source_unavailable", "validation_failed", "awaiting_review")
    if outcome not in allowed:
        raise DwrError("operation_state_unknown", outcome)
    updated = dict(status)
    updated["last_run_state"] = outcome
    if run_at:
        updated["last_run_at"] = run_at
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
    """Missing metadata are not equality evidence. Raw unequal-duration counts differ."""
    from .dates import window_from_strings
    reasons = []
    for key in COMPARABILITY_KEYS:
        a = first.get("versions", {}).get(key, first.get(key))
        b = second.get("versions", {}).get(key, second.get(key))
        unresolved = lambda value: value in (None, "", "unknown", "mixed_epoch_unresolved") or (isinstance(value, list) and (not value or any(v in (None, "", "unknown", "mixed_epoch_unresolved") for v in value)))
        if unresolved(a) or unresolved(b):
            reasons.append(f"missing_or_unresolved:{key}")
        elif a != b:
            reasons.append(f"changed:{key}")
    lengths = []
    for edition in (first, second):
        if edition.get("coverage_status") != "complete_declared":
            reasons.append("coverage_not_complete:raw_comparison_not_qualified")
        dates = edition.get("dates", edition)
        try:
            lengths.append(window_from_strings(dates["period_start_inclusive"], dates["period_end_exclusive"]).days)
        except (KeyError, DwrError, TypeError):
            reasons.append("window_missing_or_invalid")
    if len(lengths) == 2 and lengths[0] != lengths[1]:
        reasons.append("unequal_calendar_days:raw_counts_not_equal_exposure")
    if first.get("edition_id") and first.get("edition_id") != second.get("edition_id") and first.get("dates", first).get("period_start_inclusive") == second.get("dates", second).get("period_start_inclusive"):
        reasons.append("revision_not_temporal_growth")
    return not reasons, sorted(set(reasons))


def growth(previous_count, current_count, comparable_editions: bool):
    if previous_count in (None, 0) or current_count is None or not comparable_editions:
        return {"value": None, "status": "not_calculable"}
    return {"value": (current_count - previous_count) / previous_count, "status": "calculated"}


def receipt_valid(approved_digest: str, candidate_digest: str) -> bool:
    return bool(isinstance(approved_digest, str) and re.fullmatch(r"[0-9a-f]{64}", approved_digest)) and approved_digest == candidate_digest


def review_date(value):
    """Explicit ISO date or timezone-aware instant, never a guessed local timezone."""
    from datetime import datetime, timezone
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2}))?", value):
        raise ValueError("review_date_invalid")
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return stamp.replace(tzinfo=timezone.utc) if len(value) == 10 else stamp.astimezone(timezone.utc)


MUTABLE_CATALOG_FIELDS = ("status", "availability_status", "reference_release_status", "scientific_review_status",
                          "approval_receipt", "approved_release_at", "review_status", "superseded_by")


def strip_operational_state(catalog):
    """Version 2 catalog is a citation anchor; mutable decisions live outside it."""
    for key in MUTABLE_CATALOG_FIELDS:
        catalog.pop(key, None)
    for key in ("published_at", "next_review_target"):
        catalog.get("dates", {}).pop(key, None)
    for item in catalog.get("files", []):
        item.pop("status", None)
        item["table_state"] = "metadata" if item.get("rows") is None else "empty" if item["rows"] == 0 else "populated"
    catalog["schema_version"] = "dwr-catalog/2.0.0"
    catalog["operational_state_source"] = "config/editions.json"
    return catalog


def status_label(entry, lang, *, scientific=True):
    """Human state from the external registry, with cryptographic receipt validation."""
    fr = lang == "fr"
    availability = {"local_candidate": ("local candidate", "candidate locale"),
                    "private_candidate": ("private candidate", "candidate privée"),
                    "publicly_accessible": ("publicly accessible", "accessible publiquement")}
    label = availability.get(entry.get("availability_status"), ("availability unknown", "disponibilité inconnue"))[fr]
    valid = approved(entry)
    reference = ("reference approved", "référence approuvée") if valid else (("reference approval invalid", "approbation de référence invalide") if entry.get("reference_release_status") == "approved" else ("reference not approved", "référence non approuvée"))
    parts = [label, reference[fr]]
    if scientific:
        parts.append(("no independent scientific review documented", "aucune évaluation scientifique indépendante documentée")[fr] if entry.get("scientific_review_status") in ("no_independent_scientific_review_documented", "not_independently_scientifically_reviewed") else ("scientific review: see edition registry", "revue scientifique : voir le registre des éditions")[fr])
    return "; ".join(parts)

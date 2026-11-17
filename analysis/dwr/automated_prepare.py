"""Offline, private-only preparation of the automated contract in a new workspace.

No acquisition, publication, edition registration, legacy cursor update or
policy activation. Native next-input admission remains mandatory.
"""
from datetime import datetime, timezone
from pathlib import Path
import os
import shutil
import tempfile
from . import automated, automated_render, dates, disclosure, measurement, next_inputs
from .common import REPO_ROOT, DwrError, canonical_json, load_json, sha256_bytes, sha256_file, write_json
from .maintenance import atomic_json, projection_inputs, retry_sharing_violation, validate_inputs
from .write_guard import checked_path, fingerprint


def private_workspace(value):
    private = Path(value).absolute()
    for part in (private, *private.parents):
        if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
            raise DwrError("automated_private_link_refused")
        if (part / ".git").exists():
            raise DwrError("private_root_inside_git_repository")
    if not private.is_dir():
        raise DwrError("private_root_unavailable")
    if (private / "preparation/candidates").exists():
        raise DwrError("automated_requires_separate_private_workspace")
    return private


def input_manifest(private):
    result = {}
    for folder in ("acquisition", "lock", "sources", "working"):
        path = checked_path(private, private / folder)
        for name, digest in (fingerprint(path) or {}).items():
            result["private/" + folder + "/" + name] = digest
    for folder in ("analysis/dwr", "config"):
        for path in sorted((REPO_ROOT / folder).rglob("*")):
            if path.is_file() and path.suffix in (".py", ".json", ".csv"):
                result["code/" + path.relative_to(REPO_ROOT).as_posix()] = sha256_file(path)
    return result


def prepare(value, now=None):
    private = private_workspace(value)
    folder = checked_path(private, private / "automated")
    folder.mkdir(exist_ok=True)
    lock = checked_path(private, folder / "preparation.lock")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise DwrError("automated_preparation_busy") from error
    os.close(fd)
    try:
        return _prepare(private, now or datetime.now(timezone.utc))
    finally:
        lock.unlink()


def _prepare(private, now):
    if now.tzinfo is None:
        raise DwrError("naive_datetime_refused")
    period = next_inputs.window(private)
    calendar = load_json(REPO_ROOT / "config/edition-calendar.json")
    if not dates.consolidation_ready(period, now, calendar["consolidation_delay_hours"]):
        raise DwrError("next_window_not_consolidated")
    edition = period.edition_id(1)
    working = checked_path(private, private / "working" / edition)
    manifest = input_manifest(private)
    normalized = load_json(checked_path(private, working / "normalized.json"))
    qualified = load_json(checked_path(private, working / "qualified.json"))
    if normalized.get("edition_id") != edition or qualified.get("edition_id") != edition:
        raise DwrError("source_edition_mismatch")
    # Never use a caller's marker, a diagnostic ZIP, or existing aggregate tables
    # as an alternative admission path. This recomputes from the accepted receipts.
    next_inputs.verify_preparation_inputs(private, normalized, qualified)
    validate_inputs(normalized, qualified, period)
    if input_manifest(private) != manifest:
        raise DwrError("automated_inputs_changed_during_admission")
    evidence = automated.coverage_evidence(normalized["archive_inventory"]["days"], period)
    document = automated.project(normalized["joint_rows"], qualified["resources"], window=period,
                                 evidence=evidence, provenance=normalized.get("measurement_provenance", {}))
    digest = sha256_bytes(canonical_json({"contract": automated.CONTRACT, "files": manifest}).encode("utf-8"))
    parent = checked_path(private, private / "automated/candidates")
    target = checked_path(private, parent / edition)
    receipt_path = checked_path(private, target / "preparation-receipt.json")
    if target.exists():
        if not receipt_path.is_file():
            raise DwrError("incomplete_candidate_requires_inspection")
        receipt = load_json(receipt_path)
        if (receipt.get("contract") != automated.CONTRACT or receipt.get("input_digest") != digest
                or receipt.get("input_manifest") != manifest):
            raise DwrError("existing_candidate_changed_inputs_requires_revision")
        if any(receipt.get(k) is not False for k in ("distribution_authorized", "public_mutation", "planning_activated", "legacy_cursor_changed")):
            raise DwrError("automated_receipt_approval_invalid")
        actual = fingerprint(target)
        actual.pop("preparation-receipt.json")
        if actual != receipt.get("files"):
            raise DwrError("existing_candidate_bytes_changed")
        # Verify against fresh source-derived bytes, not an edited candidate plus
        # a newly forged self-consistent manifest/receipt.
        automated_render.verify(target / "projection", document)
        if input_manifest(private) != manifest:
            raise DwrError("automated_inputs_changed_during_preparation")
        state_path = checked_path(private, private / "automated/status.json")
        state = _result(edition, "new_private_candidate")
        if not state_path.is_file() or load_json(state_path) != state:
            atomic_json(state_path, state)
        return _result(edition, "unchanged")
    parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".staging-", dir=parent))
    installed = False
    try:
        output = stage / "projection"
        output.mkdir()
        for name, content in automated_render.files(document).items():
            path = checked_path(stage, output / name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        verification = automated_render.verify(output, document)
        diagnostics = stage / "diagnostics"
        diagnostics.mkdir()
        admitted, _, excluded = projection_inputs(normalized, qualified)
        measured = measurement.qualify(admitted["joint_rows"], normalized["archive_inventory"]["days"],
                                       normalized.get("measurement_provenance", {}))
        # Private measurement diagnostics may contain all-source metadata. This
        # directory is never part of the closed projection manifest or renderer.
        write_json(diagnostics / "source-exclusions.private.json", excluded)
        write_json(diagnostics / "measurement-report.private.json", {k: v for k, v in measured.items() if k != "rows"})
        history = disclosure.inventory()
        decision = automated.validate(document)
        write_json(diagnostics / "disclosure-report.private.json", {**decision,
            "historical_inventory_status": history["status"], "historical_releases_considered": len(history.get("releases", [])),
            "release_review_status": "not_performed", "distribution_authorized": False,
            "prior_policy_unchanged": True, "projection_verification": verification})
        write_json(diagnostics / "delta-report.private.json", {**document["comparison"],
            "reasons": ["different_population_contract", "source_comparability_not_qualified"], "is_growth": False})
        if input_manifest(private) != manifest:
            raise DwrError("automated_inputs_changed_during_preparation")
        files = fingerprint(stage)
        write_json(stage / "preparation-receipt.json", {
            "contract": automated.CONTRACT, "edition_id": edition, "input_digest": digest, "input_manifest": manifest,
            "files": files, "preparation_status": "complete_private", "state": "distribution_blocked_pending_release_review",
            "distribution_authorized": False, "public_mutation": False, "planning_activated": False,
            "legacy_cursor_changed": False, "prepared_at": now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")})
        retry_sharing_violation(os.rename, stage, target)
        installed = True
        # State is separate from preparation/status.json, leaving its cursor intact.
        atomic_json(private / "automated/status.json", _result(edition, "new_private_candidate"))
        return _result(edition, "new_private_candidate")
    finally:
        if not installed and stage.exists():
            checked_path(private, stage)
            if stage.parent != parent or not stage.name.startswith(".staging-"):
                raise DwrError("automated_cleanup_outside_stage")
            retry_sharing_violation(shutil.rmtree, stage)


def _result(edition, outcome):
    return {"contract": automated.CONTRACT, "edition_id": edition, "outcome": outcome,
            "preparation_status": "complete_private", "state": "distribution_blocked_pending_release_review",
            "public_mutation": False, "distribution_authorized": False, "planning_activated": False,
            "legacy_cursor_changed": False}

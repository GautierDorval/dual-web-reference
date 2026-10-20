"""One admission rule for edition writers, and recoverable local transactions.

This prevents ordinary commands from replacing exposed editions. It does not
authenticate an administrator who can rewrite code and every trust registry.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
import os
import shutil
import tempfile

from .common import DwrError, canonical_json, load_json, sha256_file, write_json
from .edition_rules import parse_edition_id
from .dates import window_from_strings

_owner = ContextVar("edition_transaction", default=None)
REGISTRIES = ("editions.json", "historical-editions.json", "publication-inventory.json")


def checked_path(root, path):
    root, path = Path(root).absolute(), Path(path).absolute()
    if not path.is_relative_to(root):
        raise DwrError("edition_path_outside_root")
    for part in (root, *reversed(path.parents), path):
        if part != root and not part.is_relative_to(root):
            continue
        if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
            raise DwrError("edition_link_or_junction_refused")
    if not path.resolve().is_relative_to(root.resolve()):
        raise DwrError("edition_path_outside_root")
    return path


def state(root, edition_id):
    start, end, revision = parse_edition_id(edition_id)
    if revision < 1 or window_from_strings(start, end).edition_id(revision) != edition_id:
        raise DwrError("edition_id_invalid")
    try:
        config, history, inventory = [
            load_json(checked_path(root, Path(root) / "config" / name)) for name in REGISTRIES
        ]
        rows = config["editions"]
        if not isinstance(rows, list) or any(not isinstance(e, dict) for e in rows):
            raise ValueError()
        ids = [e["edition_id"] for e in rows]
        if len(set(ids)) != len(ids):
            raise ValueError()
        matches = [e for e in rows if e["edition_id"] == edition_id]
        if len(matches) != 1:
            raise DwrError("edition_unknown")
        entry = matches[0]
        if (entry["period_start_inclusive"], entry["period_end_exclusive"], entry["revision"]) != (start, end, revision):
            raise ValueError()
        if not isinstance(history["editions"], dict):
            raise ValueError()
        if (inventory.get("status") != "complete_for_named_repository_history"
                or not isinstance(inventory["releases"], list) or not inventory["releases"]
                or not isinstance(inventory["historical_states"], list)
                or len(inventory["historical_states"]) != inventory["historical_states_count"]):
            raise ValueError()
        exposed = {e["edition_id"] for e in inventory["releases"] + inventory["historical_states"]}
        if any(not isinstance(e, str) for e in exposed):
            raise ValueError()
        immutable = (edition_id in history["editions"] or edition_id in exposed
                     or entry.get("historical_payload_frozen") is True
                     or entry.get("availability_status") == "publicly_accessible"
                     or entry.get("reference_release_status") == "approved")
        return entry, immutable
    except (KeyError, TypeError, ValueError) as exc:
        raise DwrError("edition_registry_invalid") from exc


def admit(root, edition_id):
    entry, immutable = state(root, edition_id)
    if immutable:
        raise DwrError("public_or_historical_edition_immutable")
    if (entry.get("availability_status") != "local_candidate"
            or entry.get("reference_release_status") != "not_approved"
            or entry.get("approval_receipt") is not None
            or entry.get("approved_release_at") is not None
            or entry.get("published_at") is not None):
        raise DwrError("edition_target_not_local_unapproved")
    for prefix in ("data/editions", "figures"):
        fingerprint(checked_path(root, Path(root) / prefix / edition_id))
    return entry


def fingerprint(directory):
    if directory.is_symlink() or (hasattr(directory, "is_junction") and directory.is_junction()):
        raise DwrError("edition_link_or_junction_refused")
    if not directory.exists():
        return None
    if not directory.is_dir():
        raise DwrError("edition_destination_not_directory")
    return {p.relative_to(directory).as_posix(): sha256_file(p)
            for p in sorted(directory.rglob("*"))
            if checked_path(directory, p).is_file()}


def assert_readable(root, edition_id):
    lock = checked_path(root, Path(root) / ".dwr-work" / (edition_id + ".lock"))
    if lock.exists() and _owner.get() != (str(Path(root)), edition_id):
        raise DwrError("edition_transaction_incomplete_or_busy")


@contextmanager
def transaction(root, edition_id, *, fresh_payload=False, fresh_figures=False):
    """Stage both trees, then install under an exclusive cooperative lock.

    A caught failure rolls back. Process termination leaves the lock and recovery
    journal; readers refuse that edition until its owner inspects the journal.
    The two directory renames are not claimed to be one filesystem transaction.
    Full rebuilds start with empty staged trees so obsolete outputs cannot survive.
    """
    root = Path(root)
    admit(root, edition_id)
    work = checked_path(root, root / ".dwr-work")
    work.mkdir(exist_ok=True)
    lock = work / (edition_id + ".lock")
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise DwrError("edition_transaction_incomplete_or_busy") from exc
    stage = None
    token = _owner.set((str(root), edition_id))
    completed = False
    backed_up, installed = [], []
    targets = [root / prefix / edition_id for prefix in ("data/editions", "figures")]
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(canonical_json({"edition_id": edition_id, "state": "building"}))
        admit(root, edition_id)
        registry_hashes = {name: sha256_file(root / "config" / name) for name in REGISTRIES}
        before = [fingerprint(p) for p in targets]
        stage = Path(tempfile.mkdtemp(prefix=edition_id + "-", dir=work))
        write_json(lock, {"edition_id": edition_id, "state": "building", "staging": stage.name})
        for index, target in enumerate(targets):
            output = stage / ("payload" if index == 0 else "figures")
            fresh = fresh_payload if index == 0 else fresh_figures
            if target.exists() and not fresh:
                shutil.copytree(target, output)
            else:
                output.mkdir()
        yield stage
        admit(root, edition_id)
        if (registry_hashes != {n: sha256_file(root / "config" / n) for n in REGISTRIES}
                or before != [fingerprint(p) for p in targets]):
            raise DwrError("edition_destination_changed")
        for name in ("payload", "figures"):
            fingerprint(stage / name)
        write_json(stage / "recovery.json", {"edition_id": edition_id, "state": "installing",
                                            "original": before})
        for index, target in enumerate(targets):
            checked_path(root, target)
            target.parent.mkdir(parents=True, exist_ok=True)
            if fingerprint(target) != before[index]:
                raise DwrError("edition_destination_changed")
            if target.exists():
                os.replace(target, stage / f"backup-{index}")
                backed_up.append(index)
                if fingerprint(stage / f"backup-{index}") != before[index]:
                    raise DwrError("edition_destination_changed")
            # The lock serializes cooperative writers. Windows rename also refuses
            # a new destination; POSIX can replace an empty directory in this gap.
            # Arbitrary writers ignoring the lock are outside this transaction contract.
            source = stage / ("payload" if index == 0 else "figures")
            os.rename(source, target)
            installed.append(index)
        completed = True
    except BaseException:
        if stage is not None:
            for index in reversed(installed):
                target = targets[index]
                checked_path(root, target)
                os.rename(target, stage / f"failed-{index}")
            for index in reversed(backed_up):
                os.rename(stage / f"backup-{index}", targets[index])
        completed = True
        raise
    finally:
        _owner.reset(token)
        if completed:
            if stage is not None:
                shutil.rmtree(stage)
            lock.unlink()

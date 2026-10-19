"""Historical payloads are checked, never silently rewritten by current transformers."""
from .common import REPO_ROOT, DwrError, load_json, sha256_file, safe_relative

def entry(edition_id):
    path = REPO_ROOT / "config/historical-editions.json"
    return load_json(path)["editions"].get(edition_id) if path.is_file() else None

def verify(edition_id):
    record = entry(edition_id)
    if not record:
        return None
    for name, digest in record["files"].items():
        path = safe_relative(REPO_ROOT, name)
        if not path.is_file() or sha256_file(path) != digest:
            raise DwrError("historical_payload_changed", name)
    expected = set(record["files"])
    actual = {p.relative_to(REPO_ROOT).as_posix() for prefix in
              (f"data/editions/{edition_id}", f"figures/{edition_id}", record["rules_directory"])
              for p in (REPO_ROOT / prefix).rglob("*") if p.is_file()}
    if expected != actual:
        raise DwrError("historical_payload_file_set_changed")
    return {"edition_id": edition_id, "status": "historical_bytes_verified", "files": len(expected),
            "scope": "Original payload and sealed rule bytes; no current-style regeneration or collection audit."}

def refuse_write(edition_id):
    if entry(edition_id):
        verify(edition_id)
        raise DwrError("historical_edition_immutable", "prepare a distinct candidate revision")

def rule_path(edition_id, name):
    record = entry(edition_id)
    return REPO_ROOT / (record["rules_directory"] if record else "config") / name

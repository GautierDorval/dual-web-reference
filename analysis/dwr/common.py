"""Shared, defensive I/O helpers.

All inputs (exports, acquisitions, snapshots, configuration) are untrusted data.
Readers enforce size, depth and shape limits; writers produce canonical UTF-8 with
LF line endings so that two runs on the same inputs give identical bytes.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
from pathlib import Path
from typing import Any, Iterable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]

MAX_JSON_BYTES = 32 * 1024 * 1024
MAX_JSON_DEPTH = 40
MAX_CSV_BYTES = 64 * 1024 * 1024
MAX_FIELD_CHARS = 4096

SITE_IDS = ("gautierdorval.com", "pagup.com", "better-robots.com")
HTTP_METHODS = ("GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH", "DELETE", "OTHER")
ACTOR_ROLES = (
    "ai_training",
    "ai_search",
    "user_initiated_fetch",
    "search_indexing",
    "seo_tool",
    "generic_automation",
    "unknown",
)
IDENTITY_TIERS = (
    "cryptographically_verified_actor",
    "provider_origin_verified_actor",
    "network_verified_claimed_actor",
    "cloudflare_verified_unattributed",
    "claimed_actor_unverified",
    "unknown_automation",
    "synthetic_probe",
    "spoofed_or_failed_verification",
)
PATH_PATTERN = re.compile(r"^/[\x21-\x7e]{0,511}$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class DwrError(Exception):
    """A failure that must stop the stage explicitly (never a silent zero)."""

    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _check_depth(value: Any, depth: int = 0) -> None:
    if depth > MAX_JSON_DEPTH:
        raise DwrError("json_too_deep")
    if isinstance(value, dict):
        for item in value.values():
            _check_depth(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _check_depth(item, depth + 1)


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise DwrError("json_duplicate_key", key)
        result[key] = value
    return result


def load_json_bytes(data: bytes, *, max_bytes: int = MAX_JSON_BYTES) -> Any:
    if len(data) > max_bytes:
        raise DwrError("json_too_large", f"{len(data)} bytes")
    try:
        text = data.decode("utf-8-sig")
        value = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except UnicodeDecodeError as error:
        raise DwrError("json_not_utf8", str(error)) from error
    except json.JSONDecodeError as error:
        raise DwrError("json_invalid_or_truncated", str(error)) from error
    _check_depth(value)
    return value


def load_json(path: Path, *, max_bytes: int = MAX_JSON_BYTES) -> Any:
    path = Path(path)
    if not path.is_file():
        raise DwrError("source_unavailable", str(path.name))
    if path.stat().st_size > max_bytes:
        raise DwrError("json_too_large", path.name)
    return load_json_bytes(path.read_bytes(), max_bytes=max_bytes)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def write_text(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def write_json(path: Path, value: Any) -> None:
    write_text(path, canonical_json(value))


def read_csv(path: Path, *, max_bytes: int = MAX_CSV_BYTES) -> list[dict[str, str]]:
    path = Path(path)
    if not path.is_file():
        raise DwrError("source_unavailable", path.name)
    data = path.read_bytes()
    if len(data) > max_bytes:
        raise DwrError("csv_too_large", path.name)
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise DwrError("csv_not_utf8", path.name) from error
    reader = csv.DictReader(io.StringIO(text, newline=""))
    if reader.fieldnames is None:
        raise DwrError("csv_empty_without_header", path.name)
    if len(set(reader.fieldnames)) != len(reader.fieldnames):
        raise DwrError("csv_duplicate_column", path.name)
    rows = []
    for row in reader:
        if None in row or any(value is None for value in row.values()):
            raise DwrError("csv_ragged_row", f"{path.name}:{reader.line_num}")
        for value in row.values():
            if len(value) > MAX_FIELD_CHARS:
                raise DwrError("csv_field_too_long", f"{path.name}:{reader.line_num}")
        rows.append(row)
    return rows


def csv_text(fieldnames: Sequence[str], rows: Iterable[dict[str, Any]]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(fieldnames), lineterminator="\n",
                            quoting=csv.QUOTE_MINIMAL, extrasaction="raise")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: _csv_value(row.get(key)) for key in fieldnames})
    return buffer.getvalue()


def _csv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return format(value, ".6f").rstrip("0").rstrip(".")
    return str(value)


def write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[dict[str, Any]]) -> None:
    write_text(path, csv_text(fieldnames, rows))


SPREADSHEET_TRIGGERS = ("=", "+", "-", "@", "\t", "\r")


def spreadsheet_safe(value: str) -> str:
    """Neutralize formula interpretation for the spreadsheet-oriented copy only.

    The canonical CSV keeps exact values; this escaping is applied to the
    `*.spreadsheet.csv` variants and documented in docs/en/reproduction.md.
    """
    if value and value[0] in SPREADSHEET_TRIGGERS:
        return "'" + value
    return value


def validate_path(path: str) -> str:
    if not isinstance(path, str) or not PATH_PATTERN.match(path):
        raise DwrError("path_invalid", repr(path)[:80])
    if "/../" in path or path.endswith("/..") or "\\" in path:
        raise DwrError("path_traversal", path[:80])
    return path


def validate_site(site: str) -> str:
    if site not in SITE_IDS:
        raise DwrError("site_not_allowed", repr(site)[:80])
    return site


def private_root(explicit: str | None = None) -> Path:
    value = explicit or os.environ.get("DWR_PRIVATE_ROOT")
    if not value:
        raise DwrError("private_root_missing", "set DWR_PRIVATE_ROOT or pass --private-root")
    root = Path(value).resolve()
    if not root.is_dir():
        raise DwrError("private_root_unavailable", str(root.name))
    try:
        root.relative_to(REPO_ROOT)
    except ValueError:
        return root
    raise DwrError("private_root_inside_public_repository")


def safe_relative(base: Path, candidate: str) -> Path:
    """Resolve `candidate` under `base`, refusing absolute paths and traversal."""
    if not candidate or candidate.startswith(("/", "\\")) or ":" in candidate:
        raise DwrError("unsafe_relative_path", candidate[:80])
    parts = Path(candidate).parts
    if any(part in ("..", "") for part in parts):
        raise DwrError("unsafe_relative_path", candidate[:80])
    resolved = (base / candidate).resolve()
    resolved.relative_to(base.resolve())
    return resolved

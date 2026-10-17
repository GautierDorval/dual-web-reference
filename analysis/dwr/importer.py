"""import-existing: verify a local export package and load its marginal tables.

The package is checked against its manifest (size and SHA-256 of every listed
file). The monthly ZIP is opened with traversal, link, count and size limits and
its inner checksums are verified. A matching hash establishes binary identity
only, not the accuracy of the measured events.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

from .common import (
    ACTOR_ROLES, DwrError, IDENTITY_TIERS, SITE_IDS, load_json, load_json_bytes, read_csv,
    sha256_bytes, sha256_file, validate_path, validate_site, write_json,
)
from .dates import parse_date

MAX_ZIP_MEMBERS = 64
MAX_ZIP_TOTAL_BYTES = 64 * 1024 * 1024
MAX_ZIP_RATIO = 200

FILE_COLUMNS = ("domain", "path", "category", "requests", "get200", "head", "not_modified", "errors",
                "days", "get200_days", "provider_ai_get200", "first_date", "last_date", "scope", "url")
ACTOR_COLUMNS = ("domain", "actor_name", "actor_type", "confidence", "requests", "get200", "paths", "days")
DAILY_COLUMNS = ("event_date", "domain", "all_requests", "governance_requests", "governance_get200",
                 "provider_ai_get200")


def verify_manifest(package: Path) -> dict:
    manifest = load_json(package / "MANIFEST.json")
    if manifest.get("hash_algorithm") != "SHA-256" or not isinstance(manifest.get("files"), list):
        raise DwrError("manifest_unsupported")
    seen = set()
    checked = []
    root = package.resolve()
    for entry in manifest["files"]:
        relative = entry.get("path")
        if not isinstance(relative, str) or relative in seen:
            raise DwrError("manifest_path_invalid_or_duplicate", str(relative)[:80])
        seen.add(relative)
        target = (package / relative)
        if target.is_symlink() or root not in target.resolve().parents:
            raise DwrError("manifest_path_outside_package", relative)
        if not target.is_file():
            raise DwrError("source_unavailable", relative)
        size = target.stat().st_size
        digest = sha256_file(target)
        if size != entry.get("bytes") or digest != entry.get("sha256"):
            raise DwrError("hash_or_size_mismatch", relative)
        checked.append({"path": relative, "bytes": size, "sha256": digest})
    return {"package": manifest.get("package"), "version": manifest.get("version"),
            "manifest_sha256": sha256_file(package / "MANIFEST.json"), "files": checked}


def safe_zip_members(data: bytes) -> dict[str, bytes]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as error:
        raise DwrError("zip_invalid", str(error)) from error
    infos = archive.infolist()
    if len(infos) > MAX_ZIP_MEMBERS:
        raise DwrError("zip_too_many_members", str(len(infos)))
    total = 0
    members = {}
    for info in infos:
        name = info.filename
        if info.is_dir():
            continue
        if name.startswith(("/", "\\")) or ":" in name or "\\" in name:
            raise DwrError("zip_absolute_or_drive_path", name[:80])
        if any(part in ("..", "") for part in name.split("/")):
            raise DwrError("zip_traversal", name[:80])
        mode = (info.external_attr >> 16) & 0o170000
        if mode == 0o120000:
            raise DwrError("zip_symlink_refused", name[:80])
        total += info.file_size
        if total > MAX_ZIP_TOTAL_BYTES:
            raise DwrError("zip_too_large")
        if info.compress_size and info.file_size / info.compress_size > MAX_ZIP_RATIO:
            raise DwrError("zip_ratio_suspicious", name[:80])
        content = archive.read(info)
        if len(content) != info.file_size:
            raise DwrError("zip_member_truncated", name[:80])
        members[name] = content
    return members


def verify_zip(zip_path: Path) -> dict:
    members = safe_zip_members(zip_path.read_bytes())
    sums_names = [name for name in members if name.endswith("/SHA256SUMS.txt") or name == "SHA256SUMS.txt"]
    if len(sums_names) != 1:
        raise DwrError("zip_checksums_missing")
    prefix = sums_names[0][: -len("SHA256SUMS.txt")]
    listed = {}
    for line in members[sums_names[0]].decode("utf-8").splitlines():
        if not line.strip():
            continue
        digest, _, name = line.partition("  ")
        if len(digest) != 64 or not name or name == "SHA256SUMS.txt":
            raise DwrError("zip_checksum_line_invalid", line[:80])
        listed[name] = digest
    for name, digest in listed.items():
        content = members.get(prefix + name)
        if content is None:
            raise DwrError("zip_listed_member_missing", name)
        if sha256_bytes(content) != digest:
            raise DwrError("zip_member_hash_mismatch", name)
    unlisted = sorted(name[len(prefix):] for name in members if name != sums_names[0] and name[len(prefix):] not in listed)
    if unlisted:
        raise DwrError("zip_unlisted_members", ",".join(unlisted))
    return {"members": sorted(listed), "checksums": listed, "excluded_from_sums": ["SHA256SUMS.txt"]}


def _int(row: dict, key: str, *, minimum: int = 0) -> int:
    value = row.get(key)
    if value is None or not str(value).lstrip("-").isdigit():
        raise DwrError("count_not_integer", f"{key}={value!r}"[:80])
    number = int(value)
    if number < minimum:
        raise DwrError("count_negative", f"{key}={number}")
    return number


def _columns(rows: list[dict], expected: tuple, name: str) -> None:
    if not rows:
        raise DwrError("export_empty", name)
    if tuple(rows[0].keys()) != expected:
        raise DwrError("schema_unknown", name)


def load_marginals(inputs: Path, window_start: str, window_end: str) -> dict:
    start, end = parse_date(window_start), parse_date(window_end)
    files = read_csv(inputs / "fichiers-390-chemins.csv")
    actors = read_csv(inputs / "acteurs-46-groupes.csv")
    daily = read_csv(inputs / "journalier-90-lignes.csv")
    _columns(files, FILE_COLUMNS, "fichiers")
    _columns(actors, ACTOR_COLUMNS, "acteurs")
    _columns(daily, DAILY_COLUMNS, "journalier")
    report = load_json(inputs / "releve-mensuel-complet.json")

    typed_files, keys = [], set()
    for row in files:
        key = (validate_site(row["domain"]), validate_path(row["path"]))
        if key in keys:
            raise DwrError("duplicate_site_path", f"{key}")
        keys.add(key)
        record = {"site_id": key[0], "path": key[1], "producer_category": row["category"],
                  "historical_scope_label": row["scope"]}
        for column in ("requests", "get200", "head", "not_modified", "errors", "days", "get200_days",
                       "provider_ai_get200"):
            record[column] = _int(row, column)
        for column in ("first_date", "last_date"):
            day = parse_date(row[column])
            if not start <= day < end:
                raise DwrError("date_outside_window", f"{column}={row[column]}")
        if record["get200"] > record["requests"] or record["provider_ai_get200"] > record["get200"]:
            raise DwrError("inconsistent_counts", f"{key}")
        typed_files.append(record)

    typed_actors, actor_keys = [], set()
    for row in actors:
        if row["actor_type"] not in ACTOR_ROLES:
            raise DwrError("actor_role_unknown", row["actor_type"])
        if row["confidence"] not in IDENTITY_TIERS:
            raise DwrError("identity_tier_unknown", row["confidence"])
        key = (validate_site(row["domain"]), row["actor_name"], row["actor_type"], row["confidence"])
        if key in actor_keys:
            raise DwrError("duplicate_actor_group", f"{key}")
        actor_keys.add(key)
        typed_actors.append({"site_id": key[0], "actor_name": key[1], "actor_role": key[2],
                             "stored_identity_tier": key[3],
                             **{column: _int(row, column) for column in ("requests", "get200", "paths", "days")}})

    typed_daily, daily_keys = [], set()
    for row in daily:
        day = parse_date(row["event_date"])
        if not start <= day < end:
            raise DwrError("date_outside_window", row["event_date"])
        key = (day.isoformat(), validate_site(row["domain"]))
        if key in daily_keys:
            raise DwrError("duplicate_day_site", f"{key}")
        daily_keys.add(key)
        typed_daily.append({"date_utc": key[0], "site_id": key[1],
                            **{column: _int(row, column) for column in DAILY_COLUMNS[2:]}})
    expected_days = (end - start).days
    if len(typed_daily) != expected_days * len(SITE_IDS):
        raise DwrError("daily_rows_incomplete", f"{len(typed_daily)} rows")

    http = []
    for row in report["http"]:
        if row["method"] not in ("GET", "HEAD", "POST", "OPTIONS", "PUT", "PATCH", "DELETE", "OTHER"):
            raise DwrError("http_method_unknown", str(row["method"]))
        status = int(row["status"])
        if not 100 <= status <= 599:
            raise DwrError("http_status_unknown", str(status))
        http.append({"site_id": validate_site(row["domain"]), "http_method": row["method"], "http_status": status,
                     "requests": _int(row, "requests")})
    tiers = []
    for row in report["identity_tiers"]:
        if row["confidence"] not in IDENTITY_TIERS:
            raise DwrError("identity_tier_unknown", row["confidence"])
        tiers.append({"stored_identity_tier": row["confidence"], "requests": _int(row, "requests"),
                      "get200": _int(row, "get200")})
    archive = []
    for row in report["archive_comparison"]:
        archive.append({"date_utc": parse_date(row["date"]).isoformat(), "aggregate_count": _int(row, "aggregate_count"),
                        "v3_count": _int(row, "v3_count"), "report_status": row["report_status"],
                        "reason_code": row["reason_code"], "is_current": bool(row["current"]),
                        "d1_count": _int(row, "d1_count")})
    registered = [{"site_id": validate_site(row["domain"]), "path": validate_path(row["path"]),
                   "producer_category": row["category"], "window_rows": _int(row, "window_rows")}
                  for row in report["registered_now_without_window_rows"]]
    return {
        "mode": "export_marginals",
        "window": {"start_inclusive": start.isoformat(), "end_exclusive": end.isoformat()},
        "extracted_at": sorted(report["source"]["observed_at"]),
        "source": {key: report["source"][key] for key in ("d1_database", "table", "access", "archive_repo",
                                                           "archive_branch", "archive_commit", "archive_commit_at")},
        "sql_queries": report["sql_queries"],
        "files": sorted(typed_files, key=lambda r: (r["site_id"], r["path"])),
        "actors": sorted(typed_actors, key=lambda r: (r["site_id"], r["actor_name"], r["actor_role"], r["stored_identity_tier"])),
        "daily": sorted(typed_daily, key=lambda r: (r["date_utc"], r["site_id"])),
        "http": sorted(http, key=lambda r: (r["site_id"], r["http_method"], r["http_status"])),
        "identity_tiers": sorted(tiers, key=lambda r: r["stored_identity_tier"]),
        "archive_comparison": sorted(archive, key=lambda r: r["date_utc"]),
        "registered_without_window_rows": sorted(registered, key=lambda r: (r["site_id"], r["path"])),
    }


def import_existing(package: Path, private: Path, window_start: str, window_end: str) -> dict:
    package = Path(package)
    manifest = verify_manifest(package)
    inputs = package / "inputs-internal"
    zips = sorted(inputs.glob("*.zip"))
    zip_receipts = {item.name: verify_zip(item) for item in zips}
    marginals = load_marginals(inputs, window_start, window_end)
    import_id = "imp-" + manifest["manifest_sha256"][:12]
    target = private / "import" / import_id
    write_json(target / "receipt.json", {"import_id": import_id, "manifest": manifest, "zips": zip_receipts,
                                         "scope": "binary identity of the package; not a validation of collection"})
    write_json(target / "marginals.json", marginals)
    return {"import_id": import_id, "files_verified": len(manifest["files"]), "zips": list(zip_receipts),
            "marginals": str(target / "marginals.json")}

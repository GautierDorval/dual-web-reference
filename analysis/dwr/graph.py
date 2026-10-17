"""Deterministic extraction of documentary relations from a source snapshot.

A relation means "this reference is written in this file of this snapshot". It
is not evidence that any client followed it, and absence from this graph means
"not found in this graph", not absence of any reference elsewhere. No URL found
here is ever fetched.
"""

from __future__ import annotations

import json
import posixpath
import re
from pathlib import Path
from urllib.parse import urlsplit

from .common import DwrError, SITE_IDS, load_json, safe_relative, sha256_bytes

MAX_FILE_BYTES = 8 * 1024 * 1024
RELATION_KEYS = {
    "related", "relations", "relation", "rel", "seealso", "see_also", "sameas", "ispartof", "haspart",
    "canonical", "canonical_source", "canonicalsource", "source", "sources", "alternate", "parent",
    "children", "index", "manifest", "governs", "governed_by", "supersedes", "superseded_by",
}
HREF = re.compile(r"<a\b[^>]*?\bhref\s*=\s*(\"([^\"]*)\"|'([^']*)')", re.IGNORECASE)
MD_LINK = re.compile(r"\[[^\]\n]{0,300}\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
AUTOLINK = re.compile(r"<(https?://[^>\s]+)>")
BARE_URL = re.compile(r"https?://[A-Za-z0-9.-]+(?:/[^\s<>\"'`)\]]*)?")
LOC = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.IGNORECASE)


def _site_of(host: str) -> str | None:
    host = (host or "").lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    return host if host in SITE_IDS else None


def normalize_target(site_id: str, source_path: str, raw: str) -> dict | None:
    value = raw.strip()
    if not value or value.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
        return None
    parts = urlsplit(value)
    if parts.scheme in ("http", "https"):
        target_site = _site_of(parts.hostname or "")
        if target_site is None:
            return {"target_site": "external", "target_path": None}
        path = parts.path or "/"
    elif parts.scheme:
        return None
    elif value.startswith("//"):
        target_site = _site_of(urlsplit("https:" + value).hostname or "")
        if target_site is None:
            return {"target_site": "external", "target_path": None}
        path = urlsplit("https:" + value).path or "/"
    else:
        target_site = site_id
        base = posixpath.dirname(source_path) if not source_path.endswith("/") else source_path
        path = parts.path if parts.path.startswith("/") else posixpath.join(base or "/", parts.path)
        if not path:
            return None
    normalized = posixpath.normpath(path)
    if path.endswith("/") and not normalized.endswith("/"):
        normalized += "/"
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    return {"target_site": target_site, "target_path": normalized}


def _line_of(text: str, needle: str) -> int:
    index = text.find(needle)
    return text.count("\n", 0, index) + 1 if index >= 0 else 0


def _walk_json(value, key_path=""):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _walk_json(item, f"{key_path}.{key}" if key_path else str(key))
    elif isinstance(value, list):
        for item in value:
            yield from _walk_json(item, key_path + "[]")
    elif isinstance(value, str):
        yield key_path, value


def _json_candidate(value: str) -> bool:
    if value.startswith(("http://", "https://")):
        return True
    return value.startswith("/") and not value.startswith("//") and " " not in value and len(value) < 300


def relations_in_file(site_id: str, url_path: str, data: bytes, file_name: str = "") -> list[dict]:
    if len(data) > MAX_FILE_BYTES:
        raise DwrError("snapshot_file_too_large", url_path)
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return []
    found = []
    lower = (file_name or url_path).lower()

    def add(raw, relation_type, line, note=""):
        target = normalize_target(site_id, url_path, raw)
        if target:
            found.append({**target, "raw": raw, "relation_type": relation_type, "line": line, "note": note})

    if lower.endswith((".html", "/")) or lower.endswith(".htm"):
        for match in HREF.finditer(text):
            add(match.group(2) if match.group(2) is not None else match.group(3), "html_anchor",
                text.count("\n", 0, match.start()) + 1)
    elif lower.endswith((".json", ".jsonld")):
        try:
            document = json.loads(text)
        except json.JSONDecodeError:
            return []
        for key_path, value in _walk_json(document):
            if not _json_candidate(value):
                continue
            leaf = key_path.split(".")[-1].replace("[]", "").lower().lstrip("@")
            kind = "declared_relation" if leaf in RELATION_KEYS else "json_reference"
            add(value, kind, _line_of(text, json.dumps(value)[1:-1]), f"key={key_path}"[:120])
    elif lower.endswith(".xml"):
        for match in LOC.finditer(text):
            add(match.group(1), "sitemap_entry", text.count("\n", 0, match.start()) + 1)
    else:
        if lower.endswith(".md"):
            for match in HREF.finditer(text):
                add(match.group(2) if match.group(2) is not None else match.group(3), "html_anchor",
                    text.count("\n", 0, match.start()) + 1, "anchor in page template source")
        for number, line in enumerate(text.splitlines(), start=1):
            spans = []
            for match in MD_LINK.finditer(line):
                add(match.group(1), "markdown_link", number)
                spans.append(match.span())
            for match in AUTOLINK.finditer(line):
                add(match.group(1), "markdown_link", number)
                spans.append(match.span())
            for match in BARE_URL.finditer(line):
                if any(start <= match.start() < end for start, end in spans):
                    continue
                add(match.group(0).rstrip(".,;:"), "plain_url_mention", number)
    return found


def extract_site(site_id: str, site_dir: Path) -> dict:
    snapshot = load_json(site_dir / "snapshot.json")
    entries = []
    for item in snapshot.get("files", []):
        entries.append((item["url_path"], item["snapshot_file"], item.get("sha256")))
    for page in snapshot.get("html_pages", []):
        built = page.get("built_html") or {}
        if built.get("snapshot_file"):
            chosen = built
        elif page.get("snapshot_file"):
            chosen = page
        else:
            chosen = page.get("template_source") or {}
        if chosen.get("snapshot_file"):
            entries.append((page["url_path"], chosen["snapshot_file"], chosen.get("sha256")))
    relations, manifest = {}, []
    for url_path, snapshot_file, expected in sorted(set(entries)):
        path = safe_relative(site_dir, snapshot_file)
        data = path.read_bytes()
        digest = sha256_bytes(data)
        if expected and expected != digest:
            raise DwrError("snapshot_hash_mismatch", f"{site_id}{url_path}")
        manifest.append({"url_path": url_path, "sha256": digest})
        for relation in relations_in_file(site_id, url_path, data, snapshot_file):
            key = (url_path, relation["target_site"], relation["target_path"] or relation["raw"], relation["relation_type"])
            if key in relations:
                relations[key]["occurrences"] += 1
                continue
            relations[key] = {"source_site": site_id, "source_path": url_path, "target_site": relation["target_site"],
                              "target_path": relation["target_path"], "relation_type": relation["relation_type"],
                              "evidence_line": relation["line"], "occurrences": 1, "note": relation["note"]}
    repositories = snapshot.get("repositories") or []
    return {"site_id": site_id, "files": manifest,
            "snapshot_digest": sha256_bytes(json.dumps(manifest, sort_keys=True).encode("utf-8")),
            "repositories": repositories, "relations": list(relations.values())}

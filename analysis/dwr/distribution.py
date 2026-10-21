"""Closed distribution surfaces shared by worktree, Git, site and package checks.

Historical authority is the existing reviewed inventory and frozen registry,
identified by their bytes at the documented baseline. No runtime inventory learns
new authority. Mutable config/schema bytes still require their semantic and privacy
checks; membership is not a confidentiality or owner-approval claim.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import unicodedata
from pathlib import Path, PurePosixPath

from .common import DwrError

ROOTS = ("data", "figures", "config", "schemas")
BASELINE_PIN_SHA256 = 'b61fe79d06969098fc97702fd483b5f38eb678e6a1ae13a1c5c44d3e93e4525b'
AUTHORITY_SHA256 = {'config/publication-inventory.json': '66e7c9fb14b0861645ae08bd7bdee166d7a36d543b04239e170d885f5d2b51d1', 'config/historical-editions.json': '3570d9fe824f7842f8a5dbb1745a0ce6a5958b5d422811e0f502f3410fa3740d'}
SOURCE_FILES = frozenset((
    'config/attribution-rules.json',
    'config/cases.json',
    'config/edition-calendar.json',
    'config/editions.json',
    'config/historical-editions.json',
    'config/operations.json',
    'config/producer-classifier-2026-08-24.1.json',
    'config/publication-gate.json',
    'config/publication-inventory.json',
    'config/scope-registry.csv',
    'config/scope-rules.json',
    'config/sites.json',
    'config/small-cell-policy.json',
    'config/workflow-templates/monthly-edition.yml.example',
    'config/workflow-templates/weekly-preparation.yml.example',
    'data/index.json',
    'data/latest.json',
    'data/status.json',
    'schemas/actor-summary.schema.json',
    'schemas/consultations.schema.json',
    'schemas/coverage.schema.json',
    'schemas/daily-family-summary.schema.json',
    'schemas/daily-summary.schema.json',
    'schemas/exclusions.schema.json',
    'schemas/links.schema.json',
    'schemas/metrics.schema.json',
    'schemas/resource-summary.schema.json',
    'schemas/resources.schema.json',
    'schemas/v2/actor-summary.schema.json',
    'schemas/v2/consultations.schema.json',
    'schemas/v2/coverage.schema.json',
    'schemas/v2/daily-family-summary.schema.json',
    'schemas/v2/daily-summary.schema.json',
    'schemas/v2/exclusions.schema.json',
    'schemas/v2/links.schema.json',
    'schemas/v2/resource-summary.schema.json',
    'schemas/v2/resources.schema.json',
))
SOURCE_ONLY = frozenset(('config/workflow-templates/monthly-edition.yml.example', 'config/workflow-templates/weekly-preparation.yml.example'))


def fail(code):
    # File names and raw parse errors can themselves contain private data.
    raise DwrError("distribution_" + code, "closed file contract refused; no detected name or value disclosed")


def canonical_path(name):
    if (not isinstance(name, str) or not name or "\\" in name or name.startswith("/")
            or unicodedata.normalize("NFC", name) != name):
        fail("unsafe_path")
    for part in name.split("/"):
        if (part in ("", ".", "..") or part[-1:] in (" ", ".") or
                any(ord(c) < 32 or c in ':<>"|?*' for c in part) or
                re.fullmatch(r"(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?", part, re.I)):
            fail("unsafe_path")
    return name


def parents(names):
    return {str(p) for name in names for p in PurePosixPath(name).parents if str(p) != "."}


def unique_names(names):
    seen = set()
    for name in names:
        folded = canonical_path(name).casefold()
        if folded in seen:
            fail("path_collision")
        seen.add(folded)


def json_object(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                fail("ambiguous_json")
            result[key] = value
        return result
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=pairs)
    except (UnicodeError, ValueError, RecursionError):
        fail("invalid_json")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def expected(read):
    documents = {}
    for name, checksum in AUTHORITY_SHA256.items():
        data = read(name)
        if sha(data) != checksum:
            fail("historical_authority_changed")
        documents[name] = json_object(data)
    wanted = dict.fromkeys(SOURCE_FILES)
    inventory = documents["config/publication-inventory.json"]
    admitted = set()
    for release in inventory["releases"]:
        if release.get("accessible") is not True:
            fail("edition_not_admitted")
        admitted.add(release["edition_id"])
        wanted.update(release["files"])
    for entry in documents["config/historical-editions.json"]["editions"].values():
        wanted.update(entry["files"])
    unique_names(wanted)
    for name, checksum in wanted.items():
        if name.split("/")[0] not in ROOTS or (checksum is not None and not re.fullmatch('[0-9a-f]{64}', checksum)):
            fail("invalid_contract")
    registry = json_object(read("config/editions.json"))
    entries = registry.get("editions") if isinstance(registry, dict) else None
    if (not isinstance(entries, list) or any(not isinstance(e, dict) or not isinstance(e.get("edition_id"), str) for e in entries)
            or len({e["edition_id"] for e in entries}) != len(entries)):
        fail("edition_registry_ambiguous")
    # A private registry entry cannot add a distributable directory. Historical
    # availability remains authoritative even if a current entry is downgraded.
    if not admitted <= {e.get("edition_id") for e in entries}:
        fail("historical_edition_missing")
    return wanted


def check_set(files, directories, wanted, read):
    """The same exact-set, type-admission and content check for disk and Git."""
    unique_names([*files, *directories])
    if set(files) != set(wanted) or set(directories) != parents(wanted):
        fail("file_set_mismatch")
    contents = {}
    for name, checksum in wanted.items():
        data = read(name)
        if checksum is not None and sha(data) != checksum:
            fail("content_changed")
        if name.endswith(".json"):
            json_object(data)
        contents[name] = data
    return contents


def plain(path, directory=False):
    try:
        info = path.lstat()
        if (stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400
                or not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))):
            fail("entry_type_refused")
    except OSError:
        fail("entry_unavailable")


def read_regular(root, name):
    canonical_path(name)
    plain(root, True)
    current = root
    for part in name.split("/")[:-1]:
        current = current / part
        plain(current, True)
    path = root / name
    plain(path)
    try:
        # fstat plus O_NOFOLLOW where available supplements the cooperative model.
        fd = os.open(path, os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0))
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                fail("entry_type_refused")
            data = stream.read()
        plain(path)
        return data
    except OSError:
        fail("entry_unavailable")


def disk_entries(root, prefixes=None):
    files, directories = set(), set()
    plain(root, True)
    def walk(path):
        plain(path, True)
        try:
            children = list(path.iterdir())
        except OSError:
            fail("entry_unavailable")
        for child in children:
            name = child.relative_to(root).as_posix()
            canonical_path(name)
            try:
                info = child.lstat()
            except OSError:
                fail("entry_unavailable")
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                fail("entry_type_refused")
            if stat.S_ISDIR(info.st_mode):
                directories.add(name)
                walk(child)
            elif stat.S_ISREG(info.st_mode):
                files.add(name)
            else:
                fail("entry_type_refused")
    if prefixes is None:
        walk(root)
    else:
        # Case variants of the protected roots are not additional escape surfaces.
        try:
            children = list(root.iterdir())
        except OSError:
            fail("entry_unavailable")
        for child in children:
            if child.name.casefold() in ROOTS and child.name not in ROOTS:
                fail("path_collision")
        for prefix in prefixes:
            directories.add(prefix)
            walk(root / prefix)
    return files, directories


def check_sources(root):
    read = lambda name: read_regular(root, name)
    wanted = expected(read)
    files, directories = disk_entries(root, ROOTS)
    return check_set(files, directories, wanted, read)


def check_output(root, plan):
    unique_names(plan)
    files, directories = disk_entries(root)
    return check_set(files, directories, {p: sha(b) for p, b in plan.items()},
                     lambda name: read_regular(root, name))


def check_git(entries, read):
    """Entries are (relative path, mode, kind) of one actual Git tree."""
    wanted = expected(read)
    files, directories = set(), set()
    for name, mode, kind in entries:
        first = name.split('/')[0]
        if first.casefold() not in ROOTS:
            continue
        canonical_path(name)
        if kind == 'tree' and mode == '040000':
            directories.add(name)
        elif kind == 'blob' and mode in ('100644', '100755'):
            files.add(name)
        else:
            fail('entry_type_refused')
    return check_set(files, directories, wanted, read)


def check_candidate(payload, figures, edition_id, required, optional):
    """Private generator contract, separate from admission to public roots.

    Optional files are explicitly named; observed extras cannot extend this set.
    New bytes are sealed only after semantic validation in the caller.
    """
    from .common import SITE_IDS
    from .figures import FIGURES
    files, dirs = disk_entries(payload)
    wanted = set(required) | (files & set(optional))
    check_set(files, dirs, dict.fromkeys(wanted), lambda n: read_regular(payload, n))
    ids = set(FIGURES) | {"G09-" + site for site in SITE_IDS}
    expected_figures = {f"{fid}.{lang}{compact}.svg" for fid in ids
                        for lang in ('en', 'fr') for compact in ('', '.compact')}
    expected_figures |= {f"{fid}.csv" for fid in ids}
    files, dirs = disk_entries(figures)
    pngs = {"png/" + name[:-4] + '.png' for name in expected_figures if name.endswith('.svg')}
    wanted = expected_figures | (files & pngs)
    # An explicitly optional PNG container is allowed empty, never other dirs.
    check_set(files, dirs - ({'png'} if not files & pngs else set()), dict.fromkeys(wanted),
              lambda n: read_regular(figures, n))
    registry = json_object(read_regular(payload, 'figures.json'))
    declared = {}
    for figure in registry['figures']:
        for item in [figure['data_table'], *figure['files'].values()]:
            name = canonical_path(item['path'])
            prefix = 'figures/' + edition_id + '/'
            if not name.startswith(prefix) or name[len(prefix):] in declared:
                fail('figure_contract_invalid')
            declared[name[len(prefix):]] = item['sha256']
    if set(declared) != expected_figures:
        fail('figure_contract_changed')
    for name, digest in declared.items():
        if sha(read_regular(figures, name)) != digest:
            fail('content_changed')

"""Licences and citation: every tracked file maps to exactly one row of NOTICE.md, the legal code is the official text,
and CITATION.cff is the file validated with cffconvert 2.0.0 against CFF 1.2.0 on 2026-10-19 (pinned by digest)."""
import fnmatch
import hashlib
import re
import shutil
import subprocess
import unittest

from tests import __init__  # noqa: F401
from dwr.common import REPO_ROOT

# SHA-256 of https://creativecommons.org/licenses/by/4.0/legalcode.txt, retrieved on 2026-10-17.
CC_BY_4_SHA256 = "9ba9550ad48438d0836ddab3da480b3b69ffa0aac7b7878b5a0039e7ab429411"
# SHA-256 of CITATION.cff as validated with cffconvert 2.0.0 (schema 1.2.0) on 2026-10-19.
CITATION_SHA256 = "e5b2b47c947e33185bfc1d6bf4c00e4c07c1ad90b9e163e94ca5f502a964c291"


def licence_rows() -> dict:
    """Rows of the licence table of NOTICE.md: part -> path patterns written between backticks."""
    section = (REPO_ROOT / "NOTICE.md").read_text(encoding="utf-8").split("## Licences\n", 1)[1].split("\n## ", 1)[0]
    rows = {}
    for line in section.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if line.startswith("|") and len(cells) == 3 and cells[0] not in ("Part", "---"):
            rows[cells[0]] = re.findall(r"`([^`]+)`", cells[2])
    return rows


def matches(path: str, pattern: str) -> bool:
    if pattern.endswith("/"):
        return path.startswith(pattern)
    return fnmatch.fnmatchcase(path, pattern) if "*" in pattern else path == pattern


class LicenceTests(unittest.TestCase):
    def test_legal_code_is_the_official_text(self):
        data = (REPO_ROOT / "LICENSES" / "CC-BY-4.0.txt").read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), CC_BY_4_SHA256)

    def test_citation_file_is_the_validated_one(self):
        """A change to CITATION.cff must be validated again with a CFF 1.2.0 validator before this digest is updated."""
        data = (REPO_ROOT / "CITATION.cff").read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), CITATION_SHA256)

    def test_licence_table_has_the_decided_rows(self):
        rows = licence_rows()
        self.assertEqual(set(rows), {"Code", "Documentation", "Data", "Licence texts"})
        self.assertTrue(all(rows.values()))

    @unittest.skipUnless(shutil.which("git") and (REPO_ROOT / ".git").exists(), "needs the Git checkout")
    def test_every_tracked_file_has_exactly_one_licence_row(self):
        rows = licence_rows()
        listed = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=REPO_ROOT, capture_output=True, check=True).stdout
        problems = []
        for path in filter(None, listed.decode("utf-8").split("\0")):
            parts = [part for part, patterns in rows.items() if any(matches(path, p) for p in patterns)]
            if len(parts) != 1:
                problems.append(f"{path}: {parts}")
        self.assertEqual(problems, [])

"""Mutation tests of the publication gate: one counterexample per variant listed in gate.COVERAGE.

Every value below is synthetic and assembled at run time, so that this file carries no
literal the gate itself would flag (the repository's own gate scans this file too).
"""

import json
import ntpath
import os
import shutil
import stat
import struct
import subprocess
import tempfile
import unittest
import zlib
from unittest import mock
from pathlib import Path
from urllib.parse import quote

from tests import __init__  # noqa: F401
from dwr import gate, verify
from dwr.common import REPO_ROOT, canonical_json, load_json

TERM = "example-" + "private-repo"
IDENTIFIER = "fedcba9876543210" * 2
COMMIT = "1234567890abcdef" * 2 + "12345678"
# A synthetic Windows home folder, its 8.3 short name and a workspace tail, assembled so that no marker is literal.
HOME = "C:" + "\\" + "Users" + "\\" + "example.person"
SHORT = "C:" + "\\" + "Users" + "\\" + "EXAMPL~1"
TAIL = "Documents" + "\\" + "Example-Workspace" + "\\" + "private-workspace"
ROOTS = set(gate.local_roots([HOME, SHORT + "\\" + "App" + "Data" + "\\Local\\Temp"])) | {gate.fold_path(TAIL)}
SECRETS = gate.Secrets(terms=[TERM], identifiers=[IDENTIFIER], commits=[COMMIT], roots=ROOTS)
ACTION_SHA = "0123456789abcdef" * 2 + "01234567"
OTHER_40 = "89abcdef01234567" * 2 + "89abcdef"
HEX32_SAMPLE = "abcdef0123456789" * 2
PINS = frozenset({f"actions/checkout@{ACTION_SHA}"})
HAS_GIT = shutil.which("git") is not None


def chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))


def png(*, before=(), iend=b"", trailing=b"", idat_extra=b"", cut=0, bad_crc=False, width=1) -> bytes:
    header = chunk(b"IHDR", struct.pack(">IIBBBBB", width, 1, 8, 2, 0, 0, 0))
    body = header + b"".join(chunk(k, p) for k, p in before) + chunk(b"IDAT", zlib.compress(b"\x00\xff\xff\xff" + idat_extra))
    data = gate.PNG_SIGNATURE + body + chunk(b"IEND", iend) + trailing
    if bad_crc:
        data = data[:-1] + bytes([data[-1] ^ 1])
    return data[:len(data) - cut] if cut else data


WORKFLOW = f"jobs:\n  t:\n    steps:\n      - uses: actions/checkout@{ACTION_SHA} # v4\n"


def base_files() -> dict:
    return {
        "README.md": b"# Test repository\n",
        "data/table.csv": b"site_id,count\nexample.org,3\n",
        "analysis/tool.py": b"VALUE = 1\n",
        ".github/workflows/ci.yml": WORKFLOW.encode(),
        "config/workflow-templates/weekly.yml.example": WORKFLOW.encode(),
        "figures/f.png": png(),
    }


def remove_tree(directory: Path) -> None:
    """Delete a test repository. Git writes its objects read-only, and Windows refuses to delete such files.

    Only a permission refusal to delete a file or a folder that is not a symbolic link is retried, after making it
    writable; any other failure, including the refusal of rmtree to follow a symbolic link, is raised.
    """
    def make_writable(function, path, error):
        if (not isinstance(error, PermissionError) or function not in (os.unlink, os.remove, os.rmdir)
                or os.path.islink(path)):
            raise error
        os.chmod(path, stat.S_IWRITE)
        function(path)
    shutil.rmtree(directory, onexc=make_writable)


def percent(value: str) -> str:
    return "".join(f"%{byte:02X}" for byte in value.encode())


def ip() -> str:
    return ".".join(("203", "0", "113", "7"))


def add(files, name, data):
    return {**files, name: data if isinstance(data, bytes) else data.encode()}


def mutation(files=None, action=None, message="Candidate edition"):
    return {"files": files, "action": action, "message": message}


# (category, counterexample) -> function(base files) -> mutation
MUTATIONS = {
    ("history_not_from_published_root", "second_commit_without_root"): lambda f: mutation(f, "second_commit"),
    ("history_not_from_published_root", "other_root"): lambda f: mutation(f, "other_root"),
    ("history_not_from_published_root", "merge_commit"): lambda f: mutation(f, "named_root_then_merge"),
    ("unsupported_entry", "symlink"): lambda f: mutation(f, "symlink"),
    ("unsupported_entry", "submodule"): lambda f: mutation(f, "submodule"),
    ("file_type_not_admitted", "executable"): lambda f: mutation(add(f, "tool.exe", b"MZ\x00\x01")),
    ("text_not_utf8", "latin1_byte"): lambda f: mutation(add(f, "notes.md", b"caf\xe9\n")),
    ("private_term", "in_file"): lambda f: mutation(add(f, "docs/a.md", f"Built in {TERM}.\n")),
    ("private_term", "uppercase"): lambda f: mutation(add(f, "docs/a.md", f"Built in {TERM.upper()}.\n")),
    ("private_term", "in_path"): lambda f: mutation(add(f, f"docs/{TERM}.md", "x\n")),
    ("private_term", "in_empty_tree_name"): lambda f: mutation(f, ("empty_tree", TERM)),
    ("private_term", "in_commit_message"): lambda f: mutation(f, message=f"Import from {TERM}"),
    ("private_term", "in_png_text_chunk"): lambda f: mutation(
        add(f, "figures/f.png", png(before=((b"tEXt", b"Comment\x00" + TERM.encode()),)))),
    ("private_term", "json_unicode_escaped"): lambda f: mutation(
        add(f, "data/n.json", '{"k": "' + "".join(f"\\u{ord(c):04x}" for c in TERM) + '"}\n')),
    ("private_term", "bom_json_escaped"): lambda f: mutation(
        add(f, "data/n.json", b"\xef\xbb\xbf" + ('{"k": "' + "".join(f"\\u{ord(c):04x}" for c in TERM) + '"}\n').encode())),
    ("private_term", "percent_encoded"): lambda f: mutation(
        add(f, "docs/u.md", f"https://example.org/search?q={percent(TERM)}\n")),
    ("private_identifier", "in_test_file"): lambda f: mutation(add(f, "tests/t.py", f"SAMPLE = '{IDENTIFIER}'\n")),
    ("private_identifier", "uppercase"): lambda f: mutation(add(f, "tests/t.py", f"SAMPLE = '{IDENTIFIER.upper()}'\n")),
    ("private_identifier", "in_path"): lambda f: mutation(add(f, f"data/{IDENTIFIER}.csv", "x\n")),
    ("private_commit", "in_csv"): lambda f: mutation(add(f, "data/b.csv", f"commit_id\n{COMMIT}\n")),
    ("private_commit", "uppercase"): lambda f: mutation(add(f, "data/b.csv", f"commit_id\n{COMMIT.upper()}\n")),
    ("private_commit_prefix", "eight_in_markdown"): lambda f: mutation(add(f, "docs/b.md", f"See build {COMMIT[:8]}.\n")),
    ("private_commit_prefix", "seven_in_log_line"): lambda f: mutation(add(f, "docs/log.md", f"{COMMIT[:7]} Fix the table\n")),
    ("private_commit_prefix", "in_commit_link"): lambda f: mutation(
        add(f, "docs/link.md", f"https://example.org/owner/name/commit/{COMMIT[:7]}\n")),
    ("local_path", "in_markdown"): lambda f: mutation(add(f, "docs/c.md", "C:\\" + "Users" + "\\someone\\file\n")),
    ("local_path", "json_escaped"): lambda f: mutation(
        add(f, "data/notes.json", json.dumps({"path": "C:\\" + "Users" + "\\someone\\x"}) + "\n")),
    ("local_path", "forward_slashes"): lambda f: mutation(add(f, "docs/c.md", "C:/" + "Users" + "/someone/file\n")),
    ("local_path", "lower_case"): lambda f: mutation(add(f, "docs/c.md", "c:\\" + "users" + "\\someone\\file\n")),
    ("local_path", "unix_home"): lambda f: mutation(add(f, "docs/c.md", "path /" + "home/someone/file\n")),
    ("local_path", "mac_users"): lambda f: mutation(add(f, "docs/c.md", "path /" + "Users/someone/file\n")),
    ("local_root", "lower_case"): lambda f: mutation(add(f, "docs/r.md", ntpath.normcase(HOME + "\\file") + "\n")),
    ("local_root", "upper_case"): lambda f: mutation(add(f, "docs/r.md", (HOME + "\\file").upper() + "\n")),
    ("local_root", "forward_slashes"): lambda f: mutation(add(f, "docs/r.md", HOME.replace("\\", "/") + "/file\n")),
    ("local_root", "canonical_json"): lambda f: mutation(add(f, "data/r.json", canonical_json({"path": HOME + "\\file"}))),
    ("local_root", "unix_shell_form"): lambda f: mutation(
        add(f, "docs/r.md", "/c/" + "Users" + "/example.person/file\n")),
    ("local_root", "short_name"): lambda f: mutation(add(f, "docs/r.md", SHORT + "\\file\n")),
    ("local_root", "workspace_tail"): lambda f: mutation(add(f, "docs/r.md", "see " + TAIL + "\\notes.md\n")),
    ("local_root", "percent_encoded"): lambda f: mutation(add(f, "docs/r.md", "file:///" + percent(HOME) + "\n")),
    ("ip_address", "in_markdown"): lambda f: mutation(add(f, "docs/d.md", f"client {ip()}\n")),
    ("ip_address", "in_path"): lambda f: mutation(add(f, f"docs/{ip()}.md", "x\n")),
    ("user_agent", "in_markdown"): lambda f: mutation(add(f, "docs/e.md", "Mozi" + "lla/5.0 (X11)\n")),
    ("identifier_32", "lowercase"): lambda f: mutation(add(f, "analysis/x.py", f"K = '{HEX32_SAMPLE}'\n")),
    ("identifier_32", "uppercase"): lambda f: mutation(add(f, "analysis/x.py", f"K = '{HEX32_SAMPLE.upper()}'\n")),
    ("identifier_32", "in_path"): lambda f: mutation(add(f, f"data/{HEX32_SAMPLE}.csv", "x\n")),
    ("identifier_40", "workflow_comment"): lambda f: mutation(
        add(f, "config/workflow-templates/weekly.yml.example", WORKFLOW + f"      # previous pin {OTHER_40}\n")),
    ("identifier_40", "pin_value_repeated_bare"): lambda f: mutation(add(
        f, ".github/workflows/ci.yml",
        f"jobs:\n  t:\n    steps:\n      - uses: actions/checkout@{ACTION_SHA} # same as {ACTION_SHA}\n")),
    ("identifier_40", "unlisted_pin_in_workflow"): lambda f: mutation(
        add(f, ".github/workflows/ci.yml", WORKFLOW + f"      - uses: actions/setup-python@{OTHER_40}\n")),
    ("identifier_40", "unlisted_pin_in_run_block"): lambda f: mutation(add(
        f, ".github/workflows/ci.yml",
        WORKFLOW + f"      - name: echo\n        run: |\n          uses: actions/checkout@{OTHER_40}\n")),
    ("identifier_40", "tree_line_in_message"): lambda f: mutation(f, message=f"Note\n\ntree {OTHER_40}\n"),
    ("short_commit", "in_markdown"): lambda f: mutation(add(f, "docs/g.md", "fixed in commi" + "t 1a2b3c4d\n")),
    ("png_chunk_not_admitted", "text_chunk"): lambda f: mutation(
        add(f, "figures/f.png", png(before=((b"tEXt", b"Comment\x00hello"),)))),
    ("png_chunk_not_admitted", "palette_chunk"): lambda f: mutation(
        add(f, "figures/f.png", png(before=((b"PLTE", b"\x00\x00\x00"),)))),
    ("png_malformed", "trailing_data"): lambda f: mutation(add(f, "figures/f.png", png(trailing=b"extra bytes"))),
    ("png_malformed", "iend_payload"): lambda f: mutation(add(f, "figures/f.png", png(iend=b"hidden"))),
    ("png_malformed", "duplicate_ihdr"): lambda f: mutation(add(
        f, "figures/f.png", png(before=((b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)),)))),
    ("png_malformed", "idat_extra"): lambda f: mutation(add(f, "figures/f.png", png(idat_extra=b"hidden"))),
    ("png_malformed", "truncated"): lambda f: mutation(add(f, "figures/f.png", png(cut=6))),
    ("png_malformed", "bad_crc"): lambda f: mutation(add(f, "figures/f.png", png(bad_crc=True))),
    ("png_malformed", "extreme_dimensions"): lambda f: mutation(add(f, "figures/f.png", png(width=1 << 30))),
}


@unittest.skipUnless(HAS_GIT, "git is required for the publication gate tests")
class PublicationGateTests(unittest.TestCase):
    def repo(self, files: dict, action=None, message="Candidate edition") -> Path:
        directory = Path(tempfile.mkdtemp(prefix="dwr-gate-"))
        self.addCleanup(remove_tree, directory)

        def git(*args, data=None):
            return subprocess.run(["git", "-c", "core.autocrlf=false", "-c", "commit.gpgsign=false",
                                   "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
                                  cwd=directory, input=data, capture_output=True, check=True).stdout

        git("init", "-q")
        for name, data in files.items():
            target = directory / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        git("add", "-A")
        if action == "symlink":
            blob = git("hash-object", "-w", "--stdin", data=b"README.md").decode().strip()
            git("update-index", "--add", "--cacheinfo", f"120000,{blob},link")
        if action == "submodule":
            git("update-index", "--add", "--cacheinfo", f"160000,{'ab' * 20},vendor/sub")
        if isinstance(action, tuple) and action[0] == "empty_tree":
            empty = git("hash-object", "-t", "tree", "-w", "--stdin", data=b"").decode().strip()
            root = git("write-tree").decode().strip()
            listing = git("ls-tree", root) + f"040000 tree {empty}\t{action[1]}\n".encode()
            tree = git("mktree", data=listing).decode().strip()
            commit = git("commit-tree", tree, "-m", message).decode().strip()
            git("update-ref", "HEAD", commit)
            return directory
        git("commit", "-q", "-m", message)
        if action == "second_commit":
            (directory / "data" / "more.csv").write_bytes(b"x\n1\n")
            git("add", "-A")
            git("commit", "-q", "-m", "Second commit")
        if action in ("named_root", "other_root", "named_root_then_merge"):
            first = git("rev-parse", "HEAD").decode().strip()
            named = OTHER_40 if action == "other_root" else first
            config = json.dumps({"published_root": f"example/repo@{named}"})
            (directory / "config").mkdir(exist_ok=True)
            (directory / "config" / "publication-gate.json").write_text(config, encoding="utf-8")
            git("add", "-A")
            git("commit", "-q", "-m", "Next edition")
        if action == "named_root_then_merge":
            branch = git("rev-parse", "--abbrev-ref", "HEAD").decode().strip()
            git("checkout", "-q", "-b", "side", first)
            (directory / "side.md").write_bytes(b"side\n")
            git("add", "side.md")
            git("commit", "-q", "-m", "Side branch")
            git("checkout", "-q", branch)
            git("merge", "-q", "--no-ff", "--no-edit", "side")
        if action == "leak_then_remove":
            (directory / "docs" / "c.md").unlink()
            git("add", "-A")
            git("commit", "-q", "-m", "Remove the file")
        return directory

    def report(self, case: dict, **kwargs) -> dict:
        return gate.check_ref(self.repo(case["files"], case["action"], case["message"]), "HEAD", SECRETS, pins=PINS,
                              **kwargs)

    def test_coverage_and_mutations_match_one_to_one(self):
        listed = {(category, variant) for category, _, _, variants in gate.COVERAGE for variant, _, _ in variants}
        self.assertEqual(set(MUTATIONS), listed)
        self.assertEqual(len(gate.CATEGORY_IDS), len(set(gate.CATEGORY_IDS)))
        # The coverage is rendered as a Markdown table: a vertical bar would split a cell.
        texts = [text for _, en, fr, variants in gate.COVERAGE for text in (en, fr, *[v for _, *pair in variants for v in pair])]
        self.assertFalse([text for text in texts if "|" in text])

    def test_clean_candidate_passes_with_pinned_actions(self):
        report = gate.check_ref(self.repo(base_files()), "HEAD", SECRETS, pins=PINS)
        self.assertTrue(report["passed"], report["findings"])
        self.assertEqual((report["commits"], report["files"]), (1, 6))

    def test_each_listed_counterexample_is_caught_by_its_category(self):
        for (category, variant), build in MUTATIONS.items():
            case = build(base_files())
            case["files"] = case["files"] if case["files"] is not None else base_files()
            with self.subTest(category=category, variant=variant):
                found = {f["category"] for f in self.report(case)["findings"]}
                self.assertIn(category, found)

    def test_reports_never_print_private_values(self):
        for key in (("private_identifier", "in_path"), ("private_term", "in_path"), ("private_term", "in_empty_tree_name"),
                    ("identifier_32", "in_path")):
            case = MUTATIONS[key](base_files())
            case["files"] = case["files"] if case["files"] is not None else base_files()
            with self.subTest(case=key):
                text = repr(self.report(case)).lower()
                for value in (IDENTIFIER, TERM, HEX32_SAMPLE):
                    self.assertNotIn(value.lower(), text)

    def test_a_leak_removed_later_is_still_caught_in_history(self):
        case = MUTATIONS[("local_path", "in_markdown")](base_files())
        found = {f["category"] for f in gate.check_ref(self.repo(case["files"], "leak_then_remove"), "HEAD", SECRETS,
                                                       pins=PINS)["findings"]}
        self.assertIn("local_path", found)

    def test_linear_history_from_the_named_root_passes(self):
        directory = self.repo(base_files(), "named_root")
        first = subprocess.run(["git", "rev-list", "--max-parents=0", "HEAD"], cwd=directory, capture_output=True,
                               check=True).stdout.decode().strip()
        report = gate.check_ref(directory, "HEAD", SECRETS, pins=PINS | {f"example/repo@{first}"})
        self.assertTrue(report["passed"], report["findings"])
        self.assertEqual(report["commits"], 2)

    def test_history_counterexamples_raise_only_the_history_category(self):
        for action in ("second_commit", "other_root", "named_root_then_merge"):
            directory = self.repo(base_files(), action)
            config = directory / "config" / "publication-gate.json"
            named = json.loads(config.read_text(encoding="utf-8"))["published_root"] if config.is_file() else None
            with self.subTest(action=action):
                report = gate.check_ref(directory, "HEAD", SECRETS, pins=PINS | ({named} if named else set()))
                self.assertEqual({f["category"] for f in report["findings"]}, {"history_not_from_published_root"})

    def test_an_unreadable_configuration_stops_the_gate(self):
        directory = self.repo(base_files())
        real = gate._git

        def failing(repo, *args, data=None):
            if any("publication-gate.json" in arg for arg in args):
                raise gate.DwrError("git_failed", "simulated read failure")
            return real(repo, *args, data=data)

        with mock.patch.object(gate, "_git", failing):
            with self.assertRaises(gate.DwrError):
                gate.check_ref(directory, "HEAD", SECRETS, pins=PINS)

    def test_a_configuration_that_is_not_a_file_stops_the_gate(self):
        files = add(base_files(), "config/publication-gate.json/inner.json", "{}")
        with self.assertRaises(gate.DwrError):
            gate.check_ref(self.repo(files), "HEAD", SECRETS, pins=PINS)

    def test_a_malformed_published_root_stops_the_gate(self):
        files = add(base_files(), "config/publication-gate.json", json.dumps({"published_root": "not-a-pin"}))
        with self.assertRaises(gate.DwrError):
            gate.check_ref(self.repo(files), "HEAD", SECRETS, pins=PINS)


class CleanupTests(unittest.TestCase):
    def test_remove_tree_deletes_read_only_files(self):
        directory = Path(tempfile.mkdtemp(prefix="dwr-gate-"))
        target = directory / "objects" / "blob"
        target.parent.mkdir()
        target.write_bytes(b"x")
        os.chmod(target, stat.S_IREAD)
        remove_tree(directory)
        self.assertFalse(directory.exists())

    def test_remove_tree_raises_other_failures(self):
        parent = Path(tempfile.mkdtemp(prefix="dwr-gate-"))
        self.addCleanup(remove_tree, parent)
        with self.assertRaises(FileNotFoundError):
            remove_tree(parent / "missing")

    def test_remove_tree_refuses_a_symbolic_link_and_leaves_its_target(self):
        target = Path(tempfile.mkdtemp(prefix="dwr-gate-"))
        self.addCleanup(remove_tree, target)
        (target / "kept").write_bytes(b"x")
        link = target.with_name(target.name + "-link")
        try:
            os.symlink(target, link, target_is_directory=True)
        except OSError:
            self.skipTest("symbolic links cannot be created here")
        self.addCleanup(link.unlink)
        mode = target.stat().st_mode
        with self.assertRaises(OSError):
            remove_tree(link)
        self.assertTrue((target / "kept").exists())
        self.assertEqual(target.stat().st_mode, mode)


class GateSourceTests(unittest.TestCase):
    def test_gate_verify_and_these_tests_do_not_flag_their_own_source(self):
        for rel in ("analysis/dwr/gate.py", "analysis/dwr/verify.py", "tests/test_publication_gate.py",
                    "tests/test_privacy_scan.py", "tests/test_security_privacy.py"):
            with self.subTest(file=rel):
                # Patterns only: these tests hold synthetic secret values on purpose; the real values are checked by
                # the gate run with the private workspace.
                self.assertEqual(gate.scan_bytes(rel, (REPO_ROOT / rel).read_bytes(), None), [])

    def test_verify_uses_the_gate_patterns(self):
        self.assertIs(verify.HEX32, gate.HEX32)
        self.assertIs(verify.LOCAL_PATH, gate.LOCAL_PATH)

    def test_every_pin_of_the_workflows_is_admitted(self):
        files = sorted((REPO_ROOT / ".github" / "workflows").glob("*.yml")) + sorted(
            (REPO_ROOT / "config" / "workflow-templates").glob("*.yml.example"))
        pins = {f"{m.group('pair')}@{m.group('sha')}" for path in files
                for m in gate.PIN.finditer(path.read_text(encoding="utf-8"))}
        self.assertTrue(pins)
        self.assertEqual(pins, set(gate.action_pins()))
        self.assertEqual(set(gate.admitted_pins()) - set(gate.action_pins()),
                         {load_json(gate.PIN_CONFIG)["published_root"]})

    def test_png_of_the_edition_have_the_admitted_structure(self):
        pngs = sorted((REPO_ROOT / "figures").rglob("*.png"))
        self.assertTrue(pngs)
        for path in pngs:
            with self.subTest(png=path.name):
                self.assertEqual(gate.png_findings(path.read_bytes()), [])


if __name__ == "__main__":
    unittest.main()

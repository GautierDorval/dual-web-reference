import importlib.util
import unittest
from pathlib import Path

from tests import __init__  # noqa: F401
from dwr import verify
from dwr.common import REPO_ROOT


def registry_builder():
    spec = importlib.util.spec_from_file_location("build_scope_registry", REPO_ROOT / "scripts" / "build_scope_registry.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PrivacyScanTests(unittest.TestCase):
    def test_local_path_markers_match_paths_but_not_their_own_source(self):
        # Inputs are assembled at run time so that this file does not itself carry a local path marker.
        users, box, app = "Users", "Drop" + "box", "App" + "Data"
        for text in (f"C:\\{users}\\someone\\x", f"/c/{users}/someone/x", f"a {box} folder", f"C:\\x\\{app}\\Local"):
            self.assertTrue(verify.LOCAL_PATH.search(text), text)
        self.assertIsNone(verify.LOCAL_PATH.search((REPO_ROOT / "analysis" / "dwr" / "verify.py").read_text(encoding="utf-8")))

    def test_private_values_are_read_from_the_private_workspace_only(self):
        self.assertIsNone(verify.private_secrets(None))
        self.assertIsNone(verify.private_secrets(Path("does-not-exist") / "lock" / "private-lock.json"))
        self.assertFalse(hasattr(verify, "PRIVATE_NAMES"))

    def test_scan_covers_code_tests_and_scripts(self):
        rel = {p.relative_to(REPO_ROOT).as_posix() for p in verify.tracked_files()}
        for expected in ("analysis/dwr/verify.py", "scripts/build_scope_registry.py", "tests/test_privacy_scan.py",
                         "config/scope-registry.csv", "figures/2026-09-15_2026-10-15-r1/png/G01.en.png"):
            self.assertIn(expected, rel)
        self.assertFalse(any(r.startswith(".git/") for r in rel))


class JustificationTests(unittest.TestCase):
    def test_public_formats_survive_and_source_layout_is_removed(self):
        builder = registry_builder()
        builder.PRIVATE_REPOSITORIES = ("example-private-repo",)
        text = builder.public_justification(
            "Mirror of candidate-public.json and ai-governance.json; built by src/lib/build.ts:12-20 in "
            "example-private-repo from docs/governance/policy.md. Not in docs/public; produced by the build.")
        self.assertIn("candidate-public.json", text)
        self.assertIn("ai-governance.json", text)
        self.assertNotIn("fileon", text)
        for leaked in ("src/lib", "docs/governance", "docs/public", "example-private-repo", "build.ts"):
            self.assertNotIn(leaked, text)
        self.assertIn("Not a static file of the site sources", text)


if __name__ == "__main__":
    unittest.main()

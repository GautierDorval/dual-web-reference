import csv
import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from tests import __init__  # noqa: F401
from dwr import importer
from dwr.common import DwrError, load_json_bytes, read_csv

FILE_HEADER = ",".join(importer.FILE_COLUMNS)


def zip_bytes(members: dict, *, symlink: str | None = None) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in members.items():
            archive.writestr(name, content)
        if symlink:
            info = zipfile.ZipInfo(symlink)
            info.external_attr = 0o120777 << 16
            archive.writestr(info, "target")
    return buffer.getvalue()


def sums(members: dict) -> str:
    return "".join(f"{hashlib.sha256(c.encode()).hexdigest()}  {n.split('/')[-1]}\n" for n, c in members.items())


class ZipTests(unittest.TestCase):
    def test_traversal_absolute_and_symlink_are_refused(self):
        for name in ("../evil.csv", "/abs.csv", "C:/drive.csv", "a/../../b.csv"):
            with self.assertRaises(DwrError, msg=name):
                importer.safe_zip_members(zip_bytes({name: "x"}))
        with self.assertRaises(DwrError):
            importer.safe_zip_members(zip_bytes({"ok.txt": "x"}, symlink="link"))

    def test_too_many_members_and_bad_zip(self):
        with self.assertRaises(DwrError):
            importer.safe_zip_members(zip_bytes({f"f{i}.txt": "x" for i in range(importer.MAX_ZIP_MEMBERS + 1)}))
        with self.assertRaises(DwrError):
            importer.safe_zip_members(b"not a zip")

    def test_inner_checksums_verified_and_unlisted_members_refused(self):
        members = {"pkg/a.csv": "a,b\n1,2\n"}
        with tempfile.TemporaryDirectory() as tmp:
            good = Path(tmp) / "good.zip"
            good.write_bytes(zip_bytes({**members, "pkg/SHA256SUMS.txt": sums(members)}))
            self.assertEqual(importer.verify_zip(good)["members"], ["a.csv"])
            bad = Path(tmp) / "bad.zip"
            bad.write_bytes(zip_bytes({"pkg/a.csv": "tampered\n", "pkg/SHA256SUMS.txt": sums(members)}))
            with self.assertRaises(DwrError):
                importer.verify_zip(bad)
            extra = Path(tmp) / "extra.zip"
            extra.write_bytes(zip_bytes({**members, "pkg/b.csv": "x", "pkg/SHA256SUMS.txt": sums(members)}))
            with self.assertRaises(DwrError):
                importer.verify_zip(extra)


class ManifestTests(unittest.TestCase):
    def test_fake_digest_or_size_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.txt").write_text("hello", encoding="utf-8")
            digest = hashlib.sha256(b"hello").hexdigest()
            manifest = {"hash_algorithm": "SHA-256", "files": [{"path": "a.txt", "bytes": 5, "sha256": digest}]}
            (root / "MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
            self.assertEqual(len(importer.verify_manifest(root)["files"]), 1)
            manifest["files"][0]["sha256"] = "0" * 64
            (root / "MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(DwrError):
                importer.verify_manifest(root)
            manifest["files"][0] = {"path": "../outside.txt", "bytes": 5, "sha256": digest}
            (root / "MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(DwrError):
                importer.verify_manifest(root)


class ParsingTests(unittest.TestCase):
    def test_truncated_and_duplicate_key_json_fail(self):
        with self.assertRaises(DwrError):
            load_json_bytes(b'{"a": [1, 2')
        with self.assertRaises(DwrError):
            load_json_bytes(b'{"a": 1, "a": 2}')
        deep = b"[" * 50 + b"]" * 50
        with self.assertRaises(DwrError):
            load_json_bytes(deep)

    def test_ragged_csv_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.csv"
            path.write_text("a,b\n1,2,3\n", encoding="utf-8")
            with self.assertRaises(DwrError):
                read_csv(path)
            path.write_text("", encoding="utf-8")
            with self.assertRaises(DwrError):
                read_csv(path)

    def _write_inputs(self, root: Path, files_rows, actor_rows, daily_rows):
        def write(name, header, rows):
            with (root / name).open("w", encoding="utf-8", newline="") as stream:
                stream.write(header + "\n")
                for row in rows:
                    stream.write(",".join(str(v) for v in row) + "\n")
        write("fichiers-390-chemins.csv", FILE_HEADER, files_rows)
        write("acteurs-46-groupes.csv", ",".join(importer.ACTOR_COLUMNS), actor_rows)
        write("journalier-90-lignes.csv", ",".join(importer.DAILY_COLUMNS), daily_rows)
        report = {"http": [], "identity_tiers": [], "archive_comparison": [], "registered_now_without_window_rows": [],
                  "source": {k: "x" for k in ("d1_database", "table", "access", "archive_repo", "archive_branch",
                                               "archive_commit", "archive_commit_at")} | {"observed_at": ["2026-10-02T00:00:00Z"]},
                  "sql_queries": {}}
        (root / "releve-mensuel-complet.json").write_text(json.dumps(report), encoding="utf-8")

    def _daily(self):
        return [[f"2026-10-0{d}", site, 1, 1, 1, 0] for d in (1, 2) for site in ("gautierdorval.com", "pagup.com", "better-robots.com")]

    def test_negative_unknown_duplicate_and_out_of_window_rows_fail(self):
        good_file = ["pagup.com", "/llms.txt", "x", 2, 1, 0, 0, 1, 2, 1, 0, "2026-10-01", "2026-10-02", "s", "u"]
        good_actor = ["pagup.com", "GPTBot", "ai_training", "provider_origin_verified_actor", 1, 1, 1, 1]
        cases = {
            "count_negative": ([good_file[:3] + [-1] + good_file[4:]], [good_actor]),
            "actor_role_unknown": ([good_file], [good_actor[:2] + ["invented_role"] + good_actor[3:]]),
            "identity_tier_unknown": ([good_file], [good_actor[:3] + ["verified"] + good_actor[4:]]),
            "duplicate_site_path": ([good_file, good_file], [good_actor]),
            "date_outside_window": ([good_file[:11] + ["2026-09-30"] + good_file[12:]], [good_actor]),
            "site_not_allowed": ([["example.com"] + good_file[1:]], [good_actor]),
        }
        for code, (files_rows, actor_rows) in cases.items():
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self._write_inputs(root, files_rows, actor_rows, self._daily())
                with self.assertRaises(DwrError, msg=code) as context:
                    importer.load_marginals(root, "2026-10-01", "2026-10-03")
                self.assertEqual(context.exception.code, code)

    def test_incomplete_daily_rows_fail_and_valid_inputs_load(self):
        good_file = ["pagup.com", "/llms.txt", "x", 2, 1, 0, 0, 1, 2, 1, 0, "2026-10-01", "2026-10-02", "s", "u"]
        good_actor = ["pagup.com", "GPTBot", "ai_training", "provider_origin_verified_actor", 1, 1, 1, 1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_inputs(root, [good_file], [good_actor], self._daily()[:-1])
            with self.assertRaises(DwrError):
                importer.load_marginals(root, "2026-10-01", "2026-10-03")
            self._write_inputs(root, [good_file], [good_actor], self._daily())
            loaded = importer.load_marginals(root, "2026-10-01", "2026-10-03")
            self.assertEqual(loaded["files"][0]["path"], "/llms.txt")
            self.assertEqual(loaded["mode"], "export_marginals")


if __name__ == "__main__":
    unittest.main()

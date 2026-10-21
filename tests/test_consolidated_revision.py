"""Regressions for the independent consolidated review, using disposable roots."""
from contextlib import ExitStack, contextmanager, redirect_stderr, redirect_stdout
from copy import deepcopy
from io import StringIO
from pathlib import Path
import tempfile
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

from tests import __init__
from tests.test_audit_followup import copy_candidate
from tests.test_next_edition import prepare_inputs
from dwr import cli, common, dates, edition_rules, frozen, maintenance, measurement, pipeline, png, project, qualify, render, revisions, semantics, verify, write_guard
from dwr.common import load_json, write_json, write_text
SOURCE_ROOT = common.REPO_ROOT

R2 = "2026-09-15_2026-10-15-r2"
LOCAL = "2026-09-15_2026-10-15-r3"


@contextmanager
def isolated_repository():
    with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
        base = Path(tmp)
        root = base / "repo"
        root.mkdir()
        copy_candidate(root)
        for name in ("analysis", "scripts"):
            shutil.copytree(SOURCE_ROOT / name, root / name, ignore=shutil.ignore_patterns("__pycache__"))
        for module in (cli, common, frozen, maintenance, pipeline, png, qualify, render, revisions, verify):
            stack.enter_context(patch.object(module, "REPO_ROOT", root))
        yield root, base / "private"


def register_local(root, edition_id=LOCAL, start="2026-09-15", end="2026-10-15", revision=3):
    config = load_json(root / "config/editions.json")
    entry = deepcopy(config["editions"][1])
    entry.update(edition_id=edition_id, revision=revision, availability_status="local_candidate",
                 period_start_inclusive=start, period_end_exclusive=end)
    if edition_id != LOCAL:
        entry.update(supersedes=None, revised_at=None, generated_at="2026-11-17",
                     observation_provenance="synthetic_only_not_observed_traffic")
    entry.pop("public_availability_evidence", None)
    config["editions"].append(entry)
    write_json(root / "config/editions.json", config)


def add_stale_outputs(root, edition_id):
    payload, figures = root / "data/editions" / edition_id, root / "figures" / edition_id
    write_text(payload / "obsolete-table.csv", "synthetic_withheld_detail\nobsolete\n")
    write_text(figures / "obsolete.svg", "<svg><!-- obsolete fixture --></svg>")
    write_text(figures / "png/G01.en.png", "obsolete synthetic PNG")
    return payload, figures


def complete_projection_inputs(root, private):
    edition_id = prepare_inputs(private)
    register_local(root, edition_id, "2026-10-15", "2026-11-15", 1)
    work = private / "working" / edition_id
    normalized = load_json(work / "normalized.json")
    normalized["joint_cross_check"] = {"all_consistent": True, "checks": []}
    normalized["marginals"].update(extracted_at=["2026-11-17T00:00:00Z"],
                                  source={"archive_commit_at": "2026-11-17T00:00:00Z"})
    write_json(work / "normalized.json", normalized)
    qualified = load_json(work / "qualified.json")
    qualified["case_checks"] = []
    write_json(work / "qualified.json", qualified)
    write_json(work / "reconciliation.json", {
        "nature": "synthetic_only_not_observed_traffic", "comparison": {"all_match": True},
        "by_site_provider_origin_ai_get200": {}, "daily_all_match_archive_aggregate": True})
    write_json(private / "import/imp-synthetic/receipt.json", {"import_id": "imp-synthetic"})
    return edition_id


class ConsolidatedRevisionTests(unittest.TestCase):
    def test_comparison_adapts_recorded_scalar_to_equal_list_without_guessing_prefixes(self):
        base = {key:"synthetic" for key in edition_rules.COMPARABILITY_KEYS}
        base.update(coverage_status="complete_declared", period_start_inclusive="2026-09-15",
                    period_end_exclusive="2026-10-15", versions={"classifier_recorded":"classifier-v1"})
        other = deepcopy(base)
        other["versions"]["classifier_recorded"] = ["classifier-v1"]
        self.assertEqual(edition_rules.comparable(base, other), (True, []))
        other["versions"]["classifier_recorded"] = ["v1"]
        self.assertIn("changed:classifier_recorded", edition_rules.comparable(base, other)[1])

    def test_registry_change_and_published_date_refuse_installation(self):
        from tests.test_consolidated import registry
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = registry(root)
            config["editions"][-1]["published_at"] = "2026-10-20"
            write_json(root / "config/editions.json", config)
            with self.assertRaisesRegex(common.DwrError, "edition_target_not_local_unapproved"):
                write_guard.admit(root, LOCAL)
            config["editions"][-1]["published_at"] = None
            write_json(root / "config/editions.json", config)
            with self.assertRaisesRegex(common.DwrError, "edition_destination_changed"):
                with write_guard.transaction(root, LOCAL) as stage:
                    write_text(stage / "payload/value", "candidate")
                    config["editions"][-1]["review_status"]["technical"] = "pending_changed_during_build"
                    write_json(root / "config/editions.json", config)
            self.assertFalse((root / "data/editions" / LOCAL).exists())
            # A target that becomes approved must report immutable admission,
            # before the generic registry-content drift diagnostic.
            with self.assertRaisesRegex(common.DwrError, "public_or_historical_edition_immutable"):
                with write_guard.transaction(root, LOCAL) as stage:
                    write_text(stage / "payload/value", "candidate")
                    config["editions"][-1]["reference_release_status"] = "approved"
                    write_json(root / "config/editions.json", config)
            self.assertFalse((root / "data/editions" / LOCAL).exists())

    def test_public_comparison_detects_changed_svg_and_metrics(self):
        with isolated_repository() as (root, private):
            svg = root / "figures" / R2 / "G01.en.svg"
            write_text(svg, svg.read_text(encoding="utf-8") + "<!-- altered -->\n")
            with self.assertRaisesRegex(common.DwrError, "public_figure_reproduction_differs"):
                render.compare_figures(render.Edition(R2))
            metrics = root / "data/editions" / R2 / "metrics.json"
            write_text(metrics, metrics.read_text(encoding="utf-8") + "\n")
            with self.assertRaisesRegex(common.DwrError, "public_metrics_reproduction_differs"):
                pipeline.cmd_analyze(R2)

    def test_preview_cannot_use_canonical_payload_or_destination(self):
        with isolated_repository() as (root, private), patch.object(png, "_render") as browser:
            with self.assertRaisesRegex(common.DwrError, "png_preview_must_be_outside_repository"):
                png.prepare(R2, root / "preview")
            browser.assert_not_called()
            edition = render.Edition(R2)
            with tempfile.TemporaryDirectory() as tmp:
                preview = Path(tmp)
                with self.assertRaisesRegex(common.DwrError, "figure_preview_requires_separate_payload_and_destination"):
                    render.render_figures(edition, preview / "figures")
                shutil.copytree(edition.dir, preview / "payload")
                detached = render.Edition(R2, preview / "payload", edition.entry)
                with self.assertRaisesRegex(common.DwrError, "figure_preview_requires_separate_payload_and_destination"):
                    render.render_figures(detached, root / "figures/unregistered-preview")
            self.assertFalse((root / "preview").exists())

    def test_consultation_sort_includes_epoch_when_every_other_key_is_equal(self):
        with tempfile.TemporaryDirectory() as tmp:
            private = Path(tmp)
            eid = prepare_inputs(private)
            work = private / "working" / eid
            norm, qual = load_json(work / "normalized.json"), load_json(work / "qualified.json")
            row = norm["joint_rows"][0]
            day = row["date_utc"]
            norm["joint_rows"] = [{**row, "measurement_epoch_id":"epoch-z", "classifier_version":"v2"},
                                  {**row, "measurement_epoch_id":"epoch-a", "classifier_version":"v1"}]
            norm["measurement_provenance"]["days"][day] = {"epochs":[
                {"epoch_id":e, "classifier_version":v, "attribution_rules":"synthetic", "deployment_evidence":"synthetic"}
                for e,v in (("epoch-z","v2"), ("epoch-a","v1"))]}
            entry = {"edition_id":eid, "window":dates.window_from_strings("2026-10-15","2026-11-15")}
            first = project.project(qual, norm, entry, "synthetic")["consultations"]
            norm["joint_rows"].reverse()
            second = project.project(qual, norm, entry, "synthetic")["consultations"]
            self.assertEqual(first, second)
            self.assertEqual([row["measurement_epoch_id"] for row in first], ["epoch-a","epoch-z"])

    def test_unknown_and_mixed_states_are_not_recorded_classifier_versions(self):
        day = "2026-10-20"
        archive = [{"date_utc":day, "archive_status":"archived", "report_status":"complete"}]
        for provenance, state in (({}, "unknown"), ({"days": {day: {"separable":False, "epochs":[
                {"classifier_version":"v1"}, {"classifier_version":"v2"}]}}}, "mixed_epoch_unresolved")):
            report = measurement.qualify([{"date_utc":day}], archive, provenance)
            self.assertEqual(report["classifier_versions"], [])
            self.assertEqual(report["days"][day]["classifier_versions"], [])
            self.assertEqual(report["epoch_resolution"], state)
            self.assertEqual(report["rows"][0]["measurement_epoch_id"], state)

    def test_daily_contract_uses_actual_revision_and_never_infers_a_removed_row_count_between_windows(self):
        edition = render.Edition(R2)
        text = semantics.daily_contract(edition, "en")
        for value in ("285", "549", "834", R2, "2026-09-15_2026-10-15-r1"):
            self.assertIn(value, text)
        edition.catalog = {**edition.catalog, "revision_kind":"new_observations", "supersedes":"unavailable-source"}
        text = semantics.daily_contract(edition, "en")
        self.assertIn("contains", text)
        self.assertNotIn("removed rows", text)

    def test_v2_schema_rejects_invalid_epoch_state_and_malformed_version_array(self):
        with isolated_repository() as (root, private):
            edition_id = complete_projection_inputs(root, private)
            render.render_schemas()
            pipeline.cmd_project_public(private, edition_id)
            from dwr.common import read_csv, csv_text
            from dwr.project import COVERAGE_FIELDS
            payload = root / "data/editions" / edition_id
            path = payload / "coverage.csv"
            original = read_csv(path)
            for field, value in (("epoch_resolution", "implied"), ("classifier_versions", '["unknown"]'),
                                 ("classifier_versions", '["v2","v1"]'), ("measurement_epochs", '{"a":1}')):
                rows = deepcopy(original)
                rows[0][field] = value
                write_text(path, csv_text(COVERAGE_FIELDS, rows))
                report = verify.Report()
                verify.check_tables(report, payload)
                self.assertFalse(report.result()["passed"], (field, value))

    def run_cli(self, root, *args):
        return subprocess.run([sys.executable, "-X", "utf8", "-I", "-B", str(root / "scripts/dwr.py"), *args],
                              cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=60)

    def test_real_cli_refuses_public_before_invalid_private_root(self):
        with isolated_repository() as (root, private):
            before = [write_guard.fingerprint(root / name / R2) for name in ("data/editions", "figures")]
            result = self.run_cli(root, "project-public", "--edition", R2, "--private-root", str(private))
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("FAIL public_or_historical_edition_immutable:", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertFalse(private.exists())
            self.assertEqual(before, [write_guard.fingerprint(root / name / R2) for name in ("data/editions", "figures")])

    def test_cli_dispatch_refuses_public_before_private_resolution(self):
        with isolated_repository() as (root, private):
            before = [write_guard.fingerprint(root / name / R2) for name in ("data/editions", "figures")]
            with patch.object(cli, "private_root", side_effect=AssertionError("private resolution reached")), \
                    patch.object(png, "_render", side_effect=AssertionError("browser reached")):
                for command in ("project-public", "prepare-edition", "revise-public", "png-fallback"):
                    error = StringIO()
                    args = [command, "--edition", R2]
                    if command == "project-public":
                        args += ["--private-root", str(private)]
                    with self.subTest(command=command), redirect_stderr(error), redirect_stdout(StringIO()):
                        self.assertEqual(cli.main(args), 2)
                    expected = ("revision_target_not_local_unapproved" if command == "revise-public"
                                else "public_or_historical_edition_immutable")
                    self.assertIn("FAIL " + expected + ":", error.getvalue())
            self.assertEqual(before, [write_guard.fingerprint(root / name / R2) for name in ("data/editions", "figures")])

    def test_revision_rebuild_drops_obsolete_payload_figures_and_png(self):
        with isolated_repository() as (root, private):
            register_local(root)
            revisions.prepare(LOCAL)
            payload, figures = add_stale_outputs(root, LOCAL)
            revisions.prepare(LOCAL)
            self.assertFalse((payload / "obsolete-table.csv").exists())
            self.assertFalse((figures / "obsolete.svg").exists())
            self.assertFalse((figures / "png").exists())
            self.assertEqual(len(list(figures.glob("*.svg"))), 48)
            self.assertNotIn("obsolete", (payload / "SHA256SUMS.txt").read_text(encoding="utf-8"))

    def test_cli_project_rebuild_is_complete_and_failed_rebuild_preserves_original(self):
        with isolated_repository() as (root, private):
            edition_id = complete_projection_inputs(root, private)
            args = ["project-public", "--edition", edition_id, "--private-root", str(private)]
            result = self.run_cli(root, *args)
            self.assertEqual(result.returncode, 0, result.stderr)
            payload, figures = add_stale_outputs(root, edition_id)
            before = [write_guard.fingerprint(p) for p in (payload, figures)]
            with patch.object(pipeline, "build_catalog", side_effect=RuntimeError("synthetic late failure")), \
                    self.assertRaises(RuntimeError):
                cli.main(args)
            self.assertEqual(before, [write_guard.fingerprint(p) for p in (payload, figures)])
            result = self.run_cli(root, *args)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((payload / "obsolete-table.csv").exists())
            self.assertFalse((figures / "obsolete.svg").exists())
            self.assertFalse((figures / "png").exists())
            self.assertEqual(len(list(figures.glob("*.svg"))), 48)
            self.assertEqual(load_json(payload / "catalog.json")["edition_id"], edition_id)

    def test_manifest_refuses_missing_or_obsolete_files_without_installation(self):
        with isolated_repository() as (root, private):
            register_local(root)
            with self.assertRaisesRegex(common.DwrError, "distribution_file_set_mismatch"):
                pipeline.cmd_prepare_edition(LOCAL)
            revisions.prepare(LOCAL)
            payload, figures = root / "data/editions" / LOCAL, root / "figures" / LOCAL
            for target in (payload / "obsolete.csv", figures / "obsolete.svg", figures / "png/obsolete.png"):
                write_text(target, "synthetic obsolete output")
                before = [write_guard.fingerprint(p) for p in (payload, figures)]
                with self.assertRaises(common.DwrError):
                    pipeline.cmd_prepare_edition(LOCAL)
                self.assertEqual(before, [write_guard.fingerprint(p) for p in (payload, figures)])
                target.unlink()

    def test_local_render_without_review_and_missing_private_metadata_are_controlled(self):
        with isolated_repository() as (root, private):
            edition_id = complete_projection_inputs(root, private)
            path = private / "working" / edition_id / "normalized.json"
            normalized = load_json(path)
            del normalized["marginals"]["extracted_at"]
            write_json(path, normalized)
            with self.assertRaisesRegex(common.DwrError, "projection_catalog_provenance_incomplete"):
                pipeline.cmd_project_public(private, edition_id)
            self.assertFalse((root / "data/editions" / edition_id).exists())
            register_local(root)
            revisions.prepare(LOCAL)
            render.cmd(LOCAL)
            status = load_json(root / "data/status.json")
            self.assertEqual(status["candidate_state"], "not_reviewed")
            self.assertIsNone(status["last_review"])

    def test_figure_rebuild_invalidates_previous_png_for_render_and_analyze(self):
        with isolated_repository() as (root, private):
            register_local(root)
            revisions.prepare(LOCAL)
            figures = root / "figures" / LOCAL
            for command in (lambda: render.render_figures(render.Edition(LOCAL)),
                            lambda: pipeline.cmd_analyze(LOCAL)):
                write_text(figures / "png/G01.en.png", "stale synthetic image")
                write_text(figures / "obsolete.svg", "<svg/>")
                command()
                self.assertFalse((figures / "png").exists())
                self.assertFalse((figures / "obsolete.svg").exists())
                self.assertEqual(len(list(figures.glob("*.svg"))), 48)

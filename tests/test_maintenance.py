import unittest

from tests import __init__  # noqa: F401
from dwr import edition_rules as rules
from dwr.common import DwrError


class EditionRuleTests(unittest.TestCase):
    def test_correction_creates_next_revision_with_reason_and_delta(self):
        r1 = {"edition_id": "2026-09-15_2026-10-15-r1"}
        r2 = rules.correction(r1, "classifier_correction", {"main.get200": {"r1": 10, "r2": 9}}, "author", "reviewer")
        self.assertEqual(r2["edition_id"], "2026-09-15_2026-10-15-r2")
        self.assertEqual(r2["supersedes"], r1["edition_id"])
        self.assertFalse(r2["is_growth"])
        self.assertIsNone(r2["published_at"])
        for bad in (("growth", {"x": 1}), ("scope_change", {})):
            with self.assertRaises(DwrError):
                rules.correction(r1, bad[0], bad[1], "a", "b")
        with self.assertRaises(DwrError):
            rules.correction(r1, "scope_change", {"x": 1}, "a", "")

    def test_latest_points_only_to_reviewed_publications(self):
        editions = [
            {"edition_id": "2026-09-15_2026-10-15-r1", "status": "published", "published_at": "2026-10-20", "reviewed": True,
             "period_end_exclusive": "2026-10-15", "superseded_by": "2026-09-15_2026-10-15-r2"},
            {"edition_id": "2026-09-15_2026-10-15-r2", "status": "published", "published_at": "2026-10-25", "reviewed": True,
             "period_end_exclusive": "2026-10-15"},
            {"edition_id": "2026-10-15_2026-11-15-r1", "status": "candidate_not_reviewed", "published_at": None,
             "period_end_exclusive": "2026-11-15"},
        ]
        # Legacy published/reviewed booleans are insufficient without a content-bound receipt.
        self.assertIsNone(rules.latest_pointer(editions))
        self.assertIsNone(rules.latest_pointer([editions[2]]))
        unreviewed = dict(editions[1], reviewed=False)
        self.assertIsNone(rules.latest_pointer([unreviewed]))

    def test_unchanged_or_failed_runs_do_not_advance_freshness(self):
        status = {"latest_available_data_date": "2026-10-14", "latest_published_edition": "e1"}
        for outcome in ("unchanged", "source_unavailable", "validation_failed"):
            updated = rules.apply_run(status, outcome)
            self.assertEqual(updated["latest_available_data_date"], "2026-10-14")
            self.assertEqual(updated["latest_published_edition"], "e1")
        self.assertEqual(rules.apply_run(status, "source_unavailable")["source_state"], "source_unavailable")
        with self.assertRaises(DwrError):
            rules.apply_run(status, "new_data", new_data_date="2026-10-14")
        self.assertEqual(rules.apply_run(status, "new_data", new_data_date="2026-11-14")["latest_available_data_date"], "2026-11-14")
        with self.assertRaises(DwrError):
            rules.apply_run(status, "published_automatically")

    def test_failed_source_keeps_previous_values_never_zeros(self):
        previous = [{"date_utc": "2026-10-01", "request_count": 5}]
        kept = rules.series_for_failed_source(previous)
        self.assertEqual(kept[0]["request_count"], 5)
        self.assertEqual(kept[0]["source_state"], "source_unavailable")

    def test_rolling_and_overlapping_windows_are_never_added(self):
        rolling = [{"type": "rolling_30d", "start": "2026-09-15", "end_exclusive": "2026-10-15", "count": 3},
                   {"type": "rolling_30d", "start": "2026-09-22", "end_exclusive": "2026-10-22", "count": 4}]
        with self.assertRaises(DwrError):
            rules.add_windows(rolling)
        overlapping = [{"type": "monthly", "start": "2026-09-15", "end_exclusive": "2026-10-15", "count": 1},
                       {"type": "monthly", "start": "2026-10-01", "end_exclusive": "2026-11-01", "count": 1}]
        with self.assertRaises(DwrError):
            rules.add_windows(overlapping)
        consecutive = [{"type": "monthly", "start": "2026-09-15", "end_exclusive": "2026-10-15", "count": 1},
                       {"type": "monthly", "start": "2026-10-15", "end_exclusive": "2026-11-15", "count": 2}]
        self.assertEqual(rules.add_windows(consecutive), 3)

    def test_incompatible_editions_are_not_compared_and_growth_from_zero_is_not_calculable(self):
        a = {"versions": {"scope_rules": "scope-rules/1.0.0", "classifier_recorded": "2026-08-24.1"}, "source_mode": "export_marginals"}
        b = {"versions": {"scope_rules": "scope-rules/1.0.0", "classifier_recorded": "2026-10-16.1"}, "source_mode": "export_marginals"}
        ok, reasons = rules.comparable(a, b)
        self.assertFalse(ok)
        self.assertTrue(any("classifier_recorded" in reason for reason in reasons))
        self.assertFalse(rules.comparable(a, dict(a))[0])
        self.assertEqual(rules.growth(0, 5, True)["status"], "not_calculable")
        self.assertEqual(rules.growth(None, 5, True)["status"], "not_calculable")
        self.assertEqual(rules.growth(4, 5, False)["status"], "not_calculable")
        self.assertAlmostEqual(rules.growth(4, 5, True)["value"], 0.25)

    def test_changed_candidate_invalidates_the_review_receipt(self):
        self.assertTrue(rules.receipt_valid("a" * 64, "a" * 64))
        self.assertFalse(rules.receipt_valid("a" * 64, "b" * 64))
        self.assertFalse(rules.receipt_valid("", ""))

    def test_edition_identifier_format(self):
        self.assertEqual(rules.parse_edition_id("2026-10-15_2026-11-15-r3"), ("2026-10-15", "2026-11-15", 3))
        with self.assertRaises(DwrError):
            rules.parse_edition_id("2026-10")


if __name__ == "__main__":
    unittest.main()

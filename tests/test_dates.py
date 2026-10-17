import unittest
from datetime import date, datetime, timedelta, timezone

from tests import __init__  # noqa: F401
from dwr.common import DwrError
from dwr.dates import (Window, consolidation_ready, last_closed_day, latest_closed_monthly_window, monthly_window,
                       next_monthly_window, parse_date, rolling_window, window_from_strings)


class WindowTests(unittest.TestCase):
    def test_first_window_bounds_and_label(self):
        window = window_from_strings("2026-09-15", "2026-10-15")
        self.assertEqual(window.days, 30)
        self.assertEqual(window.last_included, date(2026, 10, 14))
        self.assertFalse(window.contains(date(2026, 10, 15)))
        self.assertTrue(window.contains(date(2026, 9, 15)))
        self.assertEqual(window.label_fr(), "du 15 septembre au 14 octobre 2026 inclusivement, en UTC")
        self.assertEqual(window.label_en(), "September 15 to October 14, 2026 inclusive, UTC")
        self.assertEqual(window.edition_id(1), "2026-09-15_2026-10-15-r1")
        self.assertEqual(window.end_exclusive_utc, "2026-10-15T00:00:00Z")

    def test_next_window_is_31_days(self):
        nxt = next_monthly_window(monthly_window(date(2026, 9, 15)))
        self.assertEqual((nxt.start, nxt.end_exclusive, nxt.days), (date(2026, 10, 15), date(2026, 11, 15), 31))
        self.assertEqual(nxt.label_fr(), "du 15 octobre au 14 novembre 2026 inclusivement, en UTC")

    def test_month_lengths_28_29_30_31(self):
        self.assertEqual(monthly_window(date(2027, 2, 15)).days, 28)
        self.assertEqual(monthly_window(date(2028, 2, 15)).days, 29)
        self.assertEqual(monthly_window(date(2027, 4, 15)).days, 30)
        self.assertEqual(monthly_window(date(2027, 1, 15)).days, 31)
        year_end = monthly_window(date(2026, 12, 15))
        self.assertEqual(year_end.end_exclusive, date(2027, 1, 15))
        self.assertEqual(year_end.label_fr(), "du 15 décembre 2026 au 14 janvier 2027 inclusivement, en UTC")

    def test_invalid_inputs_fail(self):
        for value in ("2026-9-15", "2026-02-30", "", None, "2026-10-15T00:00:00Z"):
            with self.assertRaises(DwrError):
                parse_date(value)
        with self.assertRaises(DwrError):
            Window(date(2026, 10, 15), date(2026, 10, 15))
        with self.assertRaises(DwrError):
            monthly_window(date(2026, 9, 14))
        with self.assertRaises(DwrError):
            window_from_strings("2026-09-15", "2026-10-15").edition_id(0)

    def test_current_utc_day_never_included_and_dst_has_no_effect(self):
        self.assertEqual(last_closed_day(datetime(2026, 10, 16, 0, 0, tzinfo=timezone.utc)), date(2026, 10, 15))
        # 23:30 on Nov 1 in UTC-4 and 23:30 in UTC-5 (after a local DST change) are both Nov 2 in UTC.
        before = datetime(2026, 11, 1, 23, 30, tzinfo=timezone(timedelta(hours=-4)))
        after = datetime(2026, 11, 1, 23, 30, tzinfo=timezone(timedelta(hours=-5)))
        self.assertEqual(last_closed_day(before), date(2026, 11, 1))
        self.assertEqual(last_closed_day(after), date(2026, 11, 1))
        with self.assertRaises(DwrError):
            last_closed_day(datetime(2026, 10, 16))

    def test_consolidation_delay_and_latest_closed_window(self):
        window = monthly_window(date(2026, 9, 15))
        self.assertFalse(consolidation_ready(window, datetime(2026, 10, 16, 23, 59, tzinfo=timezone.utc), 48))
        self.assertTrue(consolidation_ready(window, datetime(2026, 10, 17, 0, 0, tzinfo=timezone.utc), 48))
        self.assertEqual(latest_closed_monthly_window(window, datetime(2026, 11, 14, tzinfo=timezone.utc)), window)
        self.assertEqual(latest_closed_monthly_window(window, datetime(2026, 11, 16, tzinfo=timezone.utc)).start, date(2026, 10, 15))
        self.assertIsNone(latest_closed_monthly_window(window, datetime(2026, 10, 14, tzinfo=timezone.utc)))

    def test_rolling_window_bounds(self):
        rolling = rolling_window(date(2026, 10, 14))
        self.assertEqual((rolling.start, rolling.end_exclusive, rolling.days), (date(2026, 9, 15), date(2026, 10, 15), 30))


if __name__ == "__main__":
    unittest.main()

import re
import unittest
from datetime import datetime, timezone

from tests import __init__  # noqa: F401
from dwr import acquire, mdlite, render, typo, verify
from dwr.common import DwrError, REPO_ROOT, load_json, safe_relative, spreadsheet_safe, validate_path
from dwr.dates import window_from_strings


class InjectionTests(unittest.TestCase):
    def test_markdown_renderer_escapes_html_and_drops_unsafe_links(self):
        html = mdlite.render("<script>alert(1)</script> [x](javascript:alert(1)) **b** `<i>`")
        self.assertNotIn("<script", html)
        self.assertNotIn("javascript:", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("<strong>b</strong>", html)
        self.assertIn("<code>&lt;i&gt;</code>", html)

    def test_untrusted_excerpts_are_neutralized_in_tables(self):
        escaped = render.md_escape("a | b <img src=x onerror=alert(1)> `c` [d](e)")
        rendered = mdlite.render(f"| h |\n|---|\n| {escaped} |")
        self.assertNotIn("<img", rendered)
        self.assertIn("&lt;img", rendered)
        self.assertEqual(rendered.count("<td"), 1)

    def test_spreadsheet_variant_neutralizes_formulas_only(self):
        for value in ("=HYPERLINK(1)", "+1", "-1", "@SUM(1)", "\tx"):
            self.assertTrue(spreadsheet_safe(value).startswith("'"))
        self.assertEqual(spreadsheet_safe("/llms.txt"), "/llms.txt")

    def test_dangerous_paths_are_refused(self):
        for value in ("../etc/passwd", "relative", "/a/../../b", "/a\\b", "/" + "x" * 600, "/a b"):
            with self.assertRaises(DwrError, msg=value):
                validate_path(value)
        for value in ("../x", "/abs", "C:/x", "a/../../b"):
            with self.assertRaises(DwrError, msg=value):
                safe_relative(REPO_ROOT, value)


class AcquisitionTests(unittest.TestCase):
    def test_queries_are_single_selects_with_validated_values(self):
        window = window_from_strings("2026-09-15", "2026-10-15")
        queries = acquire.planned_queries(window)
        self.assertEqual(len([q for q in queries if q["query_id"].startswith("q02_")]), 30)
        for query in queries:
            self.assertTrue(query["sql"].startswith("SELECT "))
            self.assertNotIn(";", query["sql"])
            self.assertNotRegex(query["sql"], r"(?i)\b(insert|update|delete|drop|alter|attach|pragma)\b")
        with self.assertRaises(DwrError):
            acquire.planned_queries(window, domains=("example.com",))
        with self.assertRaises(DwrError):
            acquire._quote("x' OR '1'='1")

    def test_dry_run_by_default_and_closed_windows_only(self):
        window = window_from_strings("2026-09-15", "2026-10-15")
        result = acquire.acquire(REPO_ROOT, window, execute=False, confirm_scope=None,
                                 now=datetime(2026, 10, 16, tzinfo=timezone.utc))
        self.assertEqual(result["mode"], "dry_run")
        with self.assertRaises(DwrError):
            acquire.acquire(REPO_ROOT, window, execute=False, confirm_scope=None,
                            now=datetime(2026, 10, 14, tzinfo=timezone.utc))
        with self.assertRaises(DwrError) as context:
            acquire.acquire(REPO_ROOT, window, execute=True, confirm_scope="wrong",
                            now=datetime(2026, 10, 16, tzinfo=timezone.utc))
        self.assertEqual(context.exception.code, "scope_confirmation_mismatch")


class PrivacyTests(unittest.TestCase):
    def test_privacy_scan_detects_forbidden_material(self):
        # Samples are synthetic and assembled at run time: a literal here would itself be scanned, and a test sample
        # must never be a real identifier.
        ip, agent, identifier = ".".join(("203", "0", "113", "7")), "Mozi" + "lla/5.0 (X11)", "0123456789abcdef" * 2
        samples = {ip: verify.IPV4, agent: verify.UA, identifier: verify.HEX32}
        for text, pattern in samples.items():
            self.assertTrue(pattern.search(text), text)
        self.assertFalse(verify.HEX32.search("a" * 64))
        self.assertFalse(verify.IPV4.search("version 2.4.0-proposed"))

    def test_small_cell_policy_forbids_daily_path_and_actor(self):
        policy = load_json(REPO_ROOT / "config" / "small-cell-policy.json")
        self.assertTrue(policy["fixed_before_results"])
        self.assertIn("day x path", policy["forbidden_combinations"])
        self.assertIn("day x actor_name", policy["forbidden_combinations"])
        daily = next(g for g in policy["grains"] if g["grain_id"] == "daily_site_population")
        self.assertNotIn("path", daily["dimensions"])
        self.assertNotIn("actor_name", daily["dimensions"])

    def test_ci_workflow_has_no_secret_schedule_or_write_permission(self):
        report = verify.Report()
        verify.check_maintenance(report)
        result = {c["check"]: c for c in report.checks}
        self.assertTrue(result["ci_offline_pinned_read_only_without_secrets"]["passed"],
                        result["ci_offline_pinned_read_only_without_secrets"]["detail"])
        self.assertTrue(result["schedules_are_inactive_templates"]["passed"])


class FrenchTypographyTests(unittest.TestCase):
    def test_idempotent_and_protects_code_and_urls(self):
        text = "Note : voir « ceci » ; vraiment ? 12 % `a : b` https://x.y/a:b"
        once = typo.fr(text)
        self.assertEqual(typo.fr(once), once)
        self.assertIn("Note\u00a0:", once)
        self.assertIn("«\u202fceci\u202f»", once)
        self.assertIn("`a : b`", once)
        self.assertIn("https://x.y/a:b", once)
        self.assertEqual(typo.dash_violations("un tiret \u2014 interdit"), 1)
        self.assertEqual(typo.dash_violations("`code \u2014`"), 0)


if __name__ == "__main__":
    unittest.main()

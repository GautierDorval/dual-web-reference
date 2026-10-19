"""Rendering checks on the committed public edition (offline, read-only)."""

import re
import unittest

from tests import __init__  # noqa: F401
from dwr import figures as F
from dwr import render as R
from dwr import svg as S
from dwr.common import REPO_ROOT, load_json, read_csv

EDITION = load_json(REPO_ROOT / "config" / "editions.json")["candidate"]


class RenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.edition = R.Edition(EDITION)

    def test_figures_are_deterministic(self):
        for function in (F.figure_g01, F.figure_g02, F.figure_g08):
            first, _ = function(self.edition.ctx, "fr", True)
            second, _ = function(self.edition.ctx, "fr", True)
            self.assertEqual(first, second)

    def test_legend_values_come_from_the_figure_table(self):
        text, rows = F.figure_g02(self.edition.ctx, "en", False)
        for row in rows:
            self.assertEqual(row["total_get200"], row["llms_txt_get200"] + row["other_get200"])
            self.assertIn(f"total {row['total_get200']:,}", text)
        self.assertEqual(rows[0]["total_get200"], self.edition.m("main.get200"))

    def test_every_figure_carries_period_unit_population_and_source(self):
        from xml.etree import ElementTree
        for figure_id, function, _, extra in R.figure_jobs(self.edition):
            for lang in ("en", "fr"):
                for compact in (False, True):
                    text, _ = R.render_figure(self.edition, function, extra, lang, compact)
                    root = ElementTree.fromstring(text)
                    visible = re.sub(r"\s+", "", "".join("".join(e.itertext()) for e in root.iter("{http://www.w3.org/2000/svg}text")))
                    for value in (EDITION, "UTC", "data/editions/" + EDITION + "/",
                                  self.edition.catalog["dates"]["period_end_exclusive"] + "T00:00:00Z"):
                        self.assertIn(value, visible, (figure_id, lang, compact))
                    self.assertIn("<desc", text, figure_id)
                    self.assertNotIn("<script", text, figure_id)

    def test_heat_map_comes_from_joint_cells_and_sums_to_its_table(self):
        text, rows = F.figure_g06(self.edition.ctx, "en", False)
        self.assertIn("never from marginals", " ".join(re.sub(r"<[^>]+>", " ", text).split()))
        family = read_csv(self.edition.dir / "daily-family-summary.csv")
        plotted = sum(r["request_count"] for r in rows)
        self.assertEqual(plotted, sum(int(r["request_count"]) for r in family))
        expected = self.edition.m("main.role.ai_training.get200") + self.edition.m("main.role.ai_search.get200")
        self.assertEqual(plotted, expected)

    def test_document_graph_never_claims_observed_paths(self):
        cases = load_json(REPO_ROOT / "config" / "cases.json")["cases"]
        case = cases[1]
        nodes = [{"path": p, "layer": l, "kind": "file"} for p, l in case["graph_layers"].items()]
        text, _ = F.figure_g09(self.edition.ctx, "en", False, {"site_id": case["site_id"], "nodes": nodes,
                                                               "graph_snapshot_id": "graph-test"})
        plain = lambda svg: " ".join(re.sub(r"<[^>]+>", " ", svg).split())
        self.assertIn("not observed robot paths", plain(text))
        fr, _ = F.figure_g09(self.edition.ctx, "fr", False, {"site_id": case["site_id"], "nodes": nodes,
                                                             "graph_snapshot_id": "graph-test"})
        self.assertIn("pas des parcours de robots observés", plain(fr))

    def test_axes_start_at_zero_with_integer_steps(self):
        for maximum in (0, 1, 5, 6, 44, 302, 12476):
            top, grid = S.axis(maximum)
            self.assertEqual(grid[0], 0)
            self.assertGreaterEqual(top, maximum)
            self.assertTrue(all(isinstance(value, int) for value in grid))
            self.assertLessEqual(len(grid), 6)

    def test_stable_tie_order_in_rankings(self):
        _, first = F.figure_g05(self.edition.ctx, "en", False)
        _, second = F.figure_g05(self.edition.ctx, "en", False)
        self.assertEqual(first, second)
        for site in {row["site_id"] for row in first}:
            ranked = [row for row in first if row["site_id"] == site]
            self.assertEqual(ranked, sorted(ranked, key=lambda r: (-r["provider_origin_ai_get200"], r["path"])))

    def test_case_tables_use_published_counts(self):
        summary = {(r["site_id"], r["path"]): r for r in read_csv(self.edition.dir / "resource-summary.csv")}
        pages = R.render_cases(self.edition, write=False)
        page = pages["cases/pagup.com/README.md"]
        count = summary[("pagup.com", "/dualweb-index.md")]["provider_origin_ai_get200"]
        self.assertRegex(page, r"\| `/dualweb-index\.md` \| " + count + r" \|")


if __name__ == "__main__":
    unittest.main()

import unittest

from tests import __init__  # noqa: F401
from dwr import graph


def kinds(relations):
    return sorted((r["relation_type"], r["target_site"], r["target_path"]) for r in relations)


class GraphTests(unittest.TestCase):
    def test_html_anchors_and_external_targets(self):
        html = b'<a href="/llms.txt">x</a> <a href=\'https://pagup.com/identity.json#a\'>y</a> <a href="https://example.org/">z</a> <a href="#top">t</a>'
        found = graph.relations_in_file("pagup.com", "/", html, "index.html")
        self.assertEqual(kinds(found), [("html_anchor", "external", None), ("html_anchor", "pagup.com", "/identity.json"),
                                        ("html_anchor", "pagup.com", "/llms.txt")])

    def test_markdown_relative_links_and_bare_urls(self):
        text = b"See [canon](canon.md) and [up](../x/y.md).\nAlso https://better-robots.com/plugin-scope.md, done.\n"
        found = graph.relations_in_file("better-robots.com", "/docs/a.md", text, "a.md")
        self.assertIn(("markdown_link", "better-robots.com", "/docs/canon.md"), kinds(found))
        self.assertIn(("markdown_link", "better-robots.com", "/x/y.md"), kinds(found))
        self.assertIn(("plain_url_mention", "better-robots.com", "/plugin-scope.md"), kinds(found))

    def test_json_references_and_declared_relations(self):
        doc = b'{"related": ["/claims.json"], "items": [{"url": "https://www.gautierdorval.com/identity.json"}], "note": "a / b"}'
        found = graph.relations_in_file("gautierdorval.com", "/ai-manifest.json", doc, "ai-manifest.json")
        self.assertIn(("declared_relation", "gautierdorval.com", "/claims.json"), kinds(found))
        self.assertIn(("json_reference", "gautierdorval.com", "/identity.json"), kinds(found))
        self.assertEqual(len(found), 2)

    def test_sitemap_entries_and_invalid_json(self):
        xml = b"<urlset><url><loc>https://pagup.com/a/</loc></url></urlset>"
        self.assertEqual(kinds(graph.relations_in_file("pagup.com", "/sitemap.xml", xml, "sitemap.xml")),
                         [("sitemap_entry", "pagup.com", "/a/")])
        self.assertEqual(graph.relations_in_file("pagup.com", "/x.json", b"{broken", "x.json"), [])

    def test_unsafe_schemes_are_ignored(self):
        html = b'<a href="javascript:alert(1)">a</a><a href="mailto:x@y">b</a><a href="data:text/html,x">c</a>'
        self.assertEqual(graph.relations_in_file("pagup.com", "/", html, "index.html"), [])


if __name__ == "__main__":
    unittest.main()

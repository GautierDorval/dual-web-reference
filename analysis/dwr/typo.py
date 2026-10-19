"""FR-CA typography for generated and hand-written French text.

Idempotent: narrow no-break space inside « » and before ; ! ?, no-break space
before : and %. Inline code, fenced code, URLs and HTML tags are left untouched.
"""

from __future__ import annotations

import re

NNBSP = " "
NBSP = " "
PROTECTED = re.compile(r"(```.*?```|`[^`\n]*`|<[^>\n]+>|https?://\S+|\]\([^)\s]*\))", re.DOTALL)


def _fix(segment: str) -> str:
    pieces = re.split(r'(«[^»]*»|“[^”]*”|"[^"\n]*")', segment)
    for index in range(0, len(pieces), 2):
        pieces[index] = re.sub(r"(?<=\d) (?=\d{3}(?:\D|$))", NNBSP, pieces[index])
        pieces[index] = re.sub(r"[ \u00a0\u202f]+,", ",", pieces[index])
    segment = "".join(pieces)
    segment = re.sub(r"«[   ]*", "«" + NNBSP, segment)
    segment = re.sub(r"[   ]*»", NNBSP + "»", segment)
    segment = re.sub(r"[   ]+([;!?])", NNBSP + r"\1", segment)
    segment = re.sub(r"[   ]+:(?=\s|$)", NBSP + ":", segment)
    segment = re.sub(r"(\d)[   ]*%", r"\1" + NBSP + "%", segment)
    return segment


def fr(text: str) -> str:
    out, last = [], 0
    for match in PROTECTED.finditer(text):
        out.append(_fix(text[last:match.start()]))
        out.append(match.group(0))
        last = match.end()
    out.append(_fix(text[last:]))
    return "".join(out)


FORBIDDEN_DASHES = ("–", "—")


def dash_violations(text: str) -> int:
    stripped = PROTECTED.sub("", text)
    return sum(stripped.count(dash) for dash in FORBIDDEN_DASHES)


def punctuation_violations(text: str) -> int:
    """Keep literal contents opaque, but retain their boundary before punctuation."""
    stripped = PROTECTED.sub(lambda match: "" if match[0].startswith("<") else "x", text)
    stripped = re.sub(r'«[^»]*»|“[^”]*”|"[^"\n]*"|&(?:#[xX]?[0-9a-fA-F]+|[a-zA-Z]+);', "x", stripped)
    return len(re.findall(r"(?<=[\w)»\]])[;!?]", stripped))


def html_punctuation_violations(text: str) -> int:
    """Check rendered prose across inline tags, excluding literal code and scripts."""
    from html.parser import HTMLParser

    class Prose(HTMLParser):
        blocks = {"p", "div", "section", "article", "header", "footer", "nav", "main", "aside",
                  "h1", "h2", "h3", "h4", "h5", "h6", "li", "ul", "ol", "table", "tr", "th", "td", "br"}
        literals = {"code", "pre", "script", "style"}

        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.parts, self.hidden = [], []

        def handle_starttag(self, tag, attrs):
            if tag in self.literals:
                if not self.hidden:
                    self.parts.append("x" if tag == "code" else "\n")
                self.hidden.append(tag)
            elif not self.hidden and tag in self.blocks:
                self.parts.append("\n")

        def handle_endtag(self, tag):
            if self.hidden:
                if tag == self.hidden[-1]:
                    self.hidden.pop()
            elif tag in self.blocks:
                self.parts.append("\n")

        def handle_data(self, data):
            if not self.hidden:
                self.parts.append(data)

    parser = Prose()
    parser.feed(text)
    parser.close()
    return punctuation_violations("".join(parser.parts))

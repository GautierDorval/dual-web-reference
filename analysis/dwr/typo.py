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
    """Missing French spacing in prose; code, URLs, entities and quotations stay literal."""
    stripped = PROTECTED.sub("", text)
    stripped = re.sub(r'«[^»]*»|“[^”]*”|"[^"\n]*"|&(?:#[xX]?[0-9a-fA-F]+|[a-zA-Z]+);', "", stripped)
    return len(re.findall(r"(?<=[\w)»])[;!?](?=\s|$)", stripped))

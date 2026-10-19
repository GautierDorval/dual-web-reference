"""Minimal deterministic SVG writer for the figures.

No randomness, no timestamps, fixed float formatting, stable element order.
Every text node is XML-escaped (labels such as paths are untrusted data). Colors
are CSS custom properties with a dark-mode block inside each file, so the same
SVG adapts in GitHub, in the static site and when opened directly. No scripts,
no external references, system font stack only (no font is redistributed).
"""

from __future__ import annotations

import re
from xml.sax.saxutils import escape

FONT = "system-ui, -apple-system, 'Segoe UI', Roboto, 'Noto Sans', 'Liberation Sans', Arial, sans-serif"
STYLE = """
svg{--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#6f6e69;--grid:#e1e0d9;--axis:#c9c8c1;
--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s5:#e87ba4;--s7:#6250d6;--neutral:#a3a29b;--neutral2:#d4d3cc;
--missing:#7a5c00;--band:#f3efe2}
@media (prefers-color-scheme: dark){svg{--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--muted:#a3a29b;
--grid:#2c2c2a;--axis:#4a4945;--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s5:#d55181;--s7:#9085e9;
--neutral:#7d7c76;--neutral2:#4a4945;--missing:#e0b84a;--band:#2a2720}}
text{font-family:FONT;fill:var(--ink)}
.t{font-size:17px;font-weight:600}.st{font-size:13px;fill:var(--ink2)}.ax{font-size:12px;fill:var(--muted)}
.lb{font-size:12.5px;fill:var(--ink2)}.vl{font-size:12.5px;font-weight:600;fill:var(--ink)}
.ft{font-size:11.5px;fill:var(--muted)}.na{font-size:15px;font-weight:600;fill:var(--missing)}
.grid{stroke:var(--grid);stroke-width:1}.axis{stroke:var(--axis);stroke-width:1}
""".replace("FONT", FONT.replace("'", "&apos;"))

CHAR = 0.56  # average glyph width relative to font size, conservative for the system stack


def f(value: float) -> str:
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def text_width(text: str, size: float) -> float:
    return len(text) * size * CHAR


def wrap(text: str, size: float, width: float) -> list[str]:
    # Keep French punctuation attached to the preceding word before breaking lines.
    text = re.sub(r" ([:;!?\u00bb%])", "\u00a0\\1", text).replace("\u00ab ", "\u00ab\u00a0")
    limit = max(1, int(width / (size * CHAR)))
    words = [part for word in text.split(" ") for part in ([word[i:i+limit] for i in range(0, len(word), limit)] if len(word) > limit else [word])]
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and text_width(candidate, size) > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


class Svg:
    def __init__(self, width: int, title: str, desc: str):
        self.width = width
        self.parts: list[str] = []
        self.title = title
        self.desc = desc
        self.defs: list[str] = []

    def add(self, fragment: str) -> None:
        self.parts.append(fragment)

    def text(self, x, y, content, cls="lb", anchor="start", extra=""):
        self.add(f'<text x="{f(x)}" y="{f(y)}" class="{cls}" text-anchor="{anchor}"{extra}>{escape(str(content))}</text>')

    def rect(self, x, y, w, h, fill, rx=0, title=None, extra=""):
        inner = f"<title>{escape(title)}</title>" if title else ""
        radius = f' rx="{f(rx)}"' if rx else ""
        self.add(f'<rect x="{f(x)}" y="{f(y)}" width="{f(max(w, 0))}" height="{f(max(h, 0))}" '
                 f'fill="{fill}"{radius}{extra}>{inner}</rect>')

    def bar_h(self, x, y, w, h, fill, title=None):
        """Horizontal bar, square at the baseline (left), 4px rounded data end."""
        if w <= 0:
            return
        r = min(4, w, h / 2)
        path = (f"M{f(x)},{f(y)}H{f(x + w - r)}Q{f(x + w)},{f(y)} {f(x + w)},{f(y + r)}"
                f"V{f(y + h - r)}Q{f(x + w)},{f(y + h)} {f(x + w - r)},{f(y + h)}H{f(x)}Z")
        inner = f"<title>{escape(title)}</title>" if title else ""
        self.add(f'<path d="{path}" fill="{fill}">{inner}</path>')

    def bar_v(self, x, y_base, w, h, fill, title=None):
        """Vertical column from the baseline up, 4px rounded top."""
        if h <= 0:
            return
        r = min(4, h, w / 2)
        top = y_base - h
        path = (f"M{f(x)},{f(y_base)}V{f(top + r)}Q{f(x)},{f(top)} {f(x + r)},{f(top)}H{f(x + w - r)}"
                f"Q{f(x + w)},{f(top)} {f(x + w)},{f(top + r)}V{f(y_base)}Z")
        inner = f"<title>{escape(title)}</title>" if title else ""
        self.add(f'<path d="{path}" fill="{fill}">{inner}</path>')

    def line(self, x1, y1, x2, y2, cls="grid", extra=""):
        self.add(f'<line x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2)}" y2="{f(y2)}" class="{cls}"{extra}/>')

    def hatch(self, pattern_id: str) -> str:
        if pattern_id not in "".join(self.defs):
            self.defs.append(
                f'<pattern id="{pattern_id}" width="6" height="6" patternUnits="userSpaceOnUse" '
                f'patternTransform="rotate(45)"><rect width="6" height="6" fill="var(--band)"/>'
                f'<line x1="0" y1="0" x2="0" y2="6" stroke="var(--missing)" stroke-width="1.5"/></pattern>')
        return f"url(#{pattern_id})"

    def render(self, height: float) -> str:
        defs = f"<defs>{''.join(self.defs)}</defs>" if self.defs else ""
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{f(height)}" '
                f'viewBox="0 0 {self.width} {f(height)}" role="img" aria-labelledby="title desc">'
                f'<title id="title">{escape(self.title)}</title><desc id="desc">{escape(self.desc)}</desc>'
                f"<style>{STYLE}</style>{defs}"
                f'<rect x="0" y="0" width="{self.width}" height="{f(height)}" fill="var(--surface)"/>'
                + "".join(self.parts) + "</svg>\n")


def header(svg: Svg, title: str, subtitles: list[str], width: float, compact: bool) -> float:
    y = 30
    for line in wrap(title, 17, width - 40):
        svg.text(20, y, line, "t")
        y += 22
    y += 2
    for subtitle in subtitles:
        for line in wrap(subtitle, 13, width - 40):
            svg.text(20, y, line, "st")
            y += 17
    return y + 10


def footer(svg: Svg, y: float, lines: list[str], width: float) -> float:
    y += 8
    svg.line(20, y, width - 20, y, "grid")
    y += 18
    for entry in lines:
        for line in wrap(entry, 11.5, width - 40):
            svg.text(20, y, line, "ft")
            y += 15
    return y + 8


NICE_STEPS = (1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 2500, 5000, 10000, 20000, 25000, 50000)


def axis(maximum: float, max_ticks: int = 5) -> tuple[int, list[int]]:
    """Linear axis from zero: integer steps, at most `max_ticks` intervals, never truncated."""
    if maximum <= 0:
        return 1, [0, 1]
    for step in NICE_STEPS:
        count = -(-int(maximum) // step) if maximum == int(maximum) else int(maximum // step) + 1
        if count <= max_ticks:
            top = step * max(count, 1)
            return top, [step * i for i in range(max(count, 1) + 1)]
    return int(maximum), [0, int(maximum)]

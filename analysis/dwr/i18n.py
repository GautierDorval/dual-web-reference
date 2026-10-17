"""Display formatting. Data files keep plain digits and ISO dates; only displays
apply language conventions (FR-CA: narrow no-break space thousands separator and
a no-break space before % and colons)."""

from __future__ import annotations

from datetime import date

NNBSP = " "
NBSP = " "
FR_MONTHS_SHORT = ("janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc.")
EN_MONTHS_SHORT = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def number(value, lang: str) -> str:
    if value is None:
        return "n/d" if lang == "fr" else "n/a"
    if isinstance(value, float) and not value.is_integer():
        text = f"{value:,.1f}"
    else:
        text = f"{int(value):,}"
    return text.replace(",", NNBSP) if lang == "fr" else text


def percent(ratio, lang: str, digits: int = 1) -> str:
    if ratio is None:
        return "non calculable" if lang == "fr" else "not calculable"
    text = f"{ratio * 100:.{digits}f}"
    return f"{text}{NBSP}%" if lang == "fr" else f"{text}%"


def short_date(day: date, lang: str) -> str:
    if lang == "fr":
        return f"{day.day} {FR_MONTHS_SHORT[day.month - 1]}"
    return f"{EN_MONTHS_SHORT[day.month - 1]} {day.day}"


def colon(lang: str) -> str:
    return f"{NBSP}:" if lang == "fr" else ":"


def t(lang: str, en: str, fr: str) -> str:
    return fr if lang == "fr" else en


def cap(text: str) -> str:
    """Upper-case the first character only (str.capitalize would lower-case UTC)."""
    return text[:1].upper() + text[1:]

"""Edition windows, all in UTC with an exclusive end.

A window [start, end) is described by its inclusive start, its exclusive end and
its last included date. Monthly reference editions are anchored on day 15: the
first one is [2026-09-15, 2026-10-15) (30 days), the next one
[2026-10-15, 2026-11-15) (31 days). Local daylight-saving changes never enter
these calculations because only calendar dates in UTC are used.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from .common import DATE_PATTERN, DwrError

FR_MONTHS = (
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
)
EN_MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)


def parse_date(value: str) -> date:
    if not isinstance(value, str) or not DATE_PATTERN.match(value):
        raise DwrError("date_invalid", repr(value)[:40])
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise DwrError("date_invalid", value) from error


@dataclass(frozen=True)
class Window:
    start: date
    end_exclusive: date

    def __post_init__(self):
        if self.end_exclusive <= self.start:
            raise DwrError("window_empty_or_reversed", f"{self.start}..{self.end_exclusive}")

    @property
    def days(self) -> int:
        return (self.end_exclusive - self.start).days

    @property
    def last_included(self) -> date:
        return self.end_exclusive - timedelta(days=1)

    def contains(self, day: date) -> bool:
        return self.start <= day < self.end_exclusive

    def dates(self) -> list[date]:
        return [self.start + timedelta(days=offset) for offset in range(self.days)]

    @property
    def start_utc(self) -> str:
        return f"{self.start.isoformat()}T00:00:00Z"

    @property
    def end_exclusive_utc(self) -> str:
        return f"{self.end_exclusive.isoformat()}T00:00:00Z"

    def edition_id(self, revision: int) -> str:
        if not isinstance(revision, int) or revision < 1:
            raise DwrError("revision_invalid", repr(revision))
        return f"{self.start.isoformat()}_{self.end_exclusive.isoformat()}-r{revision}"

    def label_fr(self) -> str:
        first, last = self.start, self.last_included
        if first.year == last.year:
            head = f"du {_day_fr(first.day)} {FR_MONTHS[first.month - 1]}"
        else:
            head = f"du {_day_fr(first.day)} {FR_MONTHS[first.month - 1]} {first.year}"
        return (f"{head} au {_day_fr(last.day)} {FR_MONTHS[last.month - 1]} {last.year} "
                "inclusivement, en UTC")

    def label_en(self) -> str:
        first, last = self.start, self.last_included
        year = "" if first.year == last.year else f", {first.year}"
        return (f"{EN_MONTHS[first.month - 1]} {first.day}{year} to "
                f"{EN_MONTHS[last.month - 1]} {last.day}, {last.year} inclusive, UTC")


def _day_fr(day: int) -> str:
    return "1er" if day == 1 else str(day)


def add_months(day: date, months: int) -> date:
    index = day.month - 1 + months
    year, month = day.year + index // 12, index % 12 + 1
    return date(year, month, day.day)


def monthly_window(anchor_start: date, anchor_day: int = 15) -> Window:
    if anchor_start.day != anchor_day:
        raise DwrError("monthly_window_not_anchored", anchor_start.isoformat())
    if not 1 <= anchor_day <= 28:
        raise DwrError("anchor_day_must_exist_in_every_month", str(anchor_day))
    return Window(anchor_start, add_months(anchor_start, 1))


def next_monthly_window(window: Window, anchor_day: int = 15) -> Window:
    return monthly_window(window.end_exclusive, anchor_day)


def window_from_strings(start: str, end_exclusive: str) -> Window:
    return Window(parse_date(start), parse_date(end_exclusive))


def last_closed_day(now: datetime) -> date:
    """The current UTC day is never included: the last closed day is yesterday (UTC)."""
    if now.tzinfo is None:
        raise DwrError("naive_datetime_refused")
    return now.astimezone(timezone.utc).date() - timedelta(days=1)


def rolling_window(last_closed: date, days: int = 30) -> Window:
    return Window(last_closed - timedelta(days=days - 1), last_closed + timedelta(days=1))


def consolidation_ready(window: Window, now: datetime, delay_hours: int) -> bool:
    if now.tzinfo is None:
        raise DwrError("naive_datetime_refused")
    closes = datetime.combine(window.end_exclusive, datetime.min.time(), tzinfo=timezone.utc)
    return now.astimezone(timezone.utc) >= closes + timedelta(hours=delay_hours)


def latest_closed_monthly_window(first: Window, now: datetime, anchor_day: int = 15) -> Window | None:
    """The most recent monthly window whose exclusive end is not after the last closed day + 1."""
    limit = last_closed_day(now) + timedelta(days=1)
    if first.end_exclusive > limit:
        return None
    current = first
    while True:
        following = next_monthly_window(current, anchor_day)
        if following.end_exclusive > limit:
            return current
        current = following

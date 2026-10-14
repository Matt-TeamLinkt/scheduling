"""Forgiving parsers for the values people actually type into spreadsheets."""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta

from .table import Cell

MONTHS = {
    m: i
    for i, names in enumerate(
        [
            ("jan", "january"),
            ("feb", "february"),
            ("mar", "march"),
            ("apr", "april"),
            ("may",),
            ("jun", "june"),
            ("jul", "july"),
            ("aug", "august"),
            ("sep", "sept", "september"),
            ("oct", "october"),
            ("nov", "november"),
            ("dec", "december"),
        ],
        1,
    )
    for m in names
}
EXCEL_EPOCH = date(1899, 12, 30)


def text(c: Cell) -> str | None:
    if c is None:
        return None
    if isinstance(c, float) and c.is_integer():
        c = int(c)
    s = re.sub(r"\s+", " ", str(c)).strip()
    return s or None


def key(s: str) -> str:
    """Comparison key: 'U-11 ', 'u11' and 'Under 11' all become 'u11'."""
    s = s.lower()
    s = re.sub(r"\bunder\s*", "u", s)
    return re.sub(r"[^a-z0-9]", "", s)


def tidy_name(s: str) -> str:
    """Collapse spaces; fix ALL CAPS or all lower case names."""
    s = re.sub(r"\s+", " ", s).strip()
    if s.islower() or s.isupper():
        s = " ".join(w[:1].upper() + w[1:].lower() for w in s.split(" "))
        s = re.sub(r"\b(Mc|Mac|O')([a-z])", lambda m: m.group(1) + m.group(2).upper(), s)
    return s


def split_people(s: str) -> list[str]:
    """'Sam Diaz / Priya Nair', 'A & B', 'A and B', 'A; B' -> separate names.
    'Ramsey, Alex' is one person, reordered to 'Alex Ramsey'. A comma only splits
    full names: 'Sam Diaz, Priya Nair'."""
    parts = re.split(r"\s*(?:/|&|;|\+|\band\b)\s*", s)
    out: list[str] = []
    for p in parts:
        bits = [b.strip() for b in p.split(",")]
        if len(bits) > 1 and all(" " in b for b in bits if b):
            out.extend(bits)
        elif len(bits) == 2 and all(b and " " not in b for b in bits):
            out.append(f"{bits[1]} {bits[0]}")  # "MacLeod, Robin" -> "Robin MacLeod"
        else:
            out.append(p)
    return [tidy_name(p) for p in out if p.strip()]


# ── dates ───────────────────────────────────────────────────────────────────

_NUMERIC_DATE = re.compile(r"^(\d{1,4})[/\-.](\d{1,2})[/\-.](\d{1,4})$")


def date_order_hint(values: list[str]) -> tuple[bool, bool]:
    """Look at every numeric date in a column. Returns (day_first, ambiguous)."""
    day_first = month_first = ambiguous = False
    for v in values:
        m = _NUMERIC_DATE.match(v.strip())
        if not m or len(m.group(1)) == 4:
            continue
        a, b = int(m.group(1)), int(m.group(2))
        if a > 12:
            day_first = True
        elif b > 12:
            month_first = True
        elif a != b:
            ambiguous = True
    if day_first and not month_first:
        return True, False
    return False, ambiguous and not month_first


def parse_date(c: Cell, day_first: bool = False) -> date | None:
    if isinstance(c, datetime):
        return c.date()
    if isinstance(c, date):
        return c
    if isinstance(c, (int, float)) and 20000 < c < 80000:  # Excel serial day number
        return EXCEL_EPOCH + timedelta(days=int(c))
    s = text(c)
    if not s:
        return None
    s = s.lower().replace(",", " ")
    s = re.sub(r"\b(mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)[a-z]*\.?\s+", "", s)
    s = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", s).strip()
    try:
        m = _NUMERIC_DATE.match(s)
        if m:
            a, b, c3 = m.groups()
            if len(a) == 4:  # 2027-01-09
                return date(int(a), int(b), int(c3))
            year = int(c3) + (2000 if len(c3) == 2 else 0)
            day, month = (int(a), int(b)) if day_first else (int(b), int(a))
            return date(year, month, day)
        words = s.replace("-", " ").replace("/", " ").split()
        if len(words) == 3:
            # "jan 9 2027" or "9 jan 2027"
            if words[0][:3] in MONTHS or words[0] in MONTHS:
                mon, day_s, yr = words
            else:
                day_s, mon, yr = words
            month_num = MONTHS.get(mon) or MONTHS.get(mon[:3])
            if month_num:
                year = int(yr) + (2000 if len(yr) == 2 else 0)
                return date(year, month_num, int(day_s))
    except ValueError:
        return None
    return None


# ── times and durations ─────────────────────────────────────────────────────

_TIME = re.compile(r"^(\d{1,2})(?:[:.h](\d{2}))?\s*(a|p|am|pm|a\.m\.|p\.m\.)?$")


def parse_time(c: Cell) -> time | None:
    if isinstance(c, datetime):
        return c.time().replace(second=0, microsecond=0)
    if isinstance(c, time):
        return c.replace(second=0, microsecond=0)
    if isinstance(c, float) and 0 <= c < 1:  # Excel time as fraction of a day
        minutes = round(c * 24 * 60)
        return time(minutes // 60 % 24, minutes % 60)
    s = text(c)
    if not s:
        return None
    s = s.lower().strip()
    if s == "noon":
        return time(12)
    if s == "midnight":
        return time(0)
    if re.fullmatch(r"\d{3,4}", s):  # 1900, 730
        s = s[:-2] + ":" + s[-2:]
    m = _TIME.match(s.replace(" ", "") if re.search(r"[ap]", s) else s)
    if not m:
        return None
    hour, minute = int(m.group(1)), int(m.group(2) or 0)
    suffix = (m.group(3) or "").replace(".", "")
    if suffix:
        if not 1 <= hour <= 12:
            return None
        hour = hour % 12 + (12 if suffix.startswith("p") else 0)
    if hour > 23 or minute > 59:
        return None
    return time(hour, minute)


def parse_time_range(c: Cell) -> tuple[time, time] | None:
    """'7:00 PM - 8:15 PM', '7-8:15pm', '19:00 to 20:15'."""
    s = text(c)
    if not s:
        return None
    parts = re.split(r"\s*(?:-|–|—|\bto\b|\buntil\b)\s*", s.lower())
    if len(parts) != 2:
        return None
    start_s, end_s = parts
    start, end = parse_time(start_s), parse_time(end_s)
    if end is None:
        return None
    # "7-8:15pm": a bare start borrows the end's am/pm when that makes sense.
    suffix = re.search(r"(am|pm|a|p)\.?$", end_s.replace(" ", "").replace(".m.", "m"))
    if suffix and not re.search(r"[ap]", start_s):
        borrowed = parse_time(start_s + suffix.group(1))
        if borrowed is not None and borrowed < end:
            start = borrowed
    if start is None:
        return None
    return start, end


def parse_minutes(c: Cell) -> int | None:
    """'60', '60 min', '1:15', '1h15', '1.5 hours', '75m'."""
    if isinstance(c, (int, float)) and not isinstance(c, bool):
        return int(c) if c > 0 else None
    if isinstance(c, time):
        return c.hour * 60 + c.minute or None
    s = text(c)
    if not s:
        return None
    s = s.lower().replace(" ", "")
    m = re.fullmatch(r"(\d+):(\d{2})", s) or re.fullmatch(
        r"(\d+)h(?:ours?|rs?)?(\d+)?m?(?:in)?s?", s
    )
    if m:
        return int(m.group(1)) * 60 + int(m.group(2) or 0) or None
    m = re.fullmatch(r"(\d+(?:\.\d+)?)(h|hr|hrs|hour|hours)", s)
    if m:
        return round(float(m.group(1)) * 60) or None
    m = re.fullmatch(r"(\d+)(m|min|mins|minute|minutes)?", s)
    if m:
        return int(m.group(1)) or None
    return None


def parse_money(c: Cell) -> float | None:
    if isinstance(c, (int, float)) and not isinstance(c, bool):
        return float(c)
    s = text(c)
    if not s:
        return None
    s = re.sub(r"[^\d.\-]", "", s.replace(",", ""))
    try:
        return float(s)
    except ValueError:
        return None

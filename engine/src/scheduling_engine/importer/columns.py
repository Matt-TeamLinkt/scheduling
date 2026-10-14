"""Match whatever column headers a file has to the fields we need."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from .table import RawRow
from .values import key, text


@dataclass(frozen=True)
class Field:
    name: str  # internal name
    label: str  # what we call it in messages: "team name"
    aliases: tuple[str, ...]
    required: bool = False


@dataclass(frozen=True)
class ColumnMatch:
    header: str
    field: str | None  # Field.label, or None = ignored


def _score(header_key: str, f: Field) -> float:
    best = 0.0
    for alias in f.aliases:
        a = key(alias)
        if header_key == a:
            return 1.0
        if a and a in header_key:
            # "Team Name (required)" contains "teamname"; longer aliases win.
            best = max(best, 0.7 + 0.2 * len(a) / len(header_key))
        ratio = SequenceMatcher(None, header_key, a).ratio()
        if ratio >= 0.85:  # typos like "Divison"
            best = max(best, ratio * 0.9)
    return best


def match_columns(headers: list[str | None], fields: list[Field]) -> dict[str, int]:
    """Return {field name: column index}. Each field and column is used at most once."""
    candidates: list[tuple[float, int, Field]] = []
    for i, h in enumerate(headers):
        if not h:
            continue
        hk = key(h)
        if not hk:
            continue
        for f in fields:
            s = _score(hk, f)
            if s > 0:
                candidates.append((s, i, f))
    candidates.sort(key=lambda c: (-c[0], c[1]))
    used_cols: set[int] = set()
    out: dict[str, int] = {}
    for _, i, f in candidates:
        if f.name in out or i in used_cols:
            continue
        out[f.name] = i
        used_cols.add(i)
    return out


def find_header(rows: list[RawRow], fields: list[Field]) -> int | None:
    """Index into rows of the header row: the one in the first 10 that matches the most
    fields. Skips title rows like 'Spring 2027 teams' above the real header."""
    best: tuple[int, int] | None = None  # (matches, -index)
    for idx, row in enumerate(rows[:10]):
        headers = [text(c) for c in row.cells]
        n = len(match_columns(headers, fields))
        if n and (best is None or n > best[0]):
            best = (n, -idx)
    return -best[1] if best else None


def describe_columns(
    headers: list[str | None], mapping: dict[str, int], fields: list[Field]
) -> list[ColumnMatch]:
    by_col = {i: next(f.label for f in fields if f.name == n) for n, i in mapping.items()}
    return [ColumnMatch(header=h, field=by_col.get(i)) for i, h in enumerate(headers) if h]

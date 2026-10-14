"""Shared steps: read the file, find the header, map the columns."""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import get_close_matches

from .columns import ColumnMatch, Field, describe_columns, find_header, match_columns
from .plan import Problem, skipped
from .table import Cell, RawRow, UnreadableFile, read_rows
from .values import key, text


@dataclass
class Sheet:
    rows: list[RawRow]  # data rows only (header removed)
    cols: dict[str, int]
    columns: list[ColumnMatch]
    problems: list[Problem] = field(default_factory=list)

    def get(self, row: RawRow, name: str) -> Cell:
        i = self.cols.get(name)
        if i is None or i >= len(row.cells):
            return None
        return row.cells[i]

    def text(self, row: RawRow, name: str) -> str | None:
        return text(self.get(row, name))

    def has(self, name: str) -> bool:
        return name in self.cols


def open_sheet(data: bytes, filename: str, fields: list[Field], what: str) -> Sheet:
    """Read and map a file. On a file-level problem the Sheet has no rows and one
    SKIPPED problem explaining what to do."""
    try:
        raw = read_rows(data, filename)
    except UnreadableFile as exc:
        return Sheet([], {}, [], [skipped(None, str(exc))])
    hi = find_header(raw, fields)
    if hi is None:
        labels = ", ".join(f.label for f in fields if f.required)
        return Sheet(
            [],
            {},
            [],
            [
                skipped(
                    None,
                    f"We couldn't find column headers in this file. The first row should name "
                    f"the columns, for example: {labels}.",
                )
            ],
        )
    headers = [text(c) for c in raw[hi].cells]
    cols = match_columns(headers, fields)
    sheet = Sheet(raw[hi + 1 :], cols, describe_columns(headers, cols, fields))
    missing = [f for f in fields if f.required and f.name not in cols]
    for f in missing:
        sheet.problems.append(
            skipped(
                None,
                f"We couldn't find a column for {f.label} in this {what} file. "
                f'Add a column headed "{f.aliases[0].title()}" and try again.',
            )
        )
    if missing:
        sheet.rows = []
    return sheet


def closest(name: str, options: list[str]) -> str | None:
    """The option that looks most like `name`, if any is close (for 'did you mean')."""
    by_key = {key(o): o for o in options}
    hit = get_close_matches(key(name), list(by_key), n=1, cutoff=0.75)
    return by_key[hit[0]] if hit else None

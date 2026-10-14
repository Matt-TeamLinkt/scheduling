"""What an import will do, shown to the scheduler before anything changes."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import StrEnum

from ..model import Coach, Division, League, Slot, Surface, Team, Venue
from .columns import ColumnMatch


class ImportKind(StrEnum):
    TEAMS = "teams"
    COACHES = "coaches"
    SLOTS = "slots"


class Level(StrEnum):
    SKIPPED = "skipped"  # the row was left out; fix it and import again
    CHECK = "check"  # imported, but worth a look
    NOTE = "note"  # just so you know (e.g. a new division will be created)


@dataclass(frozen=True)
class Problem:
    row: int | None  # spreadsheet row number; None = about the whole file
    level: Level
    message: str


def skipped(row: int | None, message: str) -> Problem:
    return Problem(row, Level.SKIPPED, message)


def check(row: int | None, message: str) -> Problem:
    return Problem(row, Level.CHECK, message)


def note(row: int | None, message: str) -> Problem:
    return Problem(row, Level.NOTE, message)


@dataclass
class Changes:
    divisions: list[Division] = field(default_factory=list)
    teams: list[Team] = field(default_factory=list)
    coaches: list[Coach] = field(default_factory=list)  # new coaches
    coach_links: list[tuple[str, str]] = field(default_factory=list)  # (coach, team) existing
    venues: list[Venue] = field(default_factory=list)
    surfaces: list[Surface] = field(default_factory=list)
    slots: list[Slot] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        return not any(
            (
                self.divisions,
                self.teams,
                self.coaches,
                self.coach_links,
                self.venues,
                self.surfaces,
                self.slots,
            )
        )


@dataclass
class ImportPreview:
    kind: ImportKind
    filename: str
    columns: list[ColumnMatch]
    changes: Changes
    problems: list[Problem]
    summary: str
    rows_read: int = 0

    @property
    def can_import(self) -> bool:
        return not self.changes.empty

    def problems_at(self, level: Level) -> list[Problem]:
        return [p for p in self.problems if p.level == level]


def apply_import(league: League, preview: ImportPreview) -> League:
    """Return a new League with the previewed changes added. The original is untouched."""
    lg = league.model_copy(deep=True)
    ch = preview.changes
    lg.divisions.extend(d.model_copy() for d in ch.divisions)
    lg.teams.extend(t.model_copy() for t in ch.teams)
    lg.coaches.extend(c.model_copy(deep=True) for c in ch.coaches)
    coaches = {c.id: c for c in lg.coaches}
    for coach_id, team_id in ch.coach_links:
        c = coaches.get(coach_id)
        if c is not None and team_id not in c.team_ids:
            c.team_ids.append(team_id)
    lg.venues.extend(v.model_copy() for v in ch.venues)
    lg.surfaces.extend(s.model_copy() for s in ch.surfaces)
    lg.slots.extend(s.model_copy() for s in ch.slots)
    return lg


class Ids:
    """Readable, unique ids: 'Falcons' -> 't-falcons', then 't-falcons-2'."""

    def __init__(self, existing: Iterable[str]) -> None:
        self.used = set(existing)

    def make(self, prefix: str, name: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40] or "x"
        base = f"{prefix}-{slug}"
        candidate, n = base, 1
        while candidate in self.used:
            n += 1
            candidate = f"{base}-{n}"
        self.used.add(candidate)
        return candidate


def all_ids(lg: League) -> list[str]:
    return [
        x.id
        for group in (
            lg.divisions,
            lg.teams,
            lg.coaches,
            lg.families,
            lg.venues,
            lg.surfaces,
            lg.slots,
            lg.blackouts,
        )
        for x in group
    ]


def plural(n: int, word: str, many: str | None = None) -> str:
    return f"{n} {word if n == 1 else (many or word + 's')}"


def summarize(parts: list[str], problems: list[Problem], changes: Changes) -> str:
    if changes.empty:
        return "Nothing can be imported from this file yet. See the notes below."
    text = (
        "We'll add "
        + ", ".join(parts[:-1])
        + (" and " if len(parts) > 1 else "")
        + (parts[-1] + ".")
    )
    skipped = sum(1 for p in problems if p.level == Level.SKIPPED and p.row is not None)
    check = sum(1 for p in problems if p.level == Level.CHECK)
    if skipped:
        text += f" {plural(skipped, 'row')} will be left out."
    if check:
        text += f" {plural(check, 'row')} {'needs' if check == 1 else 'need'} a quick look."
    return text

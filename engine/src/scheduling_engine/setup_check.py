"""Sanity checks on a league setup, run before scheduling.

Forgiving by design: nothing raises. Every problem comes back as a plain-language
item the scheduler can fix. Errors block scheduling; warnings don't.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from .index import LeagueIndex, fmt_day, fmt_time
from .model import BlackoutScope, League, Slot


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class SetupProblem(BaseModel):
    model_config = ConfigDict(frozen=True)

    severity: Severity
    message: str
    ids: tuple[str, ...] = ()


def check_setup(league: League) -> list[SetupProblem]:
    ix = LeagueIndex(league)
    return [
        *_duplicate_ids(league),
        *_dangling(ix),
        *_rules(ix),
        *_slots(ix),
        *_division_sizes(ix),
    ]


def _err(msg: str, *ids: str) -> SetupProblem:
    return SetupProblem(severity=Severity.ERROR, message=msg, ids=ids)


def _warn(msg: str, *ids: str) -> SetupProblem:
    return SetupProblem(severity=Severity.WARNING, message=msg, ids=ids)


def _duplicate_ids(lg: League) -> Iterable[SetupProblem]:
    groups: dict[str, list[str]] = {
        "division": [d.id for d in lg.divisions],
        "team": [t.id for t in lg.teams],
        "coach": [c.id for c in lg.coaches],
        "family": [f.id for f in lg.families],
        "venue": [v.id for v in lg.venues],
        "surface": [s.id for s in lg.surfaces],
        "slot": [s.id for s in lg.slots],
        "blackout": [b.id for b in lg.blackouts],
    }
    for kind, ids in groups.items():
        for dup, n in Counter(ids).items():
            if n > 1:
                yield _err(f"{n} {kind}s share the id {dup!r}. Each needs its own.", dup)


def _dangling(ix: LeagueIndex) -> Iterable[SetupProblem]:
    lg = ix.league
    for t in lg.teams:
        if t.division_id not in ix.divisions:
            yield _err(f"Team {t.name} is in a division that doesn't exist.", t.id)
        if t.home_venue_id and t.home_venue_id not in ix.venues:
            yield _err(f"Team {t.name} has a home venue that doesn't exist.", t.id)
    for c in lg.coaches:
        for tid in c.team_ids:
            if tid not in ix.teams:
                yield _err(f"Coach {c.name} is listed on a team that doesn't exist.", c.id, tid)
    for f in lg.families:
        for tid in f.team_ids:
            if tid not in ix.teams:
                yield _err(f"The {f.name} family is listed on a team that doesn't exist.", f.id)
    for s in lg.surfaces:
        if s.venue_id not in ix.venues:
            yield _err(f"{s.name} belongs to a venue that doesn't exist.", s.id)
    for sl in lg.slots:
        if sl.surface_id not in ix.surfaces:
            yield _err(f"A time slot on {fmt_day(sl.start_dt)} is on an unknown surface.", sl.id)
    targets: dict[BlackoutScope, Mapping[str, object]] = {
        BlackoutScope.DIVISION: ix.divisions,
        BlackoutScope.TEAM: ix.teams,
        BlackoutScope.VENUE: ix.venues,
        BlackoutScope.SURFACE: ix.surfaces,
    }
    for b in lg.blackouts:
        pool = targets.get(b.scope)
        if pool is not None and b.target_id not in pool:
            yield _err(
                f"A blackout on {b.start_date} points at a {b.scope} that doesn't exist.", b.id
            )


def _rules(ix: LeagueIndex) -> Iterable[SetupProblem]:
    # Overrides are valid alone but can combine badly (e.g. a team's earliest start
    # after its division's latest end).
    for d in ix.league.divisions:
        try:
            ix.division_rules(d.id)
        except ValueError as exc:
            yield _err(f"The rules for {d.name} don't fit together: {exc}.", d.id)
    for t in ix.league.teams:
        if t.division_id not in ix.divisions:
            continue
        try:
            ix.team_rules(t.id)
        except ValueError as exc:
            yield _err(f"The rules for {t.name} don't fit together: {exc}.", t.id)


def _slots(ix: LeagueIndex) -> Iterable[SetupProblem]:
    lg = ix.league
    outside = [s for s in lg.slots if not lg.season_start <= s.date <= lg.season_end]
    if outside:
        yield _warn(
            f"{len(outside)} time slots are outside the season dates and won't be used.",
            *(s.id for s in outside),
        )
    by_surface: dict[str, list[Slot]] = defaultdict(list)
    for s in lg.slots:
        by_surface[s.surface_id].append(s)
    for slots in by_surface.values():
        slots.sort(key=lambda s: s.start_dt)
        for a, b in zip(slots, slots[1:], strict=False):
            if b.start_dt < a.end_dt:
                yield _warn(
                    f"Two time slots overlap on {ix.place(a.id)} on {fmt_day(a.start_dt)}: "
                    f"{fmt_time(a.start_dt)}–{fmt_time(a.end_dt)} and "
                    f"{fmt_time(b.start_dt)}–{fmt_time(b.end_dt)}. "
                    "Only one can be used at a time.",
                    a.id,
                    b.id,
                )


def _division_sizes(ix: LeagueIndex) -> Iterable[SetupProblem]:
    counts = Counter(t.division_id for t in ix.league.teams)
    for d in ix.league.divisions:
        n = counts.get(d.id, 0)
        if n < 2:
            yield _warn(
                f"{d.name} has {n} team{'s' if n != 1 else ''}, so it can't play games.", d.id
            )

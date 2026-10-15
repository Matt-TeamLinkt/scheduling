"""Partial regeneration: re-do part of a season without touching the rest.

    reschedule(league, events)                                    # everything not locked
    reschedule(league, events, Scope(division_ids={"d-u11"}))     # just U11
    reschedule(league, events, Scope(start=date(2027, 2, 1), end=date(2027, 2, 28)))

Locked games never move. Games outside the scope never move. Games in scope keep their
opponents and home/away; with a date range they stay inside it; each aims for the week
it's in now, so nothing jumps across the season unless it has to.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from .index import LeagueIndex
from .matchups import Matchup
from .model import Event, League
from .solver import Game, SolveOptions, SolveResult, Status, run
from .validate import validate


@dataclass(frozen=True)
class Scope:
    division_ids: frozenset[str] | None = None  # None = every division
    start: date | None = None  # only games currently in this window move ...
    end: date | None = None  # ... and they stay inside it

    def covers(self, e: Event) -> bool:
        if self.division_ids is not None and e.division_id not in self.division_ids:
            return False
        day = e.start.date()
        if self.start is not None and day < self.start:
            return False
        return not (self.end is not None and day > self.end)

    def describe(self, league: League) -> str:
        parts = []
        if self.division_ids is not None:
            names = sorted(d.name for d in league.divisions if d.id in self.division_ids)
            parts.append(", ".join(names))
        if self.start or self.end:
            a = f"{self.start:%b} {self.start.day}" if self.start else "the start"
            b = f"{self.end:%b} {self.end.day}" if self.end else "the end of the season"
            parts.append(f"games from {a} to {b}")
        return " · ".join(parts) or "the whole season"


def reschedule(
    league: League,
    events: Sequence[Event],
    scope: Scope | None = None,
    also_place: Sequence[Matchup] = (),
    options: SolveOptions | None = None,
) -> SolveResult:
    """Re-place the unlocked games in `scope` (plus any `also_place` matchups, e.g. games
    that didn't fit last time). Everything else stays exactly where it is."""
    scope = scope or Scope()
    ix = LeagueIndex(league)
    window = None
    if scope.start or scope.end:
        window = (scope.start or league.season_start, scope.end or league.season_end)

    fixed = [e for e in events if e.locked or not scope.covers(e)]
    fixed_ids = {e.id for e in fixed}
    problems = validate(league, fixed)
    if problems:
        notes = [
            "These games aren't being moved, but they break a rule. Unlock them or "
            "include them in what you reschedule:"
        ] + [v.message for v in problems]
        return SolveResult(Status.NO_SCHEDULE, list(events), [], 0.0, notes)

    games: list[Game] = []
    for e in events:
        if e.id in fixed_ids:
            games.append(_game(ix, e, fixed=True))
        else:
            g = _game(ix, e, fixed=False)
            g.window = window
            week = (e.start.date() - league.season_start).days // 7
            if window:
                lo = (window[0] - league.season_start).days // 7
                hi = (window[1] - league.season_start).days // 7
                week = min(max(week, lo), hi)
            g.target_week = week
            games.append(g)
    for m in also_place:
        g = Game(
            id=m.id,
            division_id=m.division_id,
            team_ids=m.team_ids,
            home_team_id=m.home_team_id,
            away_team_id=m.away_team_id,
            minutes=_minutes(ix, m.team_ids),
            units=_units(ix, m.team_ids),
            matchup=m,
            window=window,
        )
        games.append(g)

    result = run(
        league, games, options or SolveOptions(), [f"Rescheduled {scope.describe(league)}."]
    )
    # Keep the lock flag on games that had it.
    locked = {e.id for e in events if e.locked}
    result.events = [
        e.model_copy(update={"locked": True}) if e.id in locked else e for e in result.events
    ]
    return result


def _minutes(ix: LeagueIndex, teams: Sequence[str]) -> int:
    return max(ix.team_rules(t).game_minutes for t in teams)


def _units(ix: LeagueIndex, teams: Sequence[str]) -> int | None:
    units = [ix.team_rules(t).units for t in teams]
    return None if None in units else max(u for u in units if u is not None)


def _game(ix: LeagueIndex, e: Event, fixed: bool) -> Game:
    m = Matchup(e.id, e.division_id, e.home_team_id, e.away_team_id or e.home_team_id, 0)
    return Game(
        id=e.id,
        division_id=e.division_id,
        team_ids=e.team_ids,
        home_team_id=e.home_team_id,
        away_team_id=e.away_team_id,
        minutes=e.minutes,
        units=e.units if fixed else _units(ix, e.team_ids),
        fixed=e if fixed else None,
        matchup=m,
    )

from __future__ import annotations

from datetime import date, datetime, time, timedelta

import pytest

from scheduling_engine import Event, EventKind, League, fixtures
from scheduling_engine.index import LeagueIndex


@pytest.fixture
def small() -> League:
    return fixtures.small_8()


@pytest.fixture
def hockey() -> League:
    return fixtures.league_40()


@pytest.fixture
def nightmare() -> League:
    return fixtures.nightmare()


def slot_id(lg: League, surface_id: str, day: date, start: str) -> str:
    hh, mm = map(int, start.split(":"))
    for s in lg.slots:
        if s.surface_id == surface_id and s.date == day and s.start == time(hh, mm):
            return s.id
    raise LookupError(f"no slot on {surface_id} {day} {start}")


def game(
    lg: League,
    home: str,
    away: str | None,
    surface_id: str,
    day: date,
    start: str,
    *,
    id: str | None = None,
    offset: int = 0,
    minutes: int | None = None,
    units: int | None = None,
) -> Event:
    """Build an event in a fixture slot, using the team's own rules for length and size."""
    ix = LeagueIndex(lg)
    sid = slot_id(lg, surface_id, day, start)
    slot = ix.slots[sid]
    rules = ix.team_rules(home)
    return Event(
        id=id or f"e-{home}-{away}-{day}-{start}-{offset}",
        kind=EventKind.GAME if away else EventKind.PRACTICE,
        division_id=ix.teams[home].division_id,
        home_team_id=home,
        away_team_id=away,
        slot_id=sid,
        start=slot.start_dt + timedelta(minutes=offset),
        minutes=minutes or rules.game_minutes,
        units=units or rules.units or ix.surfaces[slot.surface_id].units,
    )


def at(day: date, hhmm: str) -> datetime:
    hh, mm = map(int, hhmm.split(":"))
    return datetime.combine(day, time(hh, mm))

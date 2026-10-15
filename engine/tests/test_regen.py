"""Partial regeneration: what's out of scope or locked never moves; the rest is legal."""

from __future__ import annotations

from datetime import date

import pytest

from scheduling_engine import Blackout, BlackoutScope, Event, League, fixtures, validate
from scheduling_engine.regen import Scope, reschedule
from scheduling_engine.solver import SolveOptions, Status, solve

QUICK = SolveOptions(time_limit_s=10, workers=4)


@pytest.fixture(scope="module")
def small_season() -> tuple[League, list[Event]]:
    lg = fixtures.small_8()
    return lg, solve(lg, options=QUICK).events


@pytest.fixture(scope="module")
def big_season() -> tuple[League, list[Event]]:
    lg = fixtures.league_40()
    r = solve(lg, options=SolveOptions(time_limit_s=20, workers=4))
    assert r.unplaced == []
    return lg, r.events


def by_id(events: list[Event]) -> dict[str, Event]:
    return {e.id: e for e in events}


def test_locked_games_never_move(small_season: tuple[League, list[Event]]) -> None:
    lg, events = small_season
    locked = {e.id for e in events[::4]}
    marked = [e.model_copy(update={"locked": e.id in locked}) for e in events]
    r = reschedule(lg, marked, options=QUICK)
    after = by_id(r.events)
    assert validate(lg, r.events) == []
    assert len(r.events) == len(events) and r.unplaced == []
    for e in marked:
        if e.locked:
            assert after[e.id] == e  # same slot, same time, still locked


def test_only_one_division_moves(big_season: tuple[League, list[Event]]) -> None:
    lg, events = big_season
    r = reschedule(lg, events, Scope(division_ids=frozenset({"d-u11"})), options=QUICK)
    after = by_id(r.events)
    assert validate(lg, r.events) == []
    assert r.unplaced == []
    for e in events:
        if e.division_id != "d-u11":
            assert after[e.id] == e
        else:
            # same opponents and home team, wherever it lands
            assert (after[e.id].home_team_id, after[e.id].away_team_id) == (
                e.home_team_id,
                e.away_team_id,
            )


def test_date_range_stays_inside_the_range(small_season: tuple[League, list[Event]]) -> None:
    lg, events = small_season
    may = Scope(start=date(2027, 5, 1), end=date(2027, 5, 31))
    r = reschedule(lg, events, may, options=QUICK)
    after = by_id(r.events)
    assert validate(lg, r.events) == []
    for e in events:
        if may.covers(e):
            assert may.covers(after[e.id])
        else:
            assert after[e.id] == e
    assert "Rescheduled games from May 1 to May 31." in r.notes


def test_games_that_didnt_fit_can_be_placed_later(small_season: tuple[League, list[Event]]) -> None:
    lg, events = small_season
    from scheduling_engine.matchups import Matchup

    dropped = events[0]
    rest = [e for e in events if e.id != dropped.id]
    m = Matchup(
        dropped.id, dropped.division_id, dropped.home_team_id, dropped.away_team_id or "", 0
    )
    r = reschedule(lg, rest, Scope(division_ids=frozenset()), also_place=[m], options=QUICK)
    assert validate(lg, r.events) == []
    assert dropped.id in by_id(r.events)
    assert all(by_id(r.events)[e.id] == e for e in rest)


def test_kept_games_that_break_a_rule_are_explained(
    small_season: tuple[League, list[Event]],
) -> None:
    lg, events = small_season
    lg = lg.model_copy(deep=True)
    first = events[0]
    lg.blackouts.append(
        Blackout(
            id="b-new",
            scope=BlackoutScope.LEAGUE,
            start_date=first.start.date(),
            end_date=first.start.date(),
            note="Field closed",
        )
    )
    locked = [e.model_copy(update={"locked": e.id == first.id}) for e in events]
    r = reschedule(lg, locked, options=QUICK)
    assert r.status == Status.NO_SCHEDULE
    assert r.notes[0].startswith("These games aren't being moved, but they break a rule.")
    assert any("Field closed" in n for n in r.notes)
    # Unlocking it lets the solver move it off the closed day.
    r2 = reschedule(lg, events, options=QUICK)
    assert validate(lg, r2.events) == [] and r2.unplaced == []

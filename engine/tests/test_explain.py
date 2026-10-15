from __future__ import annotations

import re
from datetime import time

import pytest

from scheduling_engine import Blackout, BlackoutScope, League, RuleOverrides, fixtures, validate
from scheduling_engine.explain import capacity_check, explain
from scheduling_engine.regen import Scope, reschedule
from scheduling_engine.solver import SolveOptions, solve

QUICK = SolveOptions(time_limit_s=10, workers=4)


def no_ids(text: str) -> bool:
    return not re.search(r"\b(t|c|s|sl|v|d|b|g)-[a-z0-9]", text)


def short_u15() -> League:
    lg = fixtures.league_40()
    lg.slots = [s for s in lg.slots if not (s.surface_id == "s-north-1" and s.date.weekday() == 6)]
    return lg


def test_capacity_check_explains_an_impossible_division() -> None:
    findings = capacity_check(short_u15())
    assert len(findings) == 1
    f = findings[0]
    assert f.division_id == "d-u15" and f.games == 12
    assert f.message == (
        "Each U15 team needs 12 games but can only play on 10 days: U15 games fit only on "
        "Saturdays at North Arena (the only time slots 75 minutes or longer), 1 game a day. "
        "That leaves about 12 games that can't be scheduled."
    )


@pytest.mark.parametrize("name", ["small_8", "league_40", "nightmare"])
def test_capacity_check_is_quiet_when_everything_fits(name: str) -> None:
    assert capacity_check(fixtures.ALL[name]()) == []


def test_games_too_long_for_any_slot() -> None:
    lg = fixtures.small_8()
    lg.rules = lg.rules.model_copy(update={"game_minutes": 120})
    [f] = capacity_check(lg)
    assert f.message == (
        "28 U10 games can't be scheduled: they need 120 minutes, but the longest time slot "
        "is 60 minutes."
    )


def test_no_slot_in_the_allowed_hours() -> None:
    lg = fixtures.small_8()
    lg.divisions[0].rules = RuleOverrides(earliest_start=time(16), latest_end=time(20))
    [f] = capacity_check(lg)
    assert "must be played between 4:00 PM and 8:00 PM" in f.message


def test_everything_blacked_out() -> None:
    lg = fixtures.small_8()
    lg.blackouts.append(
        Blackout(
            id="b-all",
            scope=BlackoutScope.DIVISION,
            target_id="d-u10",
            start_date=lg.season_start,
            end_date=lg.season_end,
        )
    )
    [f] = capacity_check(lg)
    assert "falls on a blackout date" in f.message


def test_explain_when_everything_fits() -> None:
    lg = fixtures.small_8()
    r = solve(lg, options=QUICK)
    assert explain(lg, r).summary == "Every game fits."


@pytest.mark.slow
def test_explain_suggests_verified_fixes() -> None:
    lg = short_u15()
    r = solve(lg, options=SolveOptions(time_limit_s=40, workers=4))
    ex = explain(lg, r, max_tries=4)
    assert ex.summary.startswith(f"{len(r.unplaced)} games didn't fit ({len(r.unplaced)} U15).")
    assert ex.findings[0].message.startswith("Each U15 team needs 12 games")
    assert ex.suggestions, "expected at least one fix"
    texts = [s.message for s in ex.suggestions]
    assert any(t.startswith("Allowing U15 teams two games on the same day") for t in texts)
    assert any(t.startswith("Adding one more 75-minute slot at") for t in texts)
    assert all(no_ids(t) for t in texts + [f.message for f in ex.findings])

    # The numbers are real: applying the best suggestion and placing the missing games
    # (everything else kept where it is) fits at least as many as promised.
    best = ex.suggestions[0]
    again = reschedule(
        best.league, r.events, Scope(division_ids=frozenset()), also_place=r.unplaced, options=QUICK
    )
    assert validate(best.league, again.events) == []
    assert len(r.unplaced) - len(again.unplaced) >= best.fixes

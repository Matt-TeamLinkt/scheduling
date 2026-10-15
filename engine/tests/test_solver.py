"""The solver must never produce a schedule that breaks a hard rule. `validate` is the
independent judge; every test here ends with it."""

from __future__ import annotations

import random
from collections import Counter
from datetime import time, timedelta

import pytest

from scheduling_engine import (
    Blackout,
    BlackoutScope,
    Coach,
    Family,
    League,
    RuleOverrides,
    fixtures,
    validate,
)
from scheduling_engine.goals import Goal
from scheduling_engine.solver import Phase, Progress, SolveOptions, Status, solve

FAST = SolveOptions(time_limit_s=20, workers=4)


def test_small_league_is_complete_and_legal() -> None:
    lg = fixtures.small_8()
    r = solve(lg, options=FAST)
    assert r.status == Status.BEST
    assert len(r.events) == 28 and r.unplaced == []
    assert validate(lg, r.events) == []
    played = Counter(t for e in r.events for t in e.team_ids)
    assert set(played.values()) == {7}


def _tightened(seed: int) -> League:
    """small_8 with random extra rules piled on: shared coaches, blackouts, rest,
    narrower windows, half-field games, two games a day."""
    rng = random.Random(seed)
    lg = fixtures.small_8()
    teams = [t.id for t in lg.teams]
    a, b, c = rng.sample(teams, 3)
    lg.coaches.append(Coach(id="c-extra", name="Extra Coach", team_ids=[a, b, c]))
    for i in range(rng.randint(1, 4)):
        day = lg.season_start + timedelta(days=7 * rng.randint(0, 8))
        lg.blackouts.append(
            Blackout(id=f"b-x{i}", scope=BlackoutScope.TEAM, target_id=rng.choice(teams),
                     start_date=day, end_date=day)
        )  # fmt: skip
    lg.divisions[0].rules = RuleOverrides(
        units=rng.choice([None, 1]),
        max_games_per_day=rng.choice([1, 2]),
        min_rest_minutes=rng.choice([0, 60, 120]),
        latest_end=rng.choice([time(13), time(15), time(18)]),
    )
    lg.families.append(Family(id="f-x", name="X", team_ids=rng.sample(teams, 2)))
    return lg


@pytest.mark.parametrize("seed", range(8))
def test_random_tight_leagues_never_break_a_rule(seed: int) -> None:
    lg = _tightened(seed)
    r = solve(lg, options=SolveOptions(time_limit_s=10, workers=4, seed=seed))
    assert r.status != Status.NO_SCHEDULE
    assert validate(lg, r.events) == []
    assert len(r.events) + len(r.unplaced) == 28


def test_half_field_games_share_a_field() -> None:
    lg = fixtures.small_8()
    lg.divisions[0].rules = RuleOverrides(units=1, max_games_per_day=1)
    # Only one field and one hour each Saturday: 4 games need 2 hours of full field,
    # or 1 hour if two games share the field at a time.
    lg.slots = [s for s in lg.slots if s.surface_id == "s-maple-1" and s.start.hour in (9, 10)]
    lg.coaches = []
    r = solve(lg, options=FAST)
    assert validate(lg, r.events) == []
    assert r.unplaced == []
    per_slot = Counter(e.slot_id for e in r.events)
    assert max(per_slot.values()) == 2


def test_progress_is_reported() -> None:
    seen: list[Progress] = []
    lg = fixtures.small_8()
    solve(lg, options=SolveOptions(time_limit_s=10, workers=4, on_progress=seen.append))
    assert seen and seen[0].phase == Phase.PLACING
    assert any(p.placed == p.total == 28 for p in seen)


def test_ranking_changes_the_outcome() -> None:
    """With venues that have no map location, 'keep travel short' means playing home
    games at the home venue. Ranking it first should do much better than turning it off."""
    lg = fixtures.small_8()
    first = solve(lg, options=SolveOptions(time_limit_s=10, workers=4,
                                           priorities=[Goal.TRAVEL, Goal.SPACING]))  # fmt: skip
    off = solve(lg, options=SolveOptions(time_limit_s=10, workers=4,
                                         priorities=[Goal.SPACING]))  # fmt: skip

    def away_from_home(events: list) -> int:  # type: ignore[type-arg]
        home_venue = {t.id: t.home_venue_id for t in lg.teams}
        surface_venue = {s.id: s.venue_id for s in lg.surfaces}
        slot_surface = {s.id: s.surface_id for s in lg.slots}
        return sum(
            surface_venue[slot_surface[e.slot_id]] != home_venue[e.home_team_id] for e in events
        )

    assert away_from_home(first.events) == 0
    assert away_from_home(first.events) < away_from_home(off.events)
    assert validate(lg, first.events) == [] and validate(lg, off.events) == []


def test_families_goal_avoids_sibling_clashes() -> None:
    lg = fixtures.small_8()
    lg.families = [Family(id="f", name="Busy", team_ids=["t-01", "t-02"])]
    r = solve(lg, options=SolveOptions(time_limit_s=10, workers=4,
                                       priorities=[Goal.FAMILIES]))  # fmt: skip
    assert r.goal_scores[Goal.FAMILIES] == 0
    busy = [e for e in r.events if {"t-01", "t-02"} & set(e.team_ids)]
    for x in busy:
        for y in busy:
            if x.id < y.id and set(x.team_ids) != set(y.team_ids):
                overlap = x.start < y.end + timedelta(minutes=30) and y.start < x.end + timedelta(
                    minutes=30
                )
                assert (
                    not overlap
                    or {"t-01", "t-02"} <= set(x.team_ids) | set(y.team_ids)
                    and (x.start.date() != y.start.date())
                )


# ── the realistic leagues (slow: about a minute each) ──────────────────────


@pytest.mark.slow
@pytest.mark.parametrize("name", ["league_40", "nightmare"])
def test_forty_team_leagues_fully_scheduled_in_a_minute(name: str) -> None:
    lg = fixtures.ALL[name]()
    r = solve(lg, options=SolveOptions(time_limit_s=60, workers=4))
    assert validate(lg, r.events) == []
    assert r.unplaced == [], f"{len(r.unplaced)} games didn't fit"
    assert r.seconds < 75


@pytest.mark.slow
def test_impossible_league_still_gets_its_best_schedule() -> None:
    """Without Sunday 75-minute ice, U15 has only 10 usable Saturdays for 12 games each:
    exactly 12 games can't fit. The rest must still be scheduled, legally."""
    lg = fixtures.league_40()
    lg.slots = [s for s in lg.slots if not (s.surface_id == "s-north-1" and s.date.weekday() == 6)]
    r = solve(lg, options=SolveOptions(time_limit_s=40, workers=4))
    assert validate(lg, r.events) == []
    assert r.stats["most_possible"] == 228  # the solver knows 12 games can't fit
    assert 12 <= len(r.unplaced) <= 14  # and gets within a game or two of that
    assert {m.division_id for m in r.unplaced} == {"d-u15"}

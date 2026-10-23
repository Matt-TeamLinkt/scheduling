"""Coach restrictions end to end: times a coach can't make are never scheduled, and the
times they prefer are honoured when the schedule has room."""

from __future__ import annotations

from datetime import time

from scheduling_engine import League, TimeOff, fixtures, validate
from scheduling_engine.goals import Goal
from scheduling_engine.report import fairness_report
from scheduling_engine.solver import SolveOptions, solve

QUICK = SolveOptions(time_limit_s=10, workers=4)


def with_coach(lg: League, team: str, **changes: list[TimeOff]) -> League:
    coaches = [c.model_copy(update=changes) if team in c.team_ids else c for c in lg.coaches]
    return lg.model_copy(update={"coaches": coaches})


def test_solver_never_uses_a_coachs_unavailable_time() -> None:
    lg = fixtures.small_8()
    team = lg.teams[0].id
    first = min(s.date for s in lg.slots)
    off = [TimeOff(weekday=5, start=time(9, 0), end=time(12, 0)), TimeOff(day=first)]
    lg = with_coach(lg, team, unavailable=off)
    r = solve(lg, options=QUICK)
    assert validate(lg, r.events) == [] and r.unplaced == []
    mine = [e for e in r.events if team in e.team_ids]
    assert mine and all(e.start.time() >= time(12, 0) for e in mine)
    assert all(e.start.date() != first for e in mine)


def test_preferred_times_are_honoured_when_there_is_room() -> None:
    lg = fixtures.small_8()
    team = lg.teams[0].id
    lg = with_coach(lg, team, prefers=[TimeOff(weekday=5, start=time(13, 0), end=time(16, 0))])
    r = solve(lg, options=SolveOptions(time_limit_s=10, workers=4, priorities=[Goal.COACH_TIMES]))
    mine = [e for e in r.events if team in e.team_ids]
    assert mine and all(e.start.time() >= time(13, 0) for e in mine)
    assert fairness_report(lg, r.events).metrics["coach_pref_misses"] == 0


def test_report_flags_games_outside_preferred_times() -> None:
    lg = fixtures.small_8()
    team = lg.teams[0].id
    r = solve(lg, options=QUICK)
    lg = with_coach(lg, team, prefers=[TimeOff(weekday=0)])  # Mondays: never happens here
    rep = fairness_report(lg, r.events)
    coach = next(c for c in lg.coaches if team in c.team_ids)
    games = sum(1 for e in r.events if set(e.team_ids) & set(coach.team_ids))
    assert rep.metrics["coach_pref_misses"] >= games
    want = f"{coach.name} would rather coach Mondays; {games} of their {games} games"
    assert any(f.message.startswith(want) for f in rep.flags)

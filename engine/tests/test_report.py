from __future__ import annotations

from datetime import date

from conftest import game

from scheduling_engine import Family, League, fixtures
from scheduling_engine.report import fairness_report
from scheduling_engine.solver import SolveOptions, solve

SAT = date(2027, 1, 9)
SUN = date(2027, 1, 10)
SAT2 = date(2027, 1, 16)


def test_report_on_a_solved_league() -> None:
    lg = fixtures.small_8()
    r = solve(lg, options=SolveOptions(time_limit_s=10, workers=4))
    rep = fairness_report(lg, r.events)
    assert len(rep.teams) == 8
    for t in rep.teams:
        assert t.games == t.target == 7
        assert abs(t.home - t.away) <= 1
    assert rep.metrics["short_of_target"] == 0
    assert rep.metrics["family_clashes"] == 0


def test_flags_are_plain_language(hockey: League) -> None:
    evs = [
        game(hockey, "t-u13-01", "t-u13-02", "s-north-1", SAT, "07:00"),
        game(hockey, "t-u13-01", "t-u13-02", "s-river", SUN, "08:00"),  # rematch next day
        game(hockey, "t-u13-03", "t-u13-01", "s-north-1", SAT2, "07:00"),
    ]
    rep = fairness_report(hockey, evs)
    line = next(t for t in rep.teams if t.team_id == "t-u13-01")
    assert (line.games, line.home, line.away) == (3, 2, 1)
    assert line.back_to_back_days == 1
    assert line.quickest_rematch_days == 1
    assert line.early == 2  # 7:00 AM starts (before 8:00 AM)
    msgs = [f.message for f in rep.flags]
    assert "North Stars U13 Blue play the same opponent twice within 1 days." in msgs
    assert "North Stars U13 Blue play 3 games; the target is 12." in msgs


def test_family_clash_is_reported(hockey: League) -> None:
    hockey.families = [Family(id="f", name="Patel", team_ids=["t-u9-01", "t-u13-05"])]
    evs = [
        game(hockey, "t-u9-01", "t-u9-02", "s-north-1", SAT, "07:00"),
        game(hockey, "t-u13-05", "t-u13-06", "s-north-2", SAT, "07:00"),
    ]
    rep = fairness_report(hockey, evs)
    assert len(rep.family_clashes) == 1
    msg = rep.family_clashes[0]
    assert msg.startswith("The Patel family has kids on")
    assert "North Stars U9 Blue" in msg and "Lakeshore Lynx U13 Blue" in msg


def test_travel_measured_from_home_venue(hockey: League) -> None:
    # t-u13-01 (North Arena) plays away at Eastside: about 18 km each way.
    evs = [game(hockey, "t-u13-03", "t-u13-01", "s-east", SAT, "14:00")]
    rep = fairness_report(hockey, evs)
    line = next(t for t in rep.teams if t.team_id == "t-u13-01")
    assert 15 < line.travel_km < 25

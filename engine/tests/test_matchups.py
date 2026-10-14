from __future__ import annotations

from collections import Counter

import pytest

from scheduling_engine import Division, League, RuleOverrides, Team, fixtures
from scheduling_engine.matchups import circle_rounds, make_matchups


def league_with(n: int, games: int) -> League:
    lg = fixtures.small_8()
    lg.rules = lg.rules.model_copy(update={"games_per_team": games})
    lg.teams = [Team(id=f"t{i:02d}", name=f"Team {i}", division_id="d-u10") for i in range(n)]
    return lg


def test_circle_method_is_a_round_robin() -> None:
    teams = [f"t{i}" for i in range(8)]
    rounds = circle_rounds(teams)
    assert len(rounds) == 7
    pairs = [frozenset(p) for r in rounds for p in r]
    assert len(pairs) == len(set(pairs)) == 28
    for r in rounds:  # nobody twice in a round
        assert len({t for p in r for t in p}) == 8


@pytest.mark.parametrize(
    ("n", "games"), [(8, 7), (8, 14), (8, 12), (10, 12), (12, 12), (7, 6), (9, 7), (5, 10), (2, 4)]
)
def test_everyone_gets_their_games_and_balanced_home_away(n: int, games: int) -> None:
    ms, notes = make_matchups(league_with(n, games))
    count = Counter(t for m in ms for t in m.team_ids)
    if n * games % 2 == 0:
        assert set(count.values()) == {games} and notes == []
    else:
        assert sorted(set(count.values())) == [games - 1, games]
        assert sum(1 for c in count.values() if c == games - 1) == 1
        assert "can't be split evenly" in notes[0].message
    home = Counter(m.home_team_id for m in ms)
    for t, c in count.items():
        assert abs(2 * home[t] - c) <= 1, f"{t}: {home[t]} home of {c}"


@pytest.mark.parametrize(("n", "games"), [(8, 12), (10, 12), (12, 12), (9, 7)])
def test_opponents_are_spread_evenly(n: int, games: int) -> None:
    ms, _ = make_matchups(league_with(n, games))
    meets = Counter(frozenset(m.team_ids) for m in ms)
    assert max(meets.values()) - min(meets.values()) <= 1


def test_fixture_leagues() -> None:
    for build in fixtures.ALL.values():
        lg = build()
        ms, _ = make_matchups(lg)
        expected = sum(
            sum(t.division_id == d.id for t in lg.teams)
            * (d.rules.games_per_team or lg.rules.games_per_team)
            // 2
            for d in lg.divisions
        )
        assert len(ms) == expected
        assert all(m.home_team_id != m.away_team_id for m in ms)
        assert len({m.id for m in ms}) == len(ms)


def test_only_requested_divisions() -> None:
    lg = fixtures.league_40()
    ms, _ = make_matchups(lg, ["d-u9"])
    assert {m.division_id for m in ms} == {"d-u9"} and len(ms) == 48


def test_division_override_of_games_per_team() -> None:
    lg = fixtures.league_40()
    lg.divisions[0].rules = lg.divisions[0].rules.model_copy(update={"games_per_team": 6})
    ms, _ = make_matchups(lg, ["d-u9"])
    assert len(ms) == 8 * 6 // 2


def test_single_team_division_has_no_games() -> None:
    lg = fixtures.small_8()
    lg.divisions.append(Division(id="d-solo", name="Solo", rules=RuleOverrides()))
    lg.teams.append(Team(id="t-solo", name="Solo", division_id="d-solo"))
    ms, _ = make_matchups(lg, ["d-solo"])
    assert ms == []

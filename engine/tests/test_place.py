"""Placing one game by hand: every offered spot is legal, the best are marked, and when
nothing legal is left the near misses say which rule they break."""

from __future__ import annotations

import pytest

from scheduling_engine import Event, League, fixtures, validate
from scheduling_engine.matchups import Matchup, make_matchups
from scheduling_engine.place import SUGGESTED, event_for, open_spots
from scheduling_engine.solver import SolveOptions, solve


@pytest.fixture(scope="module")
def season() -> tuple[League, list[Event]]:
    lg = fixtures.small_8()
    return lg, solve(lg, options=SolveOptions(time_limit_s=10, workers=4)).events


def as_matchup(e: Event) -> Matchup:
    assert e.away_team_id is not None
    return Matchup(e.id, e.division_id, e.home_team_id, e.away_team_id, 0)


def test_every_offered_spot_is_legal(season: tuple[League, list[Event]]) -> None:
    lg, events = season
    taken = events[len(events) // 2]
    rest = [e for e in events if e.id != taken.id]
    spots = open_spots(lg, rest, as_matchup(taken))
    assert spots, "the game's own spot is free again, so there's at least one"
    for c in spots:
        assert c.problems == []
        assert validate(lg, [*rest, event_for(lg, as_matchup(taken), c.slot_id, c.start)]) == []
    assert any(c.slot_id == taken.slot_id and c.start == taken.start for c in spots)


def test_best_spots_are_marked_and_first(season: tuple[League, list[Event]]) -> None:
    lg, events = season
    taken = events[3]
    spots = open_spots(lg, [e for e in events if e.id != taken.id], as_matchup(taken))
    marked = [c for c in spots if c.suggested]
    assert len(marked) == min(SUGGESTED, len(spots))
    assert spots[: len(marked)] == marked
    assert [c.score for c in spots] == sorted(c.score for c in spots)


def test_reasons_are_plain_language(season: tuple[League, list[Event]]) -> None:
    lg, events = season
    taken = events[0]
    for c in open_spots(lg, [e for e in events if e.id != taken.id], as_matchup(taken)):
        for line in c.good + c.watch:
            assert line.endswith(".")
            assert "t-" not in line and "sl-" not in line  # names, never ids


def test_matchups_only_season_offers_spots() -> None:
    lg = fixtures.small_8()
    matchups, _ = make_matchups(lg)
    spots = open_spots(lg, [], matchups[0])
    assert spots and all(c.problems == [] for c in spots)
    assert "Neither team has another game yet." in spots[0].good


def test_spots_that_break_a_rule_say_why(season: tuple[League, list[Event]]) -> None:
    lg, events = season
    # A rematch of a game that's already on the schedule: its own spot is taken by it.
    taken = events[0]
    m = Matchup("rematch", taken.division_id, taken.home_team_id, taken.away_team_id or "", 9)
    legal = open_spots(lg, events, m)
    assert not any(c.slot_id == taken.slot_id and c.start == taken.start for c in legal)
    every = open_spots(lg, events, m, with_problems=True)
    same = [c for c in every if c.slot_id == taken.slot_id and c.start == taken.start]
    assert len(same) == 1 and same[0].problems and not same[0].suggested
    assert all(p.endswith(".") for p in same[0].problems)
    first_bad = next(i for i, c in enumerate(every) if c.problems)
    assert all(c.problems for c in every[first_bad:]), "legal spots come first"

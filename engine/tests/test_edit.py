"""Hand edits to the setup keep the schedule consistent: no game ever points at a team,
division or time slot that was deleted."""

from __future__ import annotations

import pytest

from scheduling_engine import Event, League, fixtures, validate
from scheduling_engine.edit import fit_to_setup
from scheduling_engine.solver import SolveOptions, solve


@pytest.fixture(scope="module")
def season() -> tuple[League, list[Event]]:
    lg = fixtures.small_8()
    return lg, solve(lg, options=SolveOptions(time_limit_s=10, workers=4)).events


def test_nothing_changes_when_nothing_was_removed(season: tuple[League, list[Event]]) -> None:
    lg, events = season
    kept, waiting, notes = fit_to_setup(lg, events, [])
    assert kept == events and waiting == [] and notes == []


def test_deleting_a_team_cancels_its_games(season: tuple[League, list[Event]]) -> None:
    lg, events = season
    gone = lg.teams[0].id
    lg2 = lg.model_copy(update={"teams": lg.teams[1:]})
    kept, waiting, notes = fit_to_setup(lg2, events, [])
    lost = [e for e in events if gone in e.team_ids]
    assert len(kept) == len(events) - len(lost) and waiting == []
    assert validate(lg2, kept) == []
    assert notes == [f"{len(lost)} games were removed with the teams."]


def test_deleting_time_sends_games_to_needs_a_spot(season: tuple[League, list[Event]]) -> None:
    lg, events = season
    day = events[0].start.date()
    lg2 = lg.model_copy(update={"slots": [s for s in lg.slots if s.date != day]})
    kept, waiting, notes = fit_to_setup(lg2, events, [])
    moved = [e for e in events if e.start.date() == day]
    assert {m.id for m in waiting} == {e.id for e in moved}
    assert {(m.home_team_id, m.away_team_id) for m in waiting} == {
        (e.home_team_id, e.away_team_id) for e in moved
    }
    assert validate(lg2, kept) == []
    assert "Needs a spot" in notes[0]

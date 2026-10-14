"""Fixtures stay in sync with their generator, and look like what they claim to be."""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from pathlib import Path

import pytest

from scheduling_engine import Event, League, fixtures, validate
from scheduling_engine.index import LeagueIndex

SNAPSHOTS = Path(__file__).resolve().parents[2] / "fixtures"


@pytest.mark.parametrize("name", sorted(fixtures.ALL))
def test_snapshot_matches_generator(name: str) -> None:
    on_disk = League.model_validate_json((SNAPSHOTS / f"{name}.json").read_text())
    assert on_disk == fixtures.ALL[name](), (
        "Snapshot is stale. Run: uv run python -m scheduling_engine.fixtures ../fixtures"
    )


def test_shapes() -> None:
    small, l40, nm = fixtures.small_8(), fixtures.league_40(), fixtures.nightmare()
    assert len(small.teams) == 8 and len(small.divisions) == 1
    assert len(l40.teams) == 40 and len(l40.divisions) == 4
    assert len(nm.teams) == 40
    # nightmare: many shared coaches, one coach on three teams, lots of siblings
    assert sum(len(c.team_ids) > 1 for c in nm.coaches) == 15
    assert max(len(c.team_ids) for c in nm.coaches) == 3
    assert len(nm.families) == 60
    assert len(nm.slots) < len(l40.slots)


def test_reference_round_robin_is_legal() -> None:
    """A hand-built single round robin for small_8 (circle method, one game per hour
    on Field 1 so a shared coach is never double-booked, skipping the long weekend)
    must pass every check."""
    lg = fixtures.small_8()
    ix = LeagueIndex(lg)
    teams = [t.id for t in lg.teams]
    saturdays: list[date] = []
    day = lg.season_start
    while len(saturdays) < 7:
        if not any(b.start_date <= day <= b.end_date for b in lg.blackouts):
            saturdays.append(day)
        day += timedelta(days=7)

    slots = {(s.surface_id, s.date, s.start.hour): s for s in lg.slots}
    events: list[Event] = []
    rotating = teams[1:]
    for rnd, sat in enumerate(saturdays):
        order = [teams[0], *rotating]
        pairs = [(order[i], order[-1 - i]) for i in range(4)]
        for g, (a, b) in enumerate(pairs):
            home, away = (a, b) if rnd % 2 == 0 else (b, a)
            surface = "s-maple-1"
            slot = slots[(surface, sat, 9 + g)]
            events.append(
                Event(
                    id=f"r{rnd}g{g}",
                    division_id="d-u10",
                    home_team_id=home,
                    away_team_id=away,
                    slot_id=slot.id,
                    start=slot.start_dt,
                    minutes=60,
                    units=ix.surfaces[surface].units,
                )
            )
        rotating = rotating[-1:] + rotating[:-1]

    assert validate(lg, events) == []
    played = Counter(t for e in events for t in e.team_ids)
    assert set(played.values()) == {7}
    assert len({frozenset(e.team_ids) for e in events}) == 28  # everyone met once
    assert all(e.start.date() != date(2027, 5, 29) for e in events)

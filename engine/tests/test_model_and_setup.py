from __future__ import annotations

from datetime import date, datetime, time

import pytest

from scheduling_engine import (
    SPORT_PRESETS,
    Division,
    Event,
    League,
    RuleOverrides,
    Rules,
    Severity,
    Slot,
    Sport,
    Team,
    check_setup,
)
from scheduling_engine.index import LeagueIndex

# ── model ──────────────────────────────────────────────────────────────────


def test_every_sport_has_a_preset() -> None:
    assert set(SPORT_PRESETS) == set(Sport)


def test_defaults_need_no_configuration() -> None:
    lg = League(
        id="x", name="New league", season_start=date(2027, 1, 1), season_end=date(2027, 3, 1)
    )
    assert lg.rules.games_per_team == 10
    assert lg.rules.max_games_per_day == 1


def test_overrides_layer_league_then_division_then_team(hockey: League) -> None:
    team = next(t for t in hockey.teams if t.id == "t-u9-01")
    team.rules = RuleOverrides(latest_end=time(18, 30))
    r = LeagueIndex(hockey).team_rules("t-u9-01")
    assert r.games_per_team == 12  # league
    assert r.game_minutes == 50 and r.units == 1  # division
    assert r.latest_end == time(18, 30)  # team
    assert r.earliest_start == time(7)  # league


def test_override_combination_is_revalidated() -> None:
    with pytest.raises(ValueError):
        RuleOverrides(earliest_start=time(22)).apply_to(Rules())


def test_slot_must_end_after_it_starts() -> None:
    with pytest.raises(ValueError):
        Slot(id="s", surface_id="x", date=date(2027, 1, 1), start=time(9), end=time(9))


def test_a_team_cant_play_itself() -> None:
    with pytest.raises(ValueError):
        Event(
            id="e",
            division_id="d",
            home_team_id="t",
            away_team_id="t",
            slot_id="s",
            start=datetime(2027, 1, 1, 9),
            minutes=60,
        )


def test_a_game_needs_two_teams() -> None:
    with pytest.raises(ValueError):
        Event(
            id="e",
            division_id="d",
            home_team_id="t",
            slot_id="s",
            start=datetime(2027, 1, 1, 9),
            minutes=60,
        )


def test_league_round_trips_through_json(hockey: League) -> None:
    assert League.model_validate_json(hockey.model_dump_json()) == hockey


# ── setup checks ───────────────────────────────────────────────────────────


@pytest.mark.parametrize("name", ["small", "hockey", "nightmare"])
def test_fixtures_have_no_setup_errors(name: str, request: pytest.FixtureRequest) -> None:
    lg: League = request.getfixturevalue(name)
    assert [p for p in check_setup(lg) if p.severity == Severity.ERROR] == []


def test_overlapping_slots_are_flagged(hockey: League) -> None:
    hockey.slots.append(
        Slot(
            id="sl-x",
            surface_id="s-north-1",
            date=date(2027, 1, 9),
            start=time(7, 30),
            end=time(8, 30),
        )
    )
    msgs = [p.message for p in check_setup(hockey)]
    assert any("overlap on North Arena Rink 1" in m for m in msgs)


def test_tiny_division_is_flagged(hockey: League) -> None:
    hockey.divisions.append(Division(id="d-u18", name="U18"))
    hockey.teams.append(Team(id="t-solo", name="Solo", division_id="d-u18"))
    probs = check_setup(hockey)
    assert any(p.message == "U18 has 1 team, so it can't play games." for p in probs)


def test_dangling_references_are_errors(hockey: League) -> None:
    hockey.teams.append(Team(id="t-lost", name="Lost Team", division_id="d-nope"))
    hockey.coaches[0].team_ids.append("t-ghost")
    errors = [p for p in check_setup(hockey) if p.severity == Severity.ERROR]
    assert len(errors) == 2


def test_duplicate_ids_are_errors(hockey: League) -> None:
    hockey.teams.append(hockey.teams[0].model_copy())
    errors = [p for p in check_setup(hockey) if p.severity == Severity.ERROR]
    assert any("share the id" in p.message for p in errors)


def test_conflicting_overrides_are_errors_not_crashes(hockey: League) -> None:
    hockey.teams[0].rules = RuleOverrides(earliest_start=time(20))  # U9 ends by 19:00
    errors = [p for p in check_setup(hockey) if p.severity == Severity.ERROR]
    assert len(errors) == 1 and "don't fit together" in errors[0].message


def test_slots_outside_season_are_flagged(hockey: League) -> None:
    hockey.slots.append(
        Slot(id="sl-x", surface_id="s-east", date=date(2027, 6, 1), start=time(9), end=time(10))
    )
    assert any("outside the season" in p.message for p in check_setup(hockey))

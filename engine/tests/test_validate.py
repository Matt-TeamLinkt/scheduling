"""One section per hard constraint. Each proves a violation is caught and that the
nearest legal case is not flagged (no false alarms for the scheduler)."""

from __future__ import annotations

import random
import re
import time as clock
from datetime import date, time

import pytest
from conftest import game

from scheduling_engine import (
    Blackout,
    BlackoutScope,
    Code,
    Event,
    League,
    RuleOverrides,
    Slot,
    validate,
)

SAT = date(2027, 1, 9)  # North rinks 07:00–13:15 (75-min slots); Eastside 14:00–18:00
SUN = date(2027, 1, 10)  # Riverside 08:00–14:00
TUE = date(2027, 1, 5)  # Riverside 17:00–21:00
WED = date(2027, 1, 6)  # Eastside 18:00–21:00


def codes(lg: League, events: list[Event]) -> set[Code]:
    return {v.code for v in validate(lg, events)}


# ── H1: a team can't be in two places at once ──────────────────────────────


def test_h1_team_in_two_games_at_once(hockey: League) -> None:
    a = game(hockey, "t-u13-01", "t-u13-02", "s-north-1", SAT, "07:00")
    b = game(hockey, "t-u13-01", "t-u13-03", "s-north-2", SAT, "07:00")
    vs = [v for v in validate(hockey, [a, b]) if v.code == Code.TEAM_DOUBLE_BOOKED]
    assert len(vs) == 1
    assert vs[0].team_ids == ("t-u13-01",)
    assert "North Stars U13 Blue" in vs[0].message


def test_h1_caught_even_without_a_coach(hockey: League) -> None:
    # The prototype only caught this through a shared coach (audit B1).
    hockey.coaches = []
    a = game(hockey, "t-u13-01", "t-u13-02", "s-north-1", SAT, "07:00")
    b = game(hockey, "t-u13-01", "t-u13-03", "s-north-2", SAT, "07:00")
    assert Code.TEAM_DOUBLE_BOOKED in codes(hockey, [a, b])


def test_h1_partial_overlap(hockey: League) -> None:
    a = game(hockey, "t-u13-01", "t-u13-02", "s-north-1", SAT, "07:00")  # 7:00–8:00
    b = game(hockey, "t-u13-01", "t-u13-03", "s-north-2", SAT, "07:00", offset=15)  # 7:15–8:15
    assert Code.TEAM_DOUBLE_BOOKED in codes(hockey, [a, b])


def test_h1_back_to_back_is_not_a_double_booking(hockey: League) -> None:
    a = game(hockey, "t-u13-01", "t-u13-02", "s-river", TUE, "17:00")  # ends 18:00
    b = game(hockey, "t-u13-01", "t-u13-03", "s-river", TUE, "18:00")  # starts 18:00
    assert Code.TEAM_DOUBLE_BOOKED not in codes(hockey, [a, b])


def test_h1_practice_counts(hockey: League) -> None:
    a = game(hockey, "t-u13-01", "t-u13-02", "s-north-1", SAT, "07:00")
    p = game(hockey, "t-u13-01", None, "s-north-2", SAT, "07:00")
    assert Code.TEAM_DOUBLE_BOOKED in codes(hockey, [a, p])


def test_h1_reported_once_not_also_as_coach_conflict(hockey: League) -> None:
    a = game(hockey, "t-u13-01", "t-u13-02", "s-north-1", SAT, "07:00")
    b = game(hockey, "t-u13-01", "t-u13-03", "s-north-2", SAT, "07:00")
    assert Code.COACH_DOUBLE_BOOKED not in codes(hockey, [a, b])


# ── H2: a surface only holds what it's sized for ───────────────────────────


def test_h2_two_full_ice_games_on_one_rink(hockey: League) -> None:
    a = game(hockey, "t-u13-01", "t-u13-02", "s-north-1", SAT, "07:00")
    b = game(hockey, "t-u13-03", "t-u13-04", "s-north-1", SAT, "07:00")
    vs = [v for v in validate(hockey, [a, b]) if v.code == Code.SURFACE_OVERBOOKED]
    assert len(vs) == 1
    assert set(vs[0].event_ids) == {a.id, b.id}


def test_h2_two_half_ice_games_share_a_rink(hockey: League) -> None:
    a = game(hockey, "t-u9-01", "t-u9-02", "s-north-1", SAT, "07:00")
    b = game(hockey, "t-u9-03", "t-u9-04", "s-north-1", SAT, "07:00")
    assert a.units == b.units == 1
    assert codes(hockey, [a, b]) == set()


def test_h2_three_half_ice_games_dont_fit(hockey: League) -> None:
    evs = [
        game(hockey, "t-u9-01", "t-u9-02", "s-north-1", SAT, "07:00"),
        game(hockey, "t-u9-03", "t-u9-04", "s-north-1", SAT, "07:00"),
        game(hockey, "t-u9-05", "t-u9-06", "s-north-1", SAT, "07:00"),
    ]
    assert Code.SURFACE_OVERBOOKED in codes(hockey, evs)


def test_h2_half_ice_plus_full_ice_dont_fit(hockey: League) -> None:
    a = game(hockey, "t-u9-01", "t-u9-02", "s-north-1", SAT, "07:00")
    b = game(hockey, "t-u13-01", "t-u13-02", "s-north-1", SAT, "07:00")
    assert Code.SURFACE_OVERBOOKED in codes(hockey, [a, b])


def test_h2_overlapping_slots_cant_double_book_a_rink(hockey: League) -> None:
    # Regression for audit B6: two slots overlap on the same rink.
    hockey.slots.append(
        Slot(id="sl-extra", surface_id="s-north-1", date=SAT, start=time(7, 30), end=time(8, 30))
    )
    a = game(hockey, "t-u13-01", "t-u13-02", "s-north-1", SAT, "07:00")
    b = game(hockey, "t-u13-03", "t-u13-04", "s-north-1", SAT, "07:30")
    assert Code.SURFACE_OVERBOOKED in codes(hockey, [a, b])


def test_h2_game_bigger_than_surface(hockey: League) -> None:
    a = game(hockey, "t-u13-01", "t-u13-02", "s-north-1", SAT, "07:00", units=3)
    assert Code.TOO_BIG_FOR_SURFACE in codes(hockey, [a])


# ── H3: blackouts at every scope ───────────────────────────────────────────


def test_h3_league_blackout(hockey: League) -> None:
    family_day = date(2027, 2, 13)
    a = game(hockey, "t-u13-01", "t-u13-02", "s-north-1", family_day, "07:00")
    vs = [v for v in validate(hockey, [a]) if v.code == Code.BLACKOUT]
    assert len(vs) == 1 and "Family Day weekend" in vs[0].message


def test_h3_division_blackout(hockey: League) -> None:
    showcase = date(2027, 3, 20)
    u15 = game(hockey, "t-u15-01", "t-u15-02", "s-north-1", showcase, "07:00")
    u13 = game(hockey, "t-u13-01", "t-u13-02", "s-north-2", showcase, "07:00")
    vs = validate(hockey, [u15, u13])
    assert [v.event_ids for v in vs if v.code == Code.BLACKOUT] == [(u15.id,)]


def test_h3_team_blackout_only_hits_that_team(hockey: League) -> None:
    tournament = date(2027, 1, 30)
    away = game(hockey, "t-u13-01", "t-u13-03", "s-north-1", tournament, "07:00")
    other = game(hockey, "t-u13-01", "t-u13-02", "s-north-2", tournament, "08:15")
    blackout = [v for v in validate(hockey, [away, other]) if v.code == Code.BLACKOUT]
    assert [v.event_ids for v in blackout] == [(away.id,)]


def test_h3_venue_blackout(hockey: League) -> None:
    closed = date(2027, 3, 6)
    a = game(hockey, "t-u13-01", "t-u13-02", "s-east", closed, "14:00")
    assert Code.BLACKOUT in codes(hockey, [a])


def test_h3_surface_blackout(nightmare: League) -> None:
    resurfacing = date(2027, 3, 13)
    rink2 = game(nightmare, "t-u13-01", "t-u13-04", "s-north-2", resurfacing, "07:00")
    rink1 = game(nightmare, "t-u13-05", "t-u13-07", "s-north-1", resurfacing, "07:00")
    vs = validate(nightmare, [rink2, rink1])
    assert [v.event_ids for v in vs if v.code == Code.BLACKOUT] == [(rink2.id,)]


def test_h3_part_day_blackout(hockey: League) -> None:
    photos = date(2027, 2, 20)  # t-u11-05 unavailable 07:00–12:00
    morning = game(hockey, "t-u11-05", "t-u11-01", "s-north-1", photos, "09:30")
    afternoon = game(hockey, "t-u11-05", "t-u11-02", "s-east", photos, "14:00")
    blackout = [v for v in validate(hockey, [morning, afternoon]) if v.code == Code.BLACKOUT]
    assert [v.event_ids for v in blackout] == [(morning.id,)]


# ── H4: only inside slots the league has, inside the season ────────────────


def test_h4_game_starting_before_its_slot(hockey: League) -> None:
    a = game(hockey, "t-u13-01", "t-u13-02", "s-river", TUE, "18:00", offset=-30)
    assert Code.OUTSIDE_SLOT in codes(hockey, [a])


def test_h4_game_running_past_its_slot(hockey: League) -> None:
    # A 75-minute U15 game doesn't fit Riverside's 60-minute slots.
    a = game(hockey, "t-u15-01", "t-u15-02", "s-river", TUE, "17:00")
    vs = [v for v in validate(hockey, [a]) if v.code == Code.OUTSIDE_SLOT]
    assert len(vs) == 1 and "5:00 PM to 6:15 PM" in vs[0].message


def test_h4_game_fits_inside_a_longer_slot(hockey: League) -> None:
    a = game(hockey, "t-u13-01", "t-u13-02", "s-north-1", SAT, "07:00", offset=15)
    assert codes(hockey, [a]) == set()


def test_h4_unknown_slot(hockey: League) -> None:
    a = game(hockey, "t-u13-01", "t-u13-02", "s-north-1", SAT, "07:00")
    a = a.model_copy(update={"slot_id": "sl-gone"})
    assert codes(hockey, [a]) == {Code.UNKNOWN_REFERENCE}


def test_h4_outside_season(hockey: League) -> None:
    before = date(2026, 12, 19)
    hockey.slots.append(
        Slot(id="sl-early", surface_id="s-north-1", date=before, start=time(7), end=time(8, 15))
    )
    a = game(hockey, "t-u13-01", "t-u13-02", "s-north-1", before, "07:00")
    assert Code.OUTSIDE_SEASON in codes(hockey, [a])


# ── H5: coaches can't be in two places at once ─────────────────────────────


def test_h5_shared_coach_overlap(hockey: League) -> None:
    # One coach runs t-u9-01 and t-u13-04.
    a = game(hockey, "t-u9-01", "t-u9-02", "s-north-1", SAT, "07:00")
    b = game(hockey, "t-u13-04", "t-u13-05", "s-north-2", SAT, "07:00")
    vs = [v for v in validate(hockey, [a, b]) if v.code == Code.COACH_DOUBLE_BOOKED]
    assert len(vs) == 1
    assert set(vs[0].team_ids) == {"t-u9-01", "t-u13-04"}


def test_h5_shared_coach_at_different_times(hockey: League) -> None:
    a = game(hockey, "t-u9-01", "t-u9-02", "s-north-1", SAT, "07:00")
    b = game(hockey, "t-u13-04", "t-u13-05", "s-north-2", SAT, "08:15")
    assert codes(hockey, [a, b]) == set()


def test_h5_coachs_two_teams_playing_each_other_is_fine(hockey: League) -> None:
    a = game(hockey, "t-u11-04", "t-u11-09", "s-north-1", SAT, "07:00")
    assert codes(hockey, [a]) == set()


def test_h5_three_team_coach(nightmare: League) -> None:
    a = game(nightmare, "t-u9-02", "t-u9-03", "s-north-1", SAT, "07:00")
    b = game(nightmare, "t-u15-02", "t-u15-03", "s-north-2", SAT, "07:00")
    assert Code.COACH_DOUBLE_BOOKED in codes(nightmare, [a, b])


# ── H6: rest and games per day ─────────────────────────────────────────────


def test_h6_min_rest_from_division_rules(nightmare: League) -> None:
    # U13 needs 18 hours between games.
    a = game(nightmare, "t-u13-01", "t-u13-02", "s-north-1", SAT, "12:00")  # ends 1:00 PM
    b = game(nightmare, "t-u13-01", "t-u13-03", "s-river", SUN, "08:00")  # 19h later: ok
    assert codes(nightmare, [a, b]) == set()
    c = game(nightmare, "t-u13-01", "t-u13-03", "s-north-2", SUN, "07:00")
    assert codes(nightmare, [a, c]) == set()  # exactly 18 hours: allowed
    d = game(nightmare, "t-u13-01", "t-u13-04", "s-north-1", SAT, "12:00", offset=15)
    vs = [v for v in validate(nightmare, [d, c]) if v.code == Code.NOT_ENOUGH_REST]
    assert len(vs) == 1 and "17 hours 45 min" in vs[0].message


def test_h6_team_override_beats_division(hockey: League) -> None:
    team = next(t for t in hockey.teams if t.id == "t-u13-01")
    team.rules = RuleOverrides(min_rest_minutes=24 * 60)
    a = game(hockey, "t-u13-01", "t-u13-02", "s-north-1", SAT, "12:00")
    b = game(hockey, "t-u13-01", "t-u13-03", "s-river", SUN, "08:00")
    vs = [v for v in validate(hockey, [a, b]) if v.code == Code.NOT_ENOUGH_REST]
    assert [v.team_ids for v in vs] == [("t-u13-01",)]  # t-u13-02/03 have no rest rule


def test_h6_two_games_in_a_day(hockey: League) -> None:
    a = game(hockey, "t-u13-01", "t-u13-02", "s-north-1", SAT, "07:00")
    b = game(hockey, "t-u13-01", "t-u13-03", "s-east", SAT, "14:00")
    vs = [v for v in validate(hockey, [a, b]) if v.code == Code.TOO_MANY_IN_A_DAY]
    assert [v.team_ids for v in vs] == [("t-u13-01",)]


def test_h6_two_games_a_day_allowed_when_configured(hockey: League) -> None:
    div = next(d for d in hockey.divisions if d.id == "d-u13")
    div.rules = RuleOverrides(max_games_per_day=2)
    a = game(hockey, "t-u13-01", "t-u13-02", "s-north-1", SAT, "07:00")
    b = game(hockey, "t-u13-01", "t-u13-03", "s-east", SAT, "14:00")
    assert codes(hockey, [a, b]) == set()


def test_h6_practice_doesnt_count_toward_games_per_day(hockey: League) -> None:
    a = game(hockey, "t-u13-01", "t-u13-02", "s-north-1", SAT, "07:00")
    p = game(hockey, "t-u13-01", None, "s-east", SAT, "14:00")
    assert codes(hockey, [a, p]) == set()


# ── H7: age-appropriate time windows ───────────────────────────────────────


def test_h7_too_late_for_u9(hockey: League) -> None:
    late = game(hockey, "t-u9-01", "t-u9-02", "s-river", TUE, "19:00")  # ends 7:50 PM
    vs = [v for v in validate(hockey, [late]) if v.code == Code.OUTSIDE_TIME_WINDOW]
    assert len(vs) == 2  # reported for each team so both can see why
    assert "7:00 AM and 7:00 PM" in vs[0].message


def test_h7_same_slot_fine_for_older_kids(hockey: League) -> None:
    a = game(hockey, "t-u13-01", "t-u13-02", "s-river", TUE, "19:00")
    assert codes(hockey, [a]) == set()


def test_h7_too_early(hockey: League) -> None:
    div = next(d for d in hockey.divisions if d.id == "d-u13")
    div.rules = RuleOverrides(earliest_start=time(8))
    a = game(hockey, "t-u13-01", "t-u13-02", "s-north-1", SAT, "07:00")
    assert Code.OUTSIDE_TIME_WINDOW in codes(hockey, [a])


# ── cross-cutting ──────────────────────────────────────────────────────────


def test_empty_schedule_is_legal(hockey: League) -> None:
    assert validate(hockey, []) == []


def test_messages_are_plain_language(nightmare: League) -> None:
    """Throw a pile of random (mostly illegal) games at the checker: every message must
    use names, never internal ids, and read as a sentence."""
    rng = random.Random(1)
    teams = [t.id for t in nightmare.teams]
    events = []
    for i, s in enumerate(rng.sample(nightmare.slots, 120)):
        home, away = rng.sample(teams, 2)
        events.append(
            Event(
                id=f"e{i}",
                division_id=next(t.division_id for t in nightmare.teams if t.id == home),
                home_team_id=home,
                away_team_id=away,
                slot_id=s.id,
                start=s.start_dt,
                minutes=rng.choice([50, 60, 75]),
                units=rng.choice([1, 2]),
            )
        )
    vs = validate(nightmare, events)
    assert {v.code for v in vs} >= {Code.TEAM_DOUBLE_BOOKED, Code.OUTSIDE_SLOT}
    for v in vs:
        assert not re.search(r"\b(t|c|s|sl|v|d|b)-[a-z0-9]", v.message), v.message
        assert v.message[0].isupper() and v.message.endswith("."), v.message


def test_fast_enough_for_live_drag_checks(hockey: League) -> None:
    rng = random.Random(2)
    teams = [t.id for t in hockey.teams]
    events = [
        Event(
            id=f"e{i}",
            division_id="d-u13",
            home_team_id=(pair := rng.sample(teams, 2))[0],
            away_team_id=pair[1],
            slot_id=s.id,
            start=s.start_dt,
            minutes=60,
            units=2,
        )
        for i, s in enumerate(rng.sample(hockey.slots, 240))
    ]
    t0 = clock.perf_counter()
    validate(hockey, events)
    assert clock.perf_counter() - t0 < 1.0


def test_blackout_scopes_need_a_target() -> None:
    with pytest.raises(ValueError):
        Blackout(id="x", scope=BlackoutScope.TEAM, start_date=SAT, end_date=SAT)

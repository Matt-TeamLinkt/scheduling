"""The importer must take messy real-world files, never crash, and say what it did."""

from __future__ import annotations

import csv
import io
from collections.abc import Sequence
from datetime import date, datetime, time
from pathlib import Path

import pytest
from openpyxl import Workbook

from scheduling_engine import Division, League, Severity, Sport, Venue, check_setup, fixtures
from scheduling_engine.importer import (
    Level,
    apply_import,
    preview_coaches,
    preview_slots,
    preview_teams,
)
from scheduling_engine.importer.values import (
    parse_date,
    parse_minutes,
    parse_time,
    parse_time_range,
    split_people,
)

DATA = Path(__file__).parent / "data"


def blank_league(**kw: object) -> League:
    base: dict[str, object] = dict(
        id="lg",
        name="Test league",
        sport=Sport.HOCKEY,
        season_start=date(2027, 1, 4),
        season_end=date(2027, 3, 28),
    )
    return League.model_validate(base | kw)


def club_league() -> League:
    return blank_league(
        divisions=[Division(id="d-u11", name="U11"), Division(id="d-u13", name="U13")],
        venues=[
            Venue(id="v-north", name="North Arena"),
            Venue(id="v-river", name="Riverside Arena"),
        ],
    )


def messages(preview: object, level: Level) -> list[str]:
    return [p.message for p in preview.problems_at(level)]  # type: ignore[attr-defined]


# ── teams ──────────────────────────────────────────────────────────────────


def test_messy_teams_file() -> None:
    lg = club_league()
    pv = preview_teams(lg, (DATA / "teams_messy.csv").read_bytes(), "teams_messy.csv")

    # Title rows skipped; columns matched despite odd headers.
    assert [(c.header, c.field) for c in pv.columns] == [
        ("Team Name", "team name"),
        ("Div.", "division"),
        ("Head Coach", "coach"),
        ("Coach Email", "coach email"),
        ("Home Arena", "home venue"),
    ]
    names = sorted(t.name for t in pv.changes.teams)
    assert names == ["Comets", "Falcons", "Kings", "Rangers", "Rovers", "Titans", "Wolves"]

    # "U-11", "u11", "U11", "U13 " all land in existing divisions.
    by_name = {t.name: t for t in pv.changes.teams}
    assert by_name["Falcons"].division_id == by_name["Rovers"].division_id == "d-u11"
    assert by_name["Rangers"].division_id == "d-u13"

    skipped = messages(pv, Level.SKIPPED)
    assert "Row 7 has no team name, so it was left out." in skipped
    assert any(m.startswith("Row 8: Strikers has no division") for m in skipped)
    assert any("Row 12: U11 already has a team called Falcons" in m for m in skipped)

    check = messages(pv, Level.CHECK)
    assert any(
        '"U13s" isn\'t one of your divisions' in m and "Did you mean U13?" in m for m in check
    )

    # Coaches: names tidied, de-duplicated across rows, two coaches on one row split,
    # "MacLeod, Robin" recognized as Robin MacLeod.
    coaches = {c.name: c for c in pv.changes.coaches}
    assert sorted(coaches) == [
        "Alex Ramsey",
        "Chris Okafor",
        "Jordan Lee",
        "Priya Nair",
        "Robin MacLeod",
        "Sam Diaz",
    ]
    assert len(coaches["Alex Ramsey"].team_ids) == 2
    assert coaches["Alex Ramsey"].email == "alex@example.com"
    assert len(coaches["Robin MacLeod"].team_ids) == 2
    notes = messages(pv, Level.NOTE)
    assert any(m.startswith("Alex Ramsey coaches 2 teams (Falcons, Titans)") for m in notes)
    assert "We'll add Eastside Arena as a new venue" in " ".join(notes)

    assert pv.summary.startswith("We'll add 7 teams in 3 divisions (1 of them new) and 6 new")
    assert "3 rows will be left out." in pv.summary
    assert "1 row needs a quick look." in pv.summary


def test_apply_teams_leaves_original_untouched() -> None:
    lg = club_league()
    pv = preview_teams(lg, (DATA / "teams_messy.csv").read_bytes(), "teams_messy.csv")
    after = apply_import(lg, pv)
    assert lg.teams == [] and len(after.teams) == 7
    assert [p for p in check_setup(after) if p.severity == Severity.ERROR] == []


def test_teams_from_excel_with_a_title_row() -> None:
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.append(["Fall house league"])
    ws.append(["Squad", "Age Group", "Coach"])
    ws.append(["Hawks", "U11", "Dana Fraser"])
    ws.append(["Owls", 11, "Dana Fraser"])  # a bare number for the age group
    buf = io.BytesIO()
    wb.save(buf)
    pv = preview_teams(club_league(), buf.getvalue(), "teams.xlsx")
    assert [t.name for t in pv.changes.teams] == ["Hawks", "Owls"]
    assert pv.changes.teams[0].division_id == "d-u11"
    assert [d.name for d in pv.changes.divisions] == ["11"]


def test_missing_required_column_explains_how_to_fix() -> None:
    pv = preview_teams(club_league(), b"Team,Coach\nFalcons,Alex\n", "teams.csv")
    assert not pv.can_import
    assert messages(pv, Level.SKIPPED) == [
        "We couldn't find a column for division in this teams file. Add a column headed "
        '"Division" and try again.'
    ]
    assert pv.summary.startswith("Nothing can be imported")


@pytest.mark.parametrize(
    ("data", "filename", "expect"),
    [
        (b"", "teams.csv", "The file is empty."),
        (b"\x00\x01garbage", "teams.xls", "older Excel file (.xls)"),
        (b"PK\x03\x04broken", "teams.xlsx", "couldn't be opened"),
        (b"just some words\n", "teams.csv", "couldn't find column headers"),
    ],
)
def test_bad_files_never_crash(data: bytes, filename: str, expect: str) -> None:
    pv = preview_teams(club_league(), data, filename)
    assert not pv.can_import
    assert expect in pv.problems[0].message


# ── coaches ────────────────────────────────────────────────────────────────


def test_coaches_file_links_existing_teams() -> None:
    lg = club_league()
    lg = apply_import(
        lg,
        preview_teams(
            lg, b"Team,Division\nFalcons,U11\nRovers,U11\nTitans,U13\nComets,U11\n", "t.csv"
        ),
    )
    pv = preview_coaches(lg, (DATA / "coaches_semicolon.csv").read_bytes(), "coaches.csv")
    coaches = {c.name: c for c in pv.changes.coaches}
    assert sorted(coaches) == ["Alex Ramsey", "Sam Diaz"]
    assert len(coaches["Sam Diaz"].team_ids) == 2  # "Rovers / Titans"
    skipped = messages(pv, Level.SKIPPED)
    assert any('no team called "Falcon". Did you mean Falcons?' in m for m in skipped)
    assert "Row 5 has no coach name, so it was left out." in skipped


def test_coaches_file_adds_teams_to_an_existing_coach() -> None:
    lg = club_league()
    lg = apply_import(
        lg,
        preview_teams(lg, b"Team,Division,Coach\nFalcons,U11,Alex Ramsey\nTitans,U13,\n", "t.csv"),
    )
    pv = preview_coaches(lg, b"Coach,Team\nALEX RAMSEY,Titans\nAlex Ramsey,Falcons\n", "c.csv")
    assert pv.changes.coaches == []
    assert len(pv.changes.coach_links) == 1  # Falcons was already linked
    after = apply_import(lg, pv)
    assert len(after.coaches[0].team_ids) == 2


# ── slots ──────────────────────────────────────────────────────────────────


def test_messy_slots_file() -> None:
    lg = fixtures.league_40()
    lg.slots = []
    pv = preview_slots(lg, (DATA / "slots_messy.csv").read_bytes(), "ice.csv")

    got = sorted((s.surface_id, s.date, s.start, s.end, s.cost) for s in pv.changes.slots)
    new_venue = {v.name: v.id for v in pv.changes.venues}
    lakeview_surface = next(
        s.id for s in pv.changes.surfaces if s.venue_id == new_venue["Lakeview Rink"]
    )
    nrth_surface = next(s.id for s in pv.changes.surfaces if s.venue_id == new_venue["Nrth Arena"])
    assert got == sorted(
        [
            ("s-north-1", date(2027, 1, 9), time(7), time(8, 15), 250.0),
            ("s-north-1", date(2027, 1, 9), time(8, 15), time(9, 30), 250.0),
            ("s-north-2", date(2027, 1, 9), time(7), time(8, 15), None),
            ("s-river", date(2027, 1, 12), time(19), time(20), 180.0),  # only rink at Riverside
            (lakeview_surface, date(2027, 2, 2), time(18, 30), time(19, 30), None),
            (nrth_surface, date(2027, 1, 16), time(7), time(8, 15), None),
            ("s-north-1", date(2027, 6, 20), time(7), time(8, 15), None),
        ]
    )

    skipped = messages(pv, Level.SKIPPED)
    assert any(
        m.startswith("Row 7: Riverside Arena Main Rink already has 7:00 PM") for m in skipped
    )
    assert any('Row 8: "13/45/2027" isn\'t a date we recognize' in m for m in skipped)
    assert any("Row 9: it ends (8:00 PM) before it starts (9:00 PM)" in m for m in skipped)
    assert any("Row 12: North Arena has 2 rinks" in m for m in skipped)

    check = messages(pv, Level.CHECK)
    assert any("Did you mean North Arena?" in m for m in check)
    assert any('we couldn\'t read the cost "TBD"' in m for m in check)
    assert any("Jun 20, 2027 is outside your season" in m for m in check)
    assert pv.summary.startswith(
        "We'll add 7 time slots (8 hours 15 min), 2 new venues and 2 new rinks."
    )


def test_slots_from_excel_with_real_date_and_time_cells() -> None:
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.append(["Venue", "Date", "Start", "Length"])
    ws.append(["Riverside Arena", datetime(2027, 1, 12), time(17, 0), 60])
    ws.append(["Riverside Arena", datetime(2027, 1, 12), time(18, 0), "1h"])
    buf = io.BytesIO()
    wb.save(buf)
    lg = fixtures.league_40()
    lg.slots = []
    pv = preview_slots(lg, buf.getvalue(), "ice.xlsx")
    assert [(s.surface_id, s.start, s.end) for s in pv.changes.slots] == [
        ("s-river", time(17), time(18)),
        ("s-river", time(18), time(19)),
    ]


def test_day_first_dates_detected_from_the_column() -> None:
    lg = fixtures.league_40()
    lg.slots = []
    data = (
        b"Venue,Date,Start,End\n"
        b"Riverside Arena,13/01/2027,17:00,18:00\n"
        b"Riverside Arena,02/01/2027,17:00,18:00\n"
    )
    pv = preview_slots(lg, data, "ice.csv")
    assert [s.date for s in pv.changes.slots] == [date(2027, 1, 13), date(2027, 1, 2)]


def test_ambiguous_dates_are_flagged() -> None:
    lg = fixtures.league_40()
    lg.slots = []
    pv = preview_slots(
        lg, b"Venue,Date,Start,End\nRiverside Arena,03/02/2027,17:00,18:00\n", "x.csv"
    )
    assert pv.changes.slots[0].date == date(2027, 3, 2)
    assert any("could be read either way" in m for m in messages(pv, Level.CHECK))


def test_existing_slots_are_not_duplicated() -> None:
    lg = fixtures.league_40()
    pv = preview_slots(
        lg, b"Venue,Rink,Date,Start,End\nNorth Arena,Rink 1,2027-01-09,7:00,8:15\n", "x.csv"
    )
    assert pv.changes.slots == []
    assert any("already has 7:00 AM" in m for m in messages(pv, Level.SKIPPED))


# ── round trip with a realistic league ─────────────────────────────────────


def shared_coaches(lg: League) -> list[list[str]]:
    name = {t.id: t.name for t in lg.teams}
    return sorted(sorted(name[t] for t in c.team_ids) for c in lg.coaches if len(c.team_ids) > 1)


def ice(lg: League) -> list[tuple[str, str, date, time, time]]:
    surf = {s.id: s for s in lg.surfaces}
    venue = {v.id: v.name for v in lg.venues}
    return sorted(
        (venue[surf[s.surface_id].venue_id], surf[s.surface_id].name, s.date, s.start, s.end)
        for s in lg.slots
    )


def _csv(rows: Sequence[Sequence[object]]) -> bytes:
    buf = io.StringIO()
    csv.writer(buf).writerows(rows)
    return buf.getvalue().encode()


def test_round_trip_league_40() -> None:
    """Export the 40-team fixture to the kind of CSVs a league would have, import them into
    an empty league, and get the same teams, shared coaches and ice back."""
    src = fixtures.league_40()
    div_name = {d.id: d.name for d in src.divisions}
    coaches_of: dict[str, list[str]] = {}
    for c in src.coaches:
        for t in c.team_ids:
            coaches_of.setdefault(t, []).append(c.name)
    teams_csv = _csv(
        [["Team", "Division", "Coach"]]
        + [
            [t.name, div_name[t.division_id], " & ".join(coaches_of.get(t.id, []))]
            for t in src.teams
        ]
    )
    venue_of = {s.id: s.venue_id for s in src.surfaces}
    vname = {v.id: v.name for v in src.venues}
    sname = {s.id: s.name for s in src.surfaces}
    slots_csv = _csv(
        [["Facility", "Surface", "Date", "Start", "End"]]
        + [
            [
                vname[venue_of[s.surface_id]],
                sname[s.surface_id],
                s.date.strftime("%m/%d/%Y"),
                s.start.strftime("%I:%M %p"),
                s.end.strftime("%I:%M %p"),
            ]
            for s in src.slots
        ]
    )

    lg = blank_league()
    pv_t = preview_teams(lg, teams_csv, "teams.csv")
    assert messages(pv_t, Level.SKIPPED) == [] and messages(pv_t, Level.CHECK) == []
    lg = apply_import(lg, pv_t)
    pv_s = preview_slots(lg, slots_csv, "slots.csv")
    assert messages(pv_s, Level.SKIPPED) == [] and messages(pv_s, Level.CHECK) == []
    lg = apply_import(lg, pv_s)

    assert sorted(t.name for t in lg.teams) == sorted(t.name for t in src.teams)
    assert sorted(d.name for d in lg.divisions) == sorted(d.name for d in src.divisions)
    assert shared_coaches(lg) == shared_coaches(src)
    assert ice(lg) == ice(src)
    assert all(s.units == 2 for s in lg.surfaces)  # hockey preset: splittable rinks
    assert [p for p in check_setup(lg) if p.severity == Severity.ERROR] == []


# ── value parsing ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("raw", "expect"),
    [
        ("7:00 PM", time(19)),
        ("7pm", time(19)),
        ("7:30p", time(19, 30)),
        ("19:00", time(19)),
        ("1900", time(19)),
        ("730", time(7, 30)),
        ("noon", time(12)),
        ("12:15 AM", time(0, 15)),
        ("7.30 pm", time(19, 30)),
        ("7:00 a.m.", time(7)),
        (0.75, time(18)),
        ("25:00", None),
        ("13pm", None),
        ("soon", None),
    ],
)
def test_parse_time(raw: object, expect: time | None) -> None:
    assert parse_time(raw) == expect  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("raw", "expect"),
    [
        ("7:00 PM - 8:15 PM", (time(19), time(20, 15))),
        ("7-8:15pm", (time(19), time(20, 15))),
        ("11-12:15pm", (time(11), time(12, 15))),
        ("19:00 to 20:15", (time(19), time(20, 15))),
        ("7:00 AM – 8:15 AM", (time(7), time(8, 15))),
        ("whenever", None),
    ],
)
def test_parse_time_range(raw: str, expect: tuple[time, time] | None) -> None:
    assert parse_time_range(raw) == expect


@pytest.mark.parametrize(
    ("raw", "day_first", "expect"),
    [
        ("2027-01-09", False, date(2027, 1, 9)),
        ("1/9/2027", False, date(2027, 1, 9)),
        ("1/9/2027", True, date(2027, 9, 1)),
        ("01/09/27", False, date(2027, 1, 9)),
        ("Sat Jan 9 2027", False, date(2027, 1, 9)),
        ("Saturday, January 9th, 2027", False, date(2027, 1, 9)),
        ("9-Jan-2027", False, date(2027, 1, 9)),
        (46396, False, date(2027, 1, 9)),
        ("2/30/2027", False, None),
        ("tbd", False, None),
    ],
)
def test_parse_date(raw: object, day_first: bool, expect: date | None) -> None:
    assert parse_date(raw, day_first) == expect  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("raw", "expect"),
    [
        ("60", 60),
        ("60 min", 60),
        ("1:15", 75),
        ("1h15", 75),
        ("1.5 hours", 90),
        ("75m", 75),
        (90, 90),
        ("2 hrs", 120),
        ("0", None),
        ("long", None),
    ],
)
def test_parse_minutes(raw: object, expect: int | None) -> None:
    assert parse_minutes(raw) == expect  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("raw", "expect"),
    [
        ("Sam Diaz / Priya Nair", ["Sam Diaz", "Priya Nair"]),
        ("Sam Diaz & Priya Nair", ["Sam Diaz", "Priya Nair"]),
        ("Sam Diaz and Priya Nair", ["Sam Diaz", "Priya Nair"]),
        ("Sam Diaz, Priya Nair", ["Sam Diaz", "Priya Nair"]),
        ("MacLeod, Robin", ["Robin MacLeod"]),
        ("ROBIN MACLEOD", ["Robin MacLeod"]),
        ("o'brien sean", ["O'Brien Sean"]),
    ],
)
def test_split_people(raw: str, expect: list[str]) -> None:
    assert split_people(raw) == expect

from __future__ import annotations

from datetime import date

from conftest import game

from scheduling_engine import League
from scheduling_engine.changes import ChangeKind, changes_by_team, diff_schedules

SAT = date(2027, 1, 9)
SUN = date(2027, 1, 10)


def test_no_changes(hockey: League) -> None:
    e = game(hockey, "t-u13-01", "t-u13-02", "s-north-1", SAT, "07:00", id="g1")
    assert diff_schedules(hockey, [e], [e]) == []


def test_moved_to_another_day_and_place(hockey: League) -> None:
    a = game(hockey, "t-u13-01", "t-u13-02", "s-north-1", SAT, "07:00", id="g1")
    b = game(hockey, "t-u13-01", "t-u13-02", "s-river", SUN, "08:00", id="g1")
    [c] = diff_schedules(hockey, [a], [b])
    assert c.kind == ChangeKind.MOVED
    assert c.message == (
        "North Stars U13 Blue vs Riverside Rapids U13 Blue moved from Sat Jan 9 at 7:00 AM at "
        "North Arena Rink 1 to Sun Jan 10 at 8:00 AM at Riverside Arena Main Rink."
    )


def test_new_time_same_place(hockey: League) -> None:
    a = game(hockey, "t-u13-01", "t-u13-02", "s-north-1", SAT, "07:00", id="g1")
    b = game(hockey, "t-u13-01", "t-u13-02", "s-north-1", SAT, "08:15", id="g1")
    [c] = diff_schedules(hockey, [a], [b])
    assert c.message.endswith("on Sat Jan 9 now starts at 8:15 AM (was 7:00 AM).")


def test_new_place_same_time(hockey: League) -> None:
    a = game(hockey, "t-u13-01", "t-u13-02", "s-north-1", SAT, "07:00", id="g1")
    b = game(hockey, "t-u13-01", "t-u13-02", "s-north-2", SAT, "07:00", id="g1")
    [c] = diff_schedules(hockey, [a], [b])
    assert "is now at North Arena Rink 2 (was North Arena Rink 1)" in c.message


def test_added_cancelled_swapped_and_who_to_tell(hockey: League) -> None:
    kept = game(hockey, "t-u13-01", "t-u13-02", "s-north-1", SAT, "07:00", id="g1")
    swapped = kept.model_copy(update={"home_team_id": "t-u13-02", "away_team_id": "t-u13-01"})
    gone = game(hockey, "t-u13-03", "t-u13-04", "s-north-2", SAT, "07:00", id="g2")
    new = game(hockey, "t-u13-05", "t-u13-06", "s-river", SUN, "08:00", id="g3")
    cs = diff_schedules(hockey, [kept, gone], [swapped, new])
    assert [c.kind for c in cs] == [ChangeKind.SWAPPED, ChangeKind.CANCELLED, ChangeKind.ADDED]
    assert cs[1].message.startswith("Cancelled: Eastside Eagles U13 Blue vs Westwood Wolves")
    assert cs[2].message.startswith("New: Lakeshore Lynx U13 Blue vs Hillcrest Hawks U13 Blue")
    who = changes_by_team(cs)
    assert set(who) == {"t-u13-01", "t-u13-02", "t-u13-03", "t-u13-04", "t-u13-05", "t-u13-06"}
    assert "t-u13-07" not in who  # unaffected teams hear nothing

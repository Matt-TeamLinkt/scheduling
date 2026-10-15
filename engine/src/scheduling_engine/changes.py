"""What changed between two versions of a schedule, in words families understand.

Used for the publish change log now, and for "only notify affected teams" in Phase 4.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from .index import LeagueIndex, fmt_day, fmt_time, fmt_when
from .model import Event, League


class ChangeKind(StrEnum):
    ADDED = "added"
    CANCELLED = "cancelled"
    MOVED = "moved"  # different time and/or place
    SWAPPED = "swapped"  # same time and place, home and away swapped


@dataclass(frozen=True)
class Change:
    kind: ChangeKind
    event_id: str
    team_ids: tuple[str, ...]
    message: str


def _what(ix: LeagueIndex, e: Event) -> str:
    if e.away_team_id is None:
        return f"{ix.team_name(e.home_team_id)} practice"
    return f"{ix.team_name(e.home_team_id)} vs {ix.team_name(e.away_team_id)}"


def diff_schedules(league: League, before: Sequence[Event], after: Sequence[Event]) -> list[Change]:
    ix = LeagueIndex(league)
    old = {e.id: e for e in before}
    new = {e.id: e for e in after}
    out: list[Change] = []
    for eid, e in new.items():
        o = old.get(eid)
        if o is None:
            out.append(
                Change(
                    ChangeKind.ADDED,
                    eid,
                    e.team_ids,
                    f"New: {_what(ix, e)}, {fmt_when(e.start)} at {ix.place(e.slot_id)}.",
                )
            )
            continue
        same_time = o.start == e.start and o.minutes == e.minutes
        same_place = ix.place(o.slot_id) == ix.place(e.slot_id)
        if same_time and same_place:
            if (o.home_team_id, o.away_team_id) != (e.home_team_id, e.away_team_id):
                out.append(
                    Change(
                        ChangeKind.SWAPPED,
                        eid,
                        e.team_ids,
                        f"{_what(ix, e)} on {fmt_when(e.start)}: home and away swapped.",
                    )
                )
            continue
        teams = tuple(dict.fromkeys(o.team_ids + e.team_ids))
        if same_place and o.start.date() == e.start.date():
            msg = (
                f"{_what(ix, e)} on {fmt_day(e.start)} now starts at {fmt_time(e.start)} "
                f"(was {fmt_time(o.start)})."
            )
        elif same_time:
            msg = (
                f"{_what(ix, e)} on {fmt_when(e.start)} is now at {ix.place(e.slot_id)} "
                f"(was {ix.place(o.slot_id)})."
            )
        else:
            msg = (
                f"{_what(ix, e)} moved from {fmt_when(o.start)} at {ix.place(o.slot_id)} "
                f"to {fmt_when(e.start)} at {ix.place(e.slot_id)}."
            )
        out.append(Change(ChangeKind.MOVED, eid, teams, msg))
    for eid, o in old.items():
        if eid not in new:
            out.append(
                Change(
                    ChangeKind.CANCELLED,
                    eid,
                    o.team_ids,
                    f"Cancelled: {_what(ix, o)}, {fmt_when(o.start)} at {ix.place(o.slot_id)}.",
                )
            )
    order = {e.id: (e.start, e.id) for e in [*before, *after]}
    out.sort(key=lambda c: order[c.event_id])
    return out


def changes_by_team(changes: Sequence[Change]) -> dict[str, list[Change]]:
    """team id -> the changes that affect it (who needs to be told)."""
    out: dict[str, list[Change]] = defaultdict(list)
    for c in changes:
        for t in c.team_ids:
            out[t].append(c)
    return dict(out)

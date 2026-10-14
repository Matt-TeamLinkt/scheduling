"""Hard-constraint checks: the single source of truth for "is this schedule legal?".

The solver, its tests, and the drag-and-drop UI all call `validate`. Every message is
written for a volunteer scheduler, not a developer.

Hard constraints (docs/ROADMAP.md):
  H1 a team can't be in two places at once
  H2 a surface can only hold what it's sized for
  H3 blackouts (league, division, team, venue, surface)
  H4 games only inside slots the league has, inside the season
  H5 coaches can't be in two places at once
  H6 minimum rest and max games per day, per team
  H7 age-appropriate time windows
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import datetime
from enum import StrEnum
from itertools import combinations

from pydantic import BaseModel, ConfigDict

from .index import LeagueIndex, fmt_day, fmt_minutes, fmt_time, fmt_when
from .model import Blackout, BlackoutScope, Event, League


class Code(StrEnum):
    UNKNOWN_REFERENCE = "unknown_reference"
    TEAM_DOUBLE_BOOKED = "team_double_booked"  # H1
    SURFACE_OVERBOOKED = "surface_overbooked"  # H2
    TOO_BIG_FOR_SURFACE = "too_big_for_surface"  # H2
    BLACKOUT = "blackout"  # H3
    OUTSIDE_SLOT = "outside_slot"  # H4
    OUTSIDE_SEASON = "outside_season"  # H4
    COACH_DOUBLE_BOOKED = "coach_double_booked"  # H5
    NOT_ENOUGH_REST = "not_enough_rest"  # H6
    TOO_MANY_IN_A_DAY = "too_many_in_a_day"  # H6
    OUTSIDE_TIME_WINDOW = "outside_time_window"  # H7


class Violation(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: Code
    message: str
    event_ids: tuple[str, ...]
    team_ids: tuple[str, ...] = ()


def validate(league: League, events: Sequence[Event]) -> list[Violation]:
    """Return every hard-constraint violation in `events`. Empty list = legal."""
    ix = LeagueIndex(league)
    out: list[Violation] = []
    known: list[Event] = []
    for e in events:
        missing = _missing_refs(ix, e)
        if missing:
            out.append(
                Violation(
                    code=Code.UNKNOWN_REFERENCE,
                    message=f"Event {e.id} refers to {missing} that no longer exists.",
                    event_ids=(e.id,),
                )
            )
        else:
            known.append(e)

    for e in known:
        out.extend(_check_slot_and_season(ix, e))
        out.extend(_check_time_window(ix, e))
        out.extend(_check_blackouts(ix, e))
    out.extend(_check_surfaces(ix, known))
    out.extend(_check_teams(ix, known))
    out.extend(_check_coaches(ix, known))
    return out


# ── per-event checks ────────────────────────────────────────────────────────


def _missing_refs(ix: LeagueIndex, e: Event) -> str | None:
    if e.slot_id not in ix.slots:
        return f"slot {e.slot_id}"
    if ix.slots[e.slot_id].surface_id not in ix.surfaces:
        return f"the surface of slot {e.slot_id}"
    for tid in e.team_ids:
        if tid not in ix.teams:
            return f"team {tid}"
    if e.division_id not in ix.divisions:
        return f"division {e.division_id}"
    return None


def _check_slot_and_season(ix: LeagueIndex, e: Event) -> Iterable[Violation]:
    slot = ix.slots[e.slot_id]
    lg = ix.league
    if not lg.season_start <= e.start.date() <= lg.season_end:
        yield Violation(
            code=Code.OUTSIDE_SEASON,
            message=(
                f"{ix.describe(e)} is outside the season "
                f"({lg.season_start:%b} {lg.season_start.day} to "
                f"{lg.season_end:%b} {lg.season_end.day})."
            ),
            event_ids=(e.id,),
            team_ids=e.team_ids,
        )
    if e.start < slot.start_dt or e.end > slot.end_dt:
        yield Violation(
            code=Code.OUTSIDE_SLOT,
            message=(
                f"{ix.describe(e)} runs {fmt_time(e.start)} to {fmt_time(e.end)}, but the "
                f"league only has {ix.place(e.slot_id)} from {fmt_time(slot.start_dt)} to "
                f"{fmt_time(slot.end_dt)} on {fmt_day(slot.start_dt)}."
            ),
            event_ids=(e.id,),
            team_ids=e.team_ids,
        )
    surface = ix.surfaces[slot.surface_id]
    if e.units > surface.units:
        yield Violation(
            code=Code.TOO_BIG_FOR_SURFACE,
            message=(
                f"{ix.describe(e)} needs more space than {ix.place(e.slot_id)} has "
                f"({e.units} units needed, {surface.units} available)."
            ),
            event_ids=(e.id,),
            team_ids=e.team_ids,
        )


def _check_time_window(ix: LeagueIndex, e: Event) -> Iterable[Violation]:
    for tid in e.team_ids:
        r = ix.team_rules(tid)
        if (
            e.start.time() < r.earliest_start
            or e.end.time() > r.latest_end
            or (e.end.date() != e.start.date())
        ):
            earliest = datetime.combine(e.start.date(), r.earliest_start)
            latest = datetime.combine(e.start.date(), r.latest_end)
            yield Violation(
                code=Code.OUTSIDE_TIME_WINDOW,
                message=(
                    f"{ix.describe(e)} runs {fmt_time(e.start)} to {fmt_time(e.end)}, but "
                    f"{ix.team_name(tid)} should only play between {fmt_time(earliest)} "
                    f"and {fmt_time(latest)}."
                ),
                event_ids=(e.id,),
                team_ids=(tid,),
            )


def _blackout_applies(ix: LeagueIndex, b: Blackout, e: Event) -> bool:
    surface = ix.surfaces[ix.slots[e.slot_id].surface_id]
    match b.scope:
        case BlackoutScope.LEAGUE:
            return True
        case BlackoutScope.DIVISION:
            return b.target_id == e.division_id or any(
                ix.teams[t].division_id == b.target_id for t in e.team_ids
            )
        case BlackoutScope.TEAM:
            return b.target_id in e.team_ids
        case BlackoutScope.VENUE:
            return b.target_id == surface.venue_id
        case BlackoutScope.SURFACE:
            return b.target_id == surface.id


def _blackout_whom(ix: LeagueIndex, b: Blackout) -> str:
    tid = b.target_id or ""
    match b.scope:
        case BlackoutScope.LEAGUE:
            return "the whole league"
        case BlackoutScope.DIVISION:
            d = ix.divisions.get(tid)
            return d.name if d else "this division"
        case BlackoutScope.TEAM:
            return ix.team_name(tid)
        case BlackoutScope.VENUE:
            v = ix.venues.get(tid)
            return v.name if v else "this venue"
        case BlackoutScope.SURFACE:
            s = ix.surfaces.get(tid)
            return s.name if s else "this surface"


def _check_blackouts(ix: LeagueIndex, e: Event) -> Iterable[Violation]:
    for b in ix.league.blackouts:
        if b.covers(e.start, e.end) and _blackout_applies(ix, b, e):
            why = f" ({b.note})" if b.note else ""
            yield Violation(
                code=Code.BLACKOUT,
                message=(f"{ix.describe(e)} falls on a blackout for {_blackout_whom(ix, b)}{why}."),
                event_ids=(e.id,),
                team_ids=e.team_ids,
            )


# ── cross-event checks ──────────────────────────────────────────────────────


def _overlaps(a: Event, b: Event) -> bool:
    return a.start < b.end and b.start < a.end


def _check_surfaces(ix: LeagueIndex, events: Sequence[Event]) -> Iterable[Violation]:
    by_surface: dict[str, list[Event]] = defaultdict(list)
    for e in events:
        by_surface[ix.slots[e.slot_id].surface_id].append(e)
    for sid, evs in by_surface.items():
        cap = ix.surfaces[sid].units
        seen: set[frozenset[str]] = set()
        # Peak load always occurs at some event's start time.
        for e in evs:
            live = [o for o in evs if o.start <= e.start < o.end]
            if sum(o.units for o in live) <= cap:
                continue
            key = frozenset(o.id for o in live)
            if key in seen:
                continue
            seen.add(key)
            live.sort(key=lambda o: (o.start, o.id))
            listed = "; ".join(ix.describe(o) for o in live)
            yield Violation(
                code=Code.SURFACE_OVERBOOKED,
                message=(
                    f"{ix.place(e.slot_id)} is overbooked on {fmt_when(e.start)}: "
                    f"{len(live)} events need more room than it has. {listed}."
                ),
                event_ids=tuple(o.id for o in live),
                team_ids=tuple(t for o in live for t in o.team_ids),
            )


def _check_teams(ix: LeagueIndex, events: Sequence[Event]) -> Iterable[Violation]:
    by_team: dict[str, list[Event]] = defaultdict(list)
    for e in events:
        for t in e.team_ids:
            by_team[t].append(e)
    for tid, evs in by_team.items():
        evs.sort(key=lambda e: (e.start, e.id))
        name = ix.team_name(tid)
        rules = ix.team_rules(tid)

        # H1: overlapping events
        for a, b in combinations(evs, 2):
            if _overlaps(a, b):
                yield Violation(
                    code=Code.TEAM_DOUBLE_BOOKED,
                    message=(
                        f"{name} are booked twice at the same time: "
                        f"{ix.describe(a)}, and {ix.describe(b)}."
                    ),
                    event_ids=(a.id, b.id),
                    team_ids=(tid,),
                )

        # H6: rest between consecutive, non-overlapping events
        if rules.min_rest_minutes:
            for a, b in zip(evs, evs[1:], strict=False):
                if _overlaps(a, b):
                    continue
                gap = int((b.start - a.end).total_seconds() // 60)
                if gap < rules.min_rest_minutes:
                    yield Violation(
                        code=Code.NOT_ENOUGH_REST,
                        message=(
                            f"{name} only get {fmt_minutes(gap)} of rest between "
                            f"{ix.describe(a)} and {ix.describe(b)}. "
                            f"They need at least {fmt_minutes(rules.min_rest_minutes)}."
                        ),
                        event_ids=(a.id, b.id),
                        team_ids=(tid,),
                    )

        # H6: games per day (practices don't count toward the game limit)
        per_day: dict[object, list[Event]] = defaultdict(list)
        for e in evs:
            if e.away_team_id is not None:
                per_day[e.start.date()].append(e)
        for day_events in per_day.values():
            if len(day_events) > rules.max_games_per_day:
                n = rules.max_games_per_day
                yield Violation(
                    code=Code.TOO_MANY_IN_A_DAY,
                    message=(
                        f"{name} have {len(day_events)} games on "
                        f"{fmt_day(day_events[0].start)}. The limit is {n} "
                        f"{'game' if n == 1 else 'games'} a day."
                    ),
                    event_ids=tuple(e.id for e in day_events),
                    team_ids=(tid,),
                )


def _check_coaches(ix: LeagueIndex, events: Sequence[Event]) -> Iterable[Violation]:
    by_coach: dict[str, list[Event]] = defaultdict(list)
    for e in events:
        coach_ids = {c.id for t in e.team_ids for c in ix.coaches_of_team.get(t, [])}
        for cid in coach_ids:
            by_coach[cid].append(e)
    for cid, evs in by_coach.items():
        evs.sort(key=lambda e: (e.start, e.id))
        coach = ix.coaches[cid]
        for a, b in combinations(evs, 2):
            if not _overlaps(a, b):
                continue
            # Two of the coach's own teams double-booked is already a team problem
            # if it's the same team; only report distinct teams here.
            if set(a.team_ids) & set(b.team_ids) & set(coach.team_ids):
                continue
            yield Violation(
                code=Code.COACH_DOUBLE_BOOKED,
                message=(
                    f"{coach.name} coaches in two places at once: "
                    f"{ix.describe(a)}, and {ix.describe(b)}."
                ),
                event_ids=(a.id, b.id),
                team_ids=tuple(t for t in a.team_ids + b.team_ids if t in coach.team_ids),
            )

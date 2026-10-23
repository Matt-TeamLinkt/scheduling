"""Placing one game by hand: where it can go, and which spots are best.

    spots = open_spots(league, events, matchup)   # every legal spot, best first
    event = event_for(league, matchup, slot_id, start)

Used by the "Needs a spot" tray: games that didn't fit (or matchups built without
placing) are placed one at a time by the scheduler. Every spot returned passes
`validate`, so the tray can never suggest a spot that breaks a rule. Ranking is a
simple fairness score for the two teams involved, with the reasons in plain words.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from .index import LeagueIndex
from .matchups import Matchup
from .model import Event, EventKind, League
from .validate import _check_blackouts, _check_slot_and_season, _check_time_window, validate

SUGGESTED = 3  # how many spots are marked "Suggested"


@dataclass
class SpotChoice:
    slot_id: str
    start: datetime
    minutes: int
    units: int
    score: int  # lower is better
    good: list[str] = field(default_factory=list)  # why it's a good spot
    watch: list[str] = field(default_factory=list)  # trade-offs worth knowing
    suggested: bool = False
    problems: list[str] = field(default_factory=list)  # rules it breaks (empty = legal)


def event_for(league: League, m: Matchup, slot_id: str, start: datetime) -> Event:
    """The event a matchup becomes when it's put in `slot_id` at `start`."""
    return _event(LeagueIndex(league), m, slot_id, start)


def _event(ix: LeagueIndex, m: Matchup, slot_id: str, start: datetime) -> Event:
    rules = [ix.team_rules(t) for t in m.team_ids]
    units = [r.units for r in rules]
    size = (
        max(u for u in units if u is not None)
        if None not in units
        else ix.surfaces[ix.slots[slot_id].surface_id].units
    )
    return Event(
        id=m.id,
        kind=EventKind.GAME,
        division_id=m.division_id,
        home_team_id=m.home_team_id,
        away_team_id=m.away_team_id,
        slot_id=slot_id,
        start=start,
        minutes=max(r.game_minutes for r in rules),
        units=size,
    )


def open_spots(
    league: League, events: Sequence[Event], m: Matchup, with_problems: bool = False
) -> list[SpotChoice]:
    """Every spot where `m` can go without breaking a rule, best first. The best spot
    on each of the best few days is marked `suggested` and comes first.

    With `with_problems`, also the spots that break a rule (after all the legal ones,
    fewest problems first), each with the rule messages, for when nothing legal is left
    and the scheduler wants to place it anyway."""
    ix = LeagueIndex(league)
    teams = set(m.team_ids)
    coach_teams = {t for c in league.coaches if teams & set(c.team_ids) for t in c.team_ids}
    rest = max(ix.team_rules(t).min_rest_minutes for t in teams)
    reach = timedelta(minutes=rest) + timedelta(days=1)

    by_surface_day: dict[tuple[str, date], list[Event]] = defaultdict(list)
    for e in events:
        if e.slot_id in ix.slots:
            by_surface_day[(ix.slots[e.slot_id].surface_id, e.start.date())].append(e)
    related = [e for e in events if e.id != m.id and set(e.team_ids) & (teams | coach_teams)]
    team_days = {t: sorted(e.start.date() for e in events if t in e.team_ids) for t in teams}

    length = timedelta(minutes=max(ix.team_rules(t).game_minutes for t in teams))
    out: list[SpotChoice] = []
    for slot in league.slots:
        if slot.surface_id not in ix.surfaces:
            continue
        t = slot.start_dt
        while t + length <= slot.end_dt:
            probe = _event(ix, m, slot.id, t)
            t += length
            if any(_check_slot_and_season(ix, probe)):
                continue  # doesn't fit the slot at all: never offered
            own = [*_check_time_window(ix, probe), *_check_blackouts(ix, probe)]
            if own and not with_problems:
                continue
            nearby = by_surface_day[(slot.surface_id, probe.start.date())] + [
                e for e in related if abs(e.start - probe.start) <= reach
            ]
            context = [e for e in {e.id: e for e in nearby}.values() if e.id != m.id]
            broken = [v for v in validate(league, [*context, probe]) if probe.id in v.event_ids]
            if broken and not with_problems:
                continue
            choice = _score(ix, probe, team_days)
            choice.problems = list(dict.fromkeys(v.message for v in broken))
            out.append(choice)
    out.sort(key=lambda c: (len(c.problems), c.score, c.start, c.slot_id))
    # Suggest the best spot on each of the best few days, so the choices differ.
    days: set[date] = set()
    for c in out:
        if len(days) == SUGGESTED or c.problems:
            break
        if c.start.date() not in days:
            days.add(c.start.date())
            c.suggested = True
    picked = [c for c in out if c.suggested]
    for c in out:
        if len(picked) == SUGGESTED or c.problems:
            break
        if not c.suggested:
            c.suggested = True
            picked.append(c)
    out.sort(key=lambda c: (not c.suggested, len(c.problems), c.score, c.start, c.slot_id))
    return out


def _score(ix: LeagueIndex, e: Event, team_days: dict[str, list[date]]) -> SpotChoice:
    """Lower is better. Spreads each team's games out, avoids early and late times,
    and prefers the home team's own venue."""
    score = 0
    good: list[str] = []
    watch: list[str] = []
    day = e.start.date()
    closest: tuple[int, str] | None = None
    for tid in e.team_ids:
        days = team_days.get(tid, [])
        gaps = [abs((d - day).days) for d in days]
        gap = min(gaps) if gaps else None
        week = sum(1 for d in days if d.isocalendar()[:2] == day.isocalendar()[:2])
        if gap is not None and (closest is None or gap < closest[0]):
            closest = (gap, tid)
        if gap is not None:
            score += max(0, 7 - gap) * 10  # games close together cost the most
        if week:
            score += week * 15
            watch.append(f"{ix.team_name(tid)} already play {_times(week)} that week.")
        r = ix.team_rules(tid)
        if e.start.time() < r.early_before:
            score += 8
            watch.append(f"Early for {ix.team_name(tid)}.")
        elif e.start.time() >= r.late_from:
            score += 8
            watch.append(f"Late for {ix.team_name(tid)}.")
    if closest is None:
        good.append("Neither team has another game yet.")
    elif closest[0] >= 5:
        good.append(f"Both teams get at least {closest[0]} days between games.")
    elif closest[0] <= 1:
        watch.append(
            f"{ix.team_name(closest[1])} play "
            f"{'the same day' if closest[0] == 0 else 'the day before or after'}."
        )
    else:
        watch.append(f"{ix.team_name(closest[1])} have another game {closest[0]} days away.")
    home = ix.teams[e.home_team_id].home_venue_id
    venue = ix.surfaces[ix.slots[e.slot_id].surface_id].venue_id
    if home is not None:
        if venue == home:
            good.append(f"At {_owner(ix.team_name(e.home_team_id))} home venue.")
        else:
            score += 5
    return SpotChoice(e.slot_id, e.start, e.minutes, e.units, score, good, watch)


def _owner(name: str) -> str:
    """'Hawks U11' -> "Hawks U11's", 'Falcons' -> "Falcons'"."""
    return f"{name}'" if name.endswith("s") else f"{name}'s"


def _times(n: int) -> str:
    return "once" if n == 1 else "twice" if n == 2 else f"{n} times"

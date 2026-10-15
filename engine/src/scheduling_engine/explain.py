"""Explain, in plain language, why games don't fit, and what would fix it.

    capacity_check(league)          before solving: cheap, catches impossible setups
    explain(league, result)         after solving: why the unplaced games didn't fit,
                                    plus suggestions verified by re-solving

Suggestions are concrete changes (an extra weekly slot like ones the league already has,
a relaxed division rule, a lifted blackout). Each is first scored with a cheap upper
bound, then the best few are checked for real: keep every placed game where it is and
see how many of the missing games now fit. So "would let 10 of the 12 games fit" is a
number we actually got, never a guess.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from .index import LeagueIndex, fmt_time
from .matchups import Matchup, make_matchups
from .model import BlackoutScope, Event, League, Slot
from .solver import Game, ModelBuilder, SolveOptions, SolveResult, games_for, run

DAY_NAMES = ["Mondays", "Tuesdays", "Wednesdays", "Thursdays", "Fridays", "Saturdays", "Sundays"]


@dataclass
class Finding:
    message: str
    division_id: str | None = None
    games: int = 0  # how many games it affects


@dataclass
class Suggestion:
    message: str
    fixes: int  # games that fit with this change (verified by re-solving)
    of: int  # games that didn't fit before
    league: League = field(repr=False)  # the league with the change applied


@dataclass
class Explanation:
    summary: str
    findings: list[Finding]
    suggestions: list[Suggestion]


def _join(items: Sequence[str]) -> str:
    items = list(items)
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


# ── before solving ──────────────────────────────────────────────────────────


def capacity_check(league: League, matchups: Sequence[Matchup] | None = None) -> list[Finding]:
    if matchups is None:
        matchups, _ = make_matchups(league)
    b = ModelBuilder(league, games_for(league, matchups))
    b.build_candidates()
    return _capacity_findings(b)


def _capacity_findings(b: ModelBuilder) -> list[Finding]:
    ix = b.ix
    out: list[Finding] = []
    free = [g for g in b.games if g.fixed is None]

    # Games with nowhere legal to go at all.
    stuck: dict[str, list[Game]] = defaultdict(list)
    for g in free:
        if not b.cands[g.id]:
            stuck[g.division_id].append(g)
    for div_id, games in stuck.items():
        out.append(Finding(_why_nowhere(b, games[0], len(games)), div_id, len(games)))

    # Teams that need more games than they have days to play them on.
    caps = b.team_capacity()
    by_div: dict[str, list[tuple[str, int, int]]] = defaultdict(list)
    for t, (need, cap) in caps.items():
        if cap < need and not any(t in g.team_ids for gs in stuck.values() for g in gs):
            by_div[ix.teams[t].division_id].append((t, need, cap))
    for div_id, short in by_div.items():
        div = ix.divisions[div_id]
        where = _where_division_fits(b, div_id)
        per_day = ix.division_rules(div_id).max_games_per_day
        missing = sum(n - c for _, n, c in short)
        lost = (missing + 1) // 2
        if len({(n, c) for _, n, c in short}) == 1 and len(short) == sum(
            1 for team in ix.league.teams if team.division_id == div_id
        ):
            _, need, cap = short[0]
            days = cap // per_day
            msg = (
                f"Each {div.name} team needs {need} games but can only play on {days} days: "
                f"{where}, {_plural(per_day, 'game')} a day. That leaves about "
                f"{_plural(lost, 'game')} that can't be scheduled."
            )
        else:
            names = _join(
                [f"{ix.team_name(t)} ({c // per_day} days for {n} games)" for t, n, c in short]
            )
            msg = (
                f"Some {div.name} teams have fewer days they can play than games they need: "
                f"{names}. {where[0].upper() + where[1:]}."
            )
        out.append(Finding(msg, div_id, lost))
    return out


def _where_division_fits(b: ModelBuilder, div_id: str) -> str:
    """'U15 games fit only on Saturdays at North Arena (the only slots 75 minutes or longer)'"""
    ix = b.ix
    div = ix.divisions[div_id]
    spots = {s.key: s for g in b.games if g.division_id == div_id for s in b.cands[g.id]}
    weekdays = sorted({s.day.weekday() for s in spots.values()})
    venues = sorted({ix.venues[s.venue_id].name for s in spots.values() if s.venue_id in ix.venues})
    minutes = ix.division_rules(div_id).game_minutes
    shorter = sum(1 for s in ix.league.slots if s.minutes < minutes)
    why = f" (the only time slots {minutes} minutes or longer)" if shorter else ""
    days = _join([DAY_NAMES[d] for d in weekdays])
    return f"{div.name} games fit only on {days} at {_join(venues)}{why}"


def _why_nowhere(b: ModelBuilder, g: Game, n: int) -> str:
    ix = b.ix
    div = ix.divisions[g.division_id].name
    long_enough = [s for s in ix.league.slots if s.minutes >= g.minutes]
    if not long_enough:
        longest = max((s.minutes for s in ix.league.slots), default=0)
        return (
            f"{_plural(n, div + ' game')} can't be scheduled: they need {g.minutes} minutes, "
            f"but the longest time slot is {longest} minutes."
        )
    r = [ix.team_rules(t) for t in g.team_ids]
    earliest, latest = max(x.earliest_start for x in r), min(x.latest_end for x in r)
    in_window = [
        s
        for s in long_enough
        if s.start >= earliest
        and (datetime.combine(s.date, s.start) + timedelta(minutes=g.minutes)).time() <= latest
    ]
    if not in_window:
        e = fmt_time(datetime.combine(date.min, earliest))
        lt = fmt_time(datetime.combine(date.min, latest))
        return (
            f"{_plural(n, div + ' game')} can't be scheduled: they must be played between "
            f"{e} and {lt}, and no time slot long enough falls in that window."
        )
    return (
        f"{_plural(n, div + ' game')} can't be scheduled: every time slot that fits them "
        "falls on a blackout date for these teams."
    )


# ── after solving ───────────────────────────────────────────────────────────


def explain(
    league: League,
    result: SolveResult,
    try_fixes: bool = True,
    seconds_per_try: float = 10.0,
    max_tries: int = 3,
) -> Explanation:
    missing = result.unplaced
    if not missing:
        return Explanation("Every game fits.", [], [])
    # Capacity is judged on the whole season as if nothing were placed yet: "each U15
    # team needs 12 games but can only play on 10 days" is the real reason, even though
    # after solving only the last 2 per team are missing.
    everything = [
        Matchup(e.id, e.division_id, e.home_team_id, e.away_team_id, 0)
        for e in result.events
        if e.away_team_id is not None
    ] + list(missing)
    b = ModelBuilder(league, games_for(league, everything))
    b.build_candidates()

    findings = _capacity_findings(b)
    covered = sum(f.games for f in findings)
    if covered < len(missing):
        findings += _congestion(b, result.events, missing)

    by_div = Counter(m.division_id for m in missing)
    ix = b.ix
    parts = [f"{n} {ix.divisions[d].name}" for d, n in by_div.most_common()]
    summary = f"{_plural(len(missing), 'game')} didn't fit ({_join(parts)})."

    suggestions: list[Suggestion] = []
    if try_fixes:
        suggestions = _suggest(league, result, missing, seconds_per_try, max_tries)
        if suggestions:
            summary += " " + suggestions[0].message
    return Explanation(summary, findings, suggestions)


def _fixed(e: Event) -> Game:
    return Game(
        id=e.id,
        division_id=e.division_id,
        team_ids=e.team_ids,
        home_team_id=e.home_team_id,
        away_team_id=e.away_team_id,
        minutes=e.minutes,
        units=e.units,
        fixed=e,
    )


def _congestion(
    b: ModelBuilder, events: Sequence[Event], missing: Sequence[Matchup]
) -> list[Finding]:
    """For games that had legal spots: what was in the way at each of them."""
    ix = b.ix
    busy: dict[str, list[Event]] = defaultdict(list)
    on_surface: dict[str, list[Event]] = defaultdict(list)
    for e in events:
        for t in e.team_ids:
            busy[t].append(e)
        on_surface[ix.slots[e.slot_id].surface_id].append(e)
    out: list[Finding] = []
    by_div: dict[str, list[Matchup]] = defaultdict(list)
    for m in missing:
        by_div[m.division_id].append(m)
    for div_id, ms in by_div.items():
        reasons: Counter[str] = Counter()
        for m in ms:
            for s in b.cands.get(m.id, []):
                full = (
                    sum(
                        e.units
                        for e in on_surface[s.surface_id]
                        if e.start < s.end and s.start < e.end
                    )
                    + s.units
                    > ix.surfaces[s.surface_id].units
                )
                team_busy = any(e.start.date() == s.day for t in m.team_ids for e in busy[t])
                if full:
                    reasons["already full"] += 1
                elif team_busy:
                    reasons["one of the teams already plays that day"] += 1
                else:
                    reasons["it would clash with a coach's other team or a rest rule"] += 1
        if not reasons:
            continue
        top = _join([f"{n} because {why}" for why, n in reasons.most_common()])
        out.append(
            Finding(
                f"{_plural(len(ms), ix.divisions[div_id].name + ' game')} didn't fit. Of the "
                f"{sum(reasons.values())} times they could have been played, {top}.",
                div_id,
                len(ms),
            )
        )
    return out


# ── suggestions ─────────────────────────────────────────────────────────────


@dataclass
class _Change:
    message: str  # with {fixes} and {of} placeholders
    apply: Callable[[League], League]


def _candidate_changes(league: League, missing: Sequence[Matchup]) -> list[_Change]:
    ix = LeagueIndex(league)
    out: list[_Change] = []
    divs = {m.division_id for m in missing}
    for div_id in divs:
        div = ix.divisions[div_id]
        rules = ix.division_rules(div_id)
        minutes = rules.game_minutes

        # 1. One more slot of this division's game length each week, right after the last
        #    slot on a surface + weekday where the league already has time.
        patterns: dict[tuple[str, int], list[Slot]] = defaultdict(list)
        for s in league.slots:
            if s.surface_id in ix.surfaces:
                patterns[(s.surface_id, s.date.weekday())].append(s)
        for (surface_id, wd), slots in patterns.items():
            last_by_day: dict[date, Slot] = {}
            for s in slots:
                if s.date not in last_by_day or s.end > last_by_day[s.date].end:
                    last_by_day[s.date] = s
            new_slots = []
            for d, last in sorted(last_by_day.items()):
                start = datetime.combine(d, last.end)
                end = start + timedelta(minutes=minutes)
                if end.date() != d or end.time() > rules.latest_end:
                    continue
                new_slots.append(
                    Slot(
                        id=f"extra-{surface_id}-{d}",
                        surface_id=surface_id,
                        date=d,
                        start=start.time(),
                        end=end.time(),
                    )
                )
            if not new_slots:
                continue
            place = ix.place(slots[0].id)
            first = new_slots[0]
            when = fmt_time(datetime.combine(first.date, first.start))
            length = (
                datetime.combine(first.date, first.end) - datetime.combine(first.date, first.start)
            ).seconds // 60

            def add(lg: League, extra: list[Slot] = new_slots) -> League:
                c = lg.model_copy(deep=True)
                c.slots.extend(extra)
                return c

            msg = (
                f"Adding one more {length}-minute slot at {place} on {DAY_NAMES[wd]} at {when} "
                f"({len(new_slots)} dates) would let {{fixes}} of the {{of}} games fit."
            )
            out.append(_Change(msg, add))

        # 2. Allow two games a day for this division.
        if rules.max_games_per_day == 1:

            def two_a_day(lg: League, d: str = div_id) -> League:
                c = lg.model_copy(deep=True)
                dv = next(x for x in c.divisions if x.id == d)
                dv.rules = dv.rules.model_copy(update={"max_games_per_day": 2})
                return c

            msg = (
                f"Allowing {div.name} teams two games on the same day would let {{fixes}} of "
                "the {of} games fit."
            )
            out.append(_Change(msg, two_a_day))

        # 3. Lift a blackout that applies to this division (not league-wide holidays).
        for bo in league.blackouts:
            if bo.scope == BlackoutScope.DIVISION and bo.target_id == div_id:

                def lift(lg: League, bid: str = bo.id) -> League:
                    c = lg.model_copy(deep=True)
                    c.blackouts = [x for x in c.blackouts if x.id != bid]
                    return c

                label = bo.note or f"{bo.start_date:%b} {bo.start_date.day}"
                msg = (
                    f"Letting {div.name} play during its blackout ({label}) would let "
                    "{fixes} of the {of} games fit."
                )
                out.append(_Change(msg, lift))
    return out


def _suggest(
    league: League,
    result: SolveResult,
    missing: Sequence[Matchup],
    seconds: float,
    max_tries: int,
) -> list[Suggestion]:
    changes = _candidate_changes(league, missing)
    if not changes:
        return []

    def bound(lg: League) -> int:
        b = ModelBuilder(lg, [_fixed(e) for e in result.events] + games_for(lg, missing))
        b.build_candidates()
        return b.placed_upper_bound()

    # Cheap first pass: how many missing games could possibly fit after each change.
    scored = []
    for ch in changes:
        lg2 = ch.apply(league)
        best_case = bound(lg2)
        if best_case > 0:
            scored.append((best_case, ch, lg2))
    scored.sort(key=lambda t: -t[0])

    out: list[Suggestion] = []
    for _, ch, lg2 in scored[:max_tries]:
        # Real check: everything already placed stays put; place what's missing.
        games = [_fixed(e) for e in result.events] + games_for(lg2, missing)
        r = run(lg2, games, SolveOptions(priorities=(), time_limit_s=seconds, workers=4), [])
        fixes = sum(1 for e in r.events if e.id in {m.id for m in missing})
        if fixes:
            text = ch.message.format(fixes=fixes, of=len(missing))
            out.append(Suggestion(text, fixes, len(missing), lg2))
    out.sort(key=lambda s: -s.fixes)
    return out

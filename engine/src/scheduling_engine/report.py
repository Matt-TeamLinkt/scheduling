"""Fairness report: shown after every generation, and for any hand-edited schedule.

Measures the schedule itself (not the solver's internal score), per team, and flags
outliers in plain language. `metrics` is the compact version the quality benchmark
tracks over time.
"""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from itertools import combinations

from .goals import FAMILY_BUFFER, km
from .index import LeagueIndex, fmt_day
from .model import Event, League


@dataclass
class TeamLine:
    team_id: str
    name: str
    division: str
    games: int
    target: int
    home: int
    away: int
    early: int
    late: int
    back_to_back_days: int  # pairs of games on consecutive days
    busiest_week: int  # most games in any one week
    longest_gap_days: int  # longest stretch between games
    quickest_rematch_days: int | None  # fewest days between games against one opponent
    travel_km: float  # total km from home venue to games (0 if locations unknown)
    away_from_home_venue: int  # home games not at the team's home venue

    @property
    def early_or_late(self) -> int:
        return self.early + self.late


@dataclass
class Flag:
    message: str
    team_ids: tuple[str, ...] = ()
    kind: str = ""  # groups flags for the "what stands out" notes


@dataclass
class DivisionLine:
    """One division at a glance: ranges across its teams, and a one-line verdict."""

    name: str
    teams: int
    games: int  # games in the division, each counted once
    target: int
    fewest_games: int
    most_games: int
    home_away_worst: int
    early_late_fewest: int
    early_late_most: int
    back_to_back_days: int
    longest_gap_days: int
    quickest_rematch_days: int | None
    flags: int
    verdict: str


@dataclass
class FairnessReport:
    teams: list[TeamLine]
    family_clashes: list[str]
    flags: list[Flag]
    metrics: dict[str, float] = field(default_factory=dict)
    divisions: list[DivisionLine] = field(default_factory=list)
    highlights: list[str] = field(default_factory=list)  # "what stands out", plain words

    @property
    def summary(self) -> str:
        n = len(self.flags)
        if n == 0:
            return "Everything looks fair. Nothing stands out."
        return f"{n} thing{'s' if n != 1 else ''} worth a look."


def fairness_report(league: League, events: Sequence[Event]) -> FairnessReport:
    ix = LeagueIndex(league)
    by_team: dict[str, list[Event]] = defaultdict(list)
    for e in events:
        if e.away_team_id is None:
            continue  # practices don't count toward game fairness
        for t in e.team_ids:
            by_team[t].append(e)
    coords: dict[str, tuple[float, float]] = {
        v.id: (v.latitude, v.longitude)
        for v in league.venues
        if v.latitude is not None and v.longitude is not None
    }
    venue_of_slot = {
        s.id: ix.surfaces[s.surface_id].venue_id
        for s in league.slots
        if s.surface_id in ix.surfaces
    }

    lines: list[TeamLine] = []
    for team in league.teams:
        evs = sorted(by_team.get(team.id, []), key=lambda e: e.start)
        r = ix.team_rules(team.id)
        days = [e.start.date() for e in evs]
        b2b = sum(1 for a, b in zip(days, days[1:], strict=False) if (b - a).days == 1)
        weeks = Counter((d - league.season_start).days // 7 for d in days)
        bounds = [league.season_start, *days, league.season_end]
        gap = max((b - a).days for a, b in zip(bounds, bounds[1:], strict=False))
        rematch: int | None = None
        by_opp: dict[str, list[date]] = defaultdict(list)
        for e in evs:
            opp = e.away_team_id if e.home_team_id == team.id else e.home_team_id
            by_opp[opp or ""].append(e.start.date())
        for ds in by_opp.values():
            for a, b in zip(ds, ds[1:], strict=False):
                d = (b - a).days
                rematch = d if rematch is None else min(rematch, d)
        travel, away_home = 0.0, 0
        hv = team.home_venue_id
        for e in evs:
            v = venue_of_slot.get(e.slot_id)
            if hv and v and v != hv:
                if hv in coords and v in coords:
                    travel += km(coords[hv], coords[v])
                if e.home_team_id == team.id:
                    away_home += 1
        lines.append(
            TeamLine(
                team_id=team.id,
                name=team.name,
                division=ix.divisions[team.division_id].name
                if team.division_id in ix.divisions
                else "",
                games=len(evs),
                target=r.games_per_team,
                home=sum(e.home_team_id == team.id for e in evs),
                away=sum(e.away_team_id == team.id for e in evs),
                early=sum(e.start.time() < r.early_before for e in evs),
                late=sum(e.start.time() >= r.late_from for e in evs),
                back_to_back_days=b2b,
                busiest_week=max(weeks.values(), default=0),
                longest_gap_days=gap,
                quickest_rematch_days=rematch,
                travel_km=round(travel, 1),
                away_from_home_venue=away_home,
            )
        )

    clashes = _family_clashes(league, ix, events)
    flags = _flags(lines, clashes)
    misses = 0
    for c in league.coaches:
        if not c.prefers:
            continue
        theirs = [e for e in events if e.away_team_id and set(e.team_ids) & set(c.team_ids)]
        out = [e for e in theirs if not any(p.contains(e.start, e.end) for p in c.prefers)]
        misses += len(out)
        if out:
            wants = " or ".join(p.describe() for p in c.prefers)
            flags.append(
                Flag(
                    f"{c.name} would rather coach {wants}; {len(out)} of their "
                    f"{len(theirs)} games are at other times.",
                    tuple(c.team_ids),
                    "coach",
                )
            )
    metrics = _metrics(lines, clashes, len(events))
    metrics["coach_pref_misses"] = misses
    return FairnessReport(
        lines, clashes, flags, metrics, _divisions(lines, flags), _highlights(lines, flags)
    )


def _family_clashes(league: League, ix: LeagueIndex, events: Sequence[Event]) -> list[str]:
    out: list[str] = []
    for fam in league.families:
        for a, c in combinations(sorted(set(fam.team_ids)), 2):
            ea = [e for e in events if a in e.team_ids and c not in e.team_ids]
            ec = [e for e in events if c in e.team_ids and a not in e.team_ids]
            for x in ea:
                for y in ec:
                    if x.start < y.end + FAMILY_BUFFER and y.start < x.end + FAMILY_BUFFER:
                        out.append(
                            f"The {fam.name} family has kids on {ix.team_name(a)} and "
                            f"{ix.team_name(c)}, who play at the same time on "
                            f"{fmt_day(x.start)} ({ix.place(x.slot_id)} and {ix.place(y.slot_id)})."
                        )
    return out


def _flags(lines: list[TeamLine], clashes: list[str]) -> list[Flag]:
    flags: list[Flag] = []
    by_div: dict[str, list[TeamLine]] = defaultdict(list)
    for t in lines:
        by_div[t.division].append(t)
    for div, ts in by_div.items():
        avg_bad = statistics.mean(t.early_or_late for t in ts)
        for t in ts:
            if t.games < t.target:
                flags.append(
                    Flag(
                        f"{t.name} play {t.games} games; the target is {t.target}.",
                        (t.team_id,),
                        "short",
                    )
                )
            if abs(t.home - t.away) >= 2:
                flags.append(
                    Flag(
                        f"{t.name} have {t.home} home and {t.away} away games.",
                        (t.team_id,),
                        "home_away",
                    )
                )
            if t.early_or_late >= avg_bad + 2:
                flags.append(
                    Flag(
                        f"{t.name} have {t.early_or_late} early or late games; the {div} average "
                        f"is {avg_bad:.1f}.",
                        (t.team_id,),
                        "early_late",
                    )
                )
            if t.longest_gap_days >= 21:
                flags.append(
                    Flag(
                        f"{t.name} go {t.longest_gap_days} days without a game.",
                        (t.team_id,),
                        "long_gap",
                    )
                )
            if t.back_to_back_days >= 3:
                flags.append(
                    Flag(
                        f"{t.name} play on back-to-back days {t.back_to_back_days} times.",
                        (t.team_id,),
                        "back_to_back",
                    )
                )
            if t.quickest_rematch_days is not None and t.quickest_rematch_days < 7:
                flags.append(
                    Flag(
                        f"{t.name} play the same opponent twice within "
                        f"{t.quickest_rematch_days} days.",
                        (t.team_id,),
                        "rematch",
                    )
                )
    flags += [Flag(c, (), "family") for c in clashes]
    return flags


def _divisions(lines: list[TeamLine], flags: list[Flag]) -> list[DivisionLine]:
    out: list[DivisionLine] = []
    by_div: dict[str, list[TeamLine]] = defaultdict(list)
    for t in lines:
        by_div[t.division].append(t)
    for div, ts in by_div.items():
        ids = {t.team_id for t in ts}
        n_flags = sum(1 for f in flags if set(f.team_ids) & ids)
        games = [t.games for t in ts]
        bad = [t.early_or_late for t in ts]
        rematches = [t.quickest_rematch_days for t in ts if t.quickest_rematch_days is not None]
        worst = max(abs(t.home - t.away) for t in ts)
        target = max(t.target for t in ts)
        line = DivisionLine(
            name=div,
            teams=len(ts),
            games=sum(t.home for t in ts),
            target=target,
            fewest_games=min(games),
            most_games=max(games),
            home_away_worst=worst,
            early_late_fewest=min(bad),
            early_late_most=max(bad),
            back_to_back_days=sum(t.back_to_back_days for t in ts),
            longest_gap_days=max(t.longest_gap_days for t in ts),
            quickest_rematch_days=min(rematches, default=None),
            flags=n_flags,
            verdict="",
        )
        line.verdict = _verdict(line)
        out.append(line)
    return out


def _verdict(d: DivisionLine) -> str:
    """'Every team plays 12 games, home and away within 1, 0 to 2 early or late games.'"""
    if d.fewest_games == d.most_games:
        games = f"Every team plays {d.most_games} {'game' if d.most_games == 1 else 'games'}"
    else:
        games = f"Teams play {d.fewest_games} to {d.most_games} games"
    if d.fewest_games < d.target:
        games += f" (target {d.target})"
    balance = (
        "home and away even"
        if d.home_away_worst == 0
        else (f"home and away within {d.home_away_worst}")
    )
    if d.early_late_fewest == d.early_late_most:
        times = f"{d.early_late_most} early or late each"
    else:
        times = f"{d.early_late_fewest} to {d.early_late_most} early or late games each"
    return f"{games}, {balance}, {times}."


WHAT_STANDS_OUT = {
    "short": "{n} play fewer games than the target.",
    "home_away": "{n} have home and away games out of balance.",
    "early_late": "{n} have more early or late games than their division average.",
    "long_gap": "{n} go three weeks or more without a game.",
    "back_to_back": "{n} play on back-to-back days three or more times.",
    "rematch": "{n} play the same opponent twice within a week.",
}


def _highlights(lines: list[TeamLine], flags: list[Flag]) -> list[str]:
    """The flags grouped into a few sentences, most serious first."""
    out: list[str] = []
    for kind, text in WHAT_STANDS_OUT.items():
        teams = {t for f in flags if f.kind == kind for t in f.team_ids}
        if teams:
            n = len(teams)
            out.append(text.format(n="1 team" if n == 1 else f"{n} teams"))
    families = sum(1 for f in flags if f.kind == "family")
    if families:
        out.append(
            "1 family has kids playing at the same time."
            if families == 1
            else f"{families} times, a family has kids playing at the same time."
        )
    coaches = sum(1 for f in flags if f.kind == "coach")
    if coaches:
        n = coaches
        out.append(
            f"{n} {'coach has' if n == 1 else 'coaches have'} games outside the times they prefer."
        )
    if not out and lines:
        out.append("Every team gets about the same deal. Nothing stands out.")
    return out


def _metrics(lines: list[TeamLine], clashes: list[str], n_events: int) -> dict[str, float]:
    by_div: dict[str, list[TeamLine]] = defaultdict(list)
    for t in lines:
        by_div[t.division].append(t)
    spread = max(
        (
            max(t.early_or_late for t in ts) - min(t.early_or_late for t in ts)
            for ts in by_div.values()
        ),
        default=0,
    )
    rematches = [t.quickest_rematch_days for t in lines if t.quickest_rematch_days is not None]
    return {
        "games": n_events,
        "short_of_target": sum(max(0, t.target - t.games) for t in lines),
        "home_away_worst": max((abs(t.home - t.away) for t in lines), default=0),
        "early_late_spread": spread,
        "back_to_back_days": sum(t.back_to_back_days for t in lines),
        "longest_gap_days": max((t.longest_gap_days for t in lines), default=0),
        "quickest_rematch_days": min(rematches, default=float("nan")),
        "family_clashes": len(clashes),
        "travel_km": round(sum(t.travel_km for t in lines), 1),
        "away_from_home_venue": sum(t.away_from_home_venue for t in lines),
    }

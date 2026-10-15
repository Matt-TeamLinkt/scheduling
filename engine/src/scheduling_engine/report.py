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


@dataclass
class FairnessReport:
    teams: list[TeamLine]
    family_clashes: list[str]
    flags: list[Flag]
    metrics: dict[str, float] = field(default_factory=dict)

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
    return FairnessReport(lines, clashes, flags, _metrics(lines, clashes, len(events)))


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
                    Flag(f"{t.name} play {t.games} games; the target is {t.target}.", (t.team_id,))
                )
            if abs(t.home - t.away) >= 2:
                flags.append(
                    Flag(f"{t.name} have {t.home} home and {t.away} away games.", (t.team_id,))
                )
            if t.early_or_late >= avg_bad + 2:
                flags.append(
                    Flag(
                        f"{t.name} have {t.early_or_late} early or late games; the {div} average "
                        f"is {avg_bad:.1f}.",
                        (t.team_id,),
                    )
                )
            if t.longest_gap_days >= 21:
                flags.append(
                    Flag(f"{t.name} go {t.longest_gap_days} days without a game.", (t.team_id,))
                )
            if t.back_to_back_days >= 3:
                flags.append(
                    Flag(
                        f"{t.name} play on back-to-back days {t.back_to_back_days} times.",
                        (t.team_id,),
                    )
                )
            if t.quickest_rematch_days is not None and t.quickest_rematch_days < 7:
                flags.append(
                    Flag(
                        f"{t.name} play the same opponent twice within "
                        f"{t.quickest_rematch_days} days.",
                        (t.team_id,),
                    )
                )
    flags += [Flag(c) for c in clashes]
    return flags


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

"""Soft goals: what makes a legal schedule a *fair* one.

The scheduler ranks goals in plain language; rank turns into a weight (top = 16, then
8, 4, 2, 1). Each goal's penalty is measured in a unit chosen so one unit of each goal
is about equally annoying to a family:
  fair times      one more early/late game for the most burdened team than the least
  spacing         one pair of games on back-to-back days, or one extra game in a week
  families        one time clash for a family with kids on two teams
  repeat opponent one day short of two weeks between rematches (7 days short = 7)
  travel          10 km driven, or one home game away from the home venue
  coach times     one game outside a coach's preferred times
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Sequence
from datetime import date, datetime, timedelta
from enum import StrEnum
from itertools import combinations
from typing import TYPE_CHECKING

from ortools.sat.python import cp_model

from .cp import Expr, total

if TYPE_CHECKING:
    from .solver import ModelBuilder


class Goal(StrEnum):
    FAIR_TIMES = "fair_times"
    SPACING = "spacing"
    FAMILIES = "families"
    REPEAT_OPPONENT = "repeat_opponent"
    TRAVEL = "travel"
    COACH_TIMES = "coach_times"


GOAL_LABELS: dict[Goal, str] = {
    Goal.FAIR_TIMES: "Share early and late games fairly",
    Goal.SPACING: "Spread each team's games through the season",
    Goal.FAMILIES: "Avoid clashes for families with kids on two teams",
    Goal.REPEAT_OPPONENT: "Don't face the same opponent twice in a short time",
    Goal.TRAVEL: "Keep travel short",
    Goal.COACH_TIMES: "Give coaches the times they prefer",
}

DEFAULT_PRIORITIES: tuple[Goal, ...] = (
    Goal.FAIR_TIMES,
    Goal.SPACING,
    Goal.FAMILIES,
    Goal.REPEAT_OPPONENT,
    Goal.TRAVEL,
    Goal.COACH_TIMES,
)

# Unit costs (see module docstring) so the ranking, not the units, decides trade-offs.
UNIT = {
    Goal.FAIR_TIMES: 6,
    Goal.SPACING: 3,
    Goal.FAMILIES: 6,
    Goal.REPEAT_OPPONENT: 1,
    Goal.TRAVEL: 1,
    Goal.COACH_TIMES: 4,
}
REMATCH_GAP_DAYS = 14
FAMILY_BUFFER = timedelta(minutes=30)  # time to get from one kid's game to the other's
AWAY_FROM_HOME_COST = 3  # when venues have no location: one home game played elsewhere


def weights(priorities: Sequence[Goal]) -> dict[Goal, int]:
    """Top-ranked goal weighs 16, then 8, 4, 2, 1. Goals left out of the list are off."""
    n = len(priorities)
    return {g: 2 ** (n - 1 - i) for i, g in enumerate(priorities)}


def km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 6371 * 2 * math.asin(math.sqrt(h))


class GoalBuilder:
    def __init__(self, b: ModelBuilder) -> None:
        self.b = b
        self.m = b.m
        self.spot = {s.key: s for s in b.spots}
        self.games = {g.id: g for g in b.games}
        # (team, spot) -> vars of that team's games at that spot
        self.team_spot: dict[tuple[str, int], list[cp_model.IntVar]] = defaultdict(list)
        for (gid, k), v in b.x.items():
            for t in self.games[gid].team_ids:
                self.team_spot[(t, k)].append(v)
        self.spots_of_team: dict[str, list[int]] = defaultdict(list)
        for t, k in self.team_spot:
            self.spots_of_team[t].append(k)
        self.var_game: dict[int, str] = {v.index: gid for (gid, _), v in b.x.items()}
        self._sums: dict[tuple[int, ...], cp_model.IntVar] = {}
        self.parts: dict[Goal, Expr] = {}

    def team_count(self, team: str, keys: Sequence[int]) -> Expr:
        return total(v for k in keys for v in self.team_spot[(team, k)])

    # ── goals ──

    def fair_times(self) -> Expr:
        ix = self.b.ix
        terms: list[Expr] = []
        by_div: dict[str, list[str]] = defaultdict(list)
        for team in ix.league.teams:
            by_div[team.division_id].append(team.id)
        for teams in by_div.values():
            counts = []
            for t in teams:
                r = ix.team_rules(t)
                bad = [
                    k
                    for k in self.spots_of_team[t]
                    if self.spot[k].start.time() < r.early_before
                    or self.spot[k].start.time() >= r.late_from
                ]
                counts.append(self.team_count(t, bad))
            if len(counts) < 2:
                continue
            hi = self.m.new_int_var(0, 100, "bad_hi")
            lo = self.m.new_int_var(0, 100, "bad_lo")
            for c in counts:
                self.m.add(hi >= c)
                self.m.add(lo <= c)
            terms.append(hi - lo)
        return total(terms)

    def spacing(self) -> Expr:
        ix = self.b.ix
        lg = ix.league
        weeks = max(1, math.ceil(((lg.season_end - lg.season_start).days + 1) / 7))
        terms: list[Expr] = []
        for t in ix.teams:
            by_day: dict[date, list[int]] = defaultdict(list)
            by_week: dict[int, list[int]] = defaultdict(list)
            for k in self.spots_of_team[t]:
                d = self.spot[k].day
                by_day[d].append(k)
                by_week[(d - lg.season_start).days // 7].append(k)
            for d, ks in by_day.items():
                nxt = by_day.get(d + timedelta(days=1))
                if nxt:
                    s = self.m.new_int_var(0, 2, "b2b")
                    self.m.add(s >= self.team_count(t, ks) + self.team_count(t, nxt) - 1)
                    terms.append(s)
            games = sum(1 for g in self.b.games if t in g.team_ids)
            cap = max(1, math.ceil(games / weeks))
            for ks in by_week.values():
                s = self.m.new_int_var(0, 7, "week")
                self.m.add(s >= self.team_count(t, ks) - cap)
                terms.append(s)
        terms.append(self.round_alignment())
        return total(terms)

    def round_alignment(self) -> Expr:
        """Each game near its target week (round r of a round robin aims at the r-th usable
        week), so teams play about once a week and rematches land far apart. Cost: weeks
        off target."""
        terms: list[Expr] = []
        for gid, target in self.b.target_week.items():
            off = [
                abs(self.b.week(s) - target) * self.b.x[(gid, s.key)]
                for s in self.b.cands[gid]
                if self.b.week(s) != target
            ]
            if off:
                terms.append(total(off))
        return total(terms)

    def families(self) -> Expr:
        terms: list[Expr] = []
        for fam in self.b.ix.league.families:
            for a, c in combinations(sorted(set(fam.team_ids)), 2):
                # Games where the two teams play each other put both kids at the same
                # game, so they never count as a clash.
                items: list[tuple[datetime, datetime, Expr, str]] = []
                for team, other in ((a, c), (c, a)):
                    for k in self.spots_of_team[team]:
                        vs = [
                            v
                            for v in self.team_spot[(team, k)]
                            if other not in self.games[self.var_game[v.index]].team_ids
                        ]
                        if not vs:
                            continue
                        s = self.spot[k]
                        busy = vs[0] if len(vs) == 1 else self._sum_var(vs)
                        items.append((s.start, s.end + FAMILY_BUFFER, busy, team))
                items.sort(key=lambda it: it[0])
                active: list[tuple[datetime, datetime, Expr, str]] = []
                i = 0
                while i < len(items):
                    t0 = items[i][0]
                    while i < len(items) and items[i][0] == t0:
                        active.append(items[i])
                        i += 1
                    active = [x for x in active if x[1] > t0]
                    ea = [x[2] for x in active if x[3] == a]
                    ec = [x[2] for x in active if x[3] == c]
                    if ea and ec:
                        clash = self.m.new_bool_var("clash")
                        self.m.add(clash >= total(ea) + total(ec) - 1)
                        terms.append(clash)
        return total(terms)

    def _sum_var(self, vs: list[cp_model.IntVar]) -> cp_model.IntVar:
        key = tuple(sorted(v.index for v in vs))
        if key not in self._sums:
            v = self.m.new_bool_var("any")
            self.m.add(v == total(vs))
            self._sums[key] = v
        return self._sums[key]

    def repeat_opponent(self) -> Expr:
        lg = self.b.ix.league
        by_pair: dict[frozenset[str], list[str]] = defaultdict(list)
        for g in self.b.games:
            if g.away_team_id is not None:
                by_pair[frozenset(g.team_ids)].append(g.id)
        cands = self.b.cands
        terms: list[Expr] = []
        horizon = (lg.season_end - lg.season_start).days + 1
        day_of: dict[str, Expr] = {}
        for gids in by_pair.values():
            if len(gids) < 2:
                continue
            for gid in gids:
                if gid not in day_of:
                    day_of[gid] = total(
                        (s.day - lg.season_start).days * self.b.x[(gid, s.key)] for s in cands[gid]
                    )
            for g1, g2 in combinations(gids, 2):
                diff = self.m.new_int_var(-horizon, horizon, "dd")
                self.m.add(diff == day_of[g1] - day_of[g2])
                gap = self.m.new_int_var(0, horizon, "gap")
                self.m.add_abs_equality(gap, diff)
                short = self.m.new_int_var(0, REMATCH_GAP_DAYS, "short")
                self.m.add(short >= REMATCH_GAP_DAYS - gap)
                # Only counts when both games are placed (unplaced games read as day 0).
                both = self.m.new_bool_var("both")
                self.m.add(both <= self.b.placed[g1])
                self.m.add(both <= self.b.placed[g2])
                self.m.add(both >= self.b.placed[g1] + self.b.placed[g2] - 1)
                counted = self.m.new_int_var(0, REMATCH_GAP_DAYS, "counted")
                self.m.add(counted >= short - REMATCH_GAP_DAYS * (1 - both))
                terms.append(counted)
        return total(terms)

    def travel(self) -> Expr:
        ix = self.b.ix
        coords: dict[str, tuple[float, float]] = {
            v.id: (v.latitude, v.longitude)
            for v in ix.league.venues
            if v.latitude is not None and v.longitude is not None
        }
        terms: list[Expr] = []
        for (gid, k), v in self.b.x.items():
            g, s = self.games[gid], self.spot[k]
            cost = 0
            for t in g.team_ids:
                home = ix.teams[t].home_venue_id
                if home is None or home == s.venue_id:
                    continue
                if home in coords and s.venue_id in coords:
                    cost += round(km(coords[home], coords[s.venue_id]) / 10)
                elif t == g.home_team_id:
                    cost += AWAY_FROM_HOME_COST
            if cost:
                terms.append(cost * v)
        return total(terms)

    def coach_times(self) -> Expr:
        """Games of a coach's teams outside the times that coach prefers."""
        terms: list[Expr] = []
        for c in self.b.ix.league.coaches:
            if not c.prefers:
                continue
            for t in c.team_ids:
                outside = [
                    k
                    for k in self.spots_of_team[t]
                    if not any(p.contains(self.spot[k].start, self.spot[k].end) for p in c.prefers)
                ]
                terms.append(self.team_count(t, outside))
        return total(terms)

    def build(self, priorities: Sequence[Goal]) -> Expr:
        w = weights(priorities)
        builders = {
            Goal.FAIR_TIMES: self.fair_times,
            Goal.SPACING: self.spacing,
            Goal.FAMILIES: self.families,
            Goal.REPEAT_OPPONENT: self.repeat_opponent,
            Goal.TRAVEL: self.travel,
            Goal.COACH_TIMES: self.coach_times,
        }
        parts: list[Expr] = []
        for goal in priorities:
            expr = builders[goal]()
            self.parts[goal] = expr
            parts.append(w[goal] * UNIT[goal] * expr)
        return total(parts)

"""A fast, sensible first draft that the solver starts from.

Walks the season week by week. Round r of each division's round robin aims for the r-th
usable week (then nearby weeks). Within a week the hardest-to-place games go first, and
each takes the legal spot that costs least: home venue preferred, early/late slots shared,
no back-to-back days, no clash with a sibling's game. Every hard rule is respected here
too; the solver and `validate` remain the final word.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

from .goals import FAMILY_BUFFER

if TYPE_CHECKING:
    from .solver import Game, ModelBuilder, Spot


def greedy(b: ModelBuilder) -> dict[str, int]:
    """game id -> spot key for every game it could place."""
    ix, lg = b.ix, b.ix.league
    team_busy: dict[str, list[tuple[datetime, datetime]]] = defaultdict(list)
    coach_busy: dict[str, list[tuple[datetime, datetime]]] = defaultdict(list)
    surface_use: dict[str, list[tuple[datetime, datetime, int]]] = defaultdict(list)
    per_day: Counter[tuple[str, date]] = Counter()
    days_of: dict[str, set[date]] = defaultdict(set)
    bad_count: Counter[str] = Counter()
    coaches_of = {t: [c.id for c in ix.coaches_of_team.get(t, []) if len(c.team_ids) > 1]
                  for t in ix.teams}  # fmt: skip
    siblings: dict[str, set[str]] = defaultdict(set)
    for f in lg.families:
        for t in f.team_ids:
            siblings[t].update(x for x in f.team_ids if x != t)
    rest = {t: timedelta(minutes=ix.team_rules(t).min_rest_minutes) for t in ix.teams}

    def week(s: Spot) -> int:
        return (s.day - lg.season_start).days // 7

    def legal(g: Game, s: Spot) -> bool:
        for t in g.team_ids:
            if per_day[(t, s.day)] >= ix.team_rules(t).max_games_per_day:
                return False
            end = s.end + rest[t]
            if any(a < end and s.start < z for a, z in team_busy[t]):
                return False
            for c in coaches_of.get(t, []):
                if any(a < s.end and s.start < z for a, z in coach_busy[c]):
                    return False
        load = sum(u for a, z, u in surface_use[s.surface_id] if a < s.end and s.start < z)
        return load + s.units <= ix.surfaces[s.surface_id].units

    def cost(g: Game, s: Spot) -> float:
        c = 0.0
        home_venue = ix.teams[g.home_team_id].home_venue_id
        if home_venue and home_venue != s.venue_id:
            c += 3
        for t in g.team_ids:
            r = ix.team_rules(t)
            if s.start.time() < r.early_before or s.start.time() >= r.late_from:
                c += 2 + 2 * bad_count[t]
            if s.day - timedelta(days=1) in days_of[t] or s.day + timedelta(days=1) in days_of[t]:
                c += 6
            for sib in siblings.get(t, ()):
                if sib in g.team_ids:
                    continue
                if any(a < s.end + FAMILY_BUFFER and s.start < z + FAMILY_BUFFER
                       for a, z in team_busy[sib]):  # fmt: skip
                    c += 8
        return c + s.start.hour / 100  # mild preference for earlier in the day (stable)

    def take(g: Game, s: Spot) -> None:
        for t in g.team_ids:
            team_busy[t].append((s.start, s.end + rest[t]))
            per_day[(t, s.day)] += 1
            days_of[t].add(s.day)
            r = ix.team_rules(t)
            if s.start.time() < r.early_before or s.start.time() >= r.late_from:
                bad_count[t] += 1
            for c in coaches_of.get(t, []):
                coach_busy[c].append((s.start, s.end))
        surface_use[s.surface_id].append((s.start, s.end, s.units))

    # Target week per game, from its round.
    target: dict[str, int] = {}
    by_div: dict[str, list[Game]] = defaultdict(list)
    for g in b.games:
        if g.fixed is None and g.matchup is not None:
            by_div[g.division_id].append(g)
    for games in by_div.values():
        weeks = sorted({week(s) for g in games for s in b.cands[g.id]})
        if not weeks:
            continue
        rounds = max(g.matchup.round for g in games if g.matchup) + 1
        for g in games:
            assert g.matchup is not None
            target[g.id] = weeks[min(len(weeks) - 1, g.matchup.round * len(weeks) // rounds)]

    for g in b.games:  # fixed events are already in place
        if g.fixed is not None:
            take(g, b.cands[g.id][0])

    chosen: dict[str, int] = {}
    pending = [g for g in b.games if g.fixed is None and g.id in target]
    max_week = max((week(s) for s in b.spots), default=0)
    for radius in range(max_week + 1):
        # Hardest first: fewest candidate spots in the weeks we're trying now.
        def near(g: Game, s: Spot, r: int = radius) -> bool:
            return abs(week(s) - target[g.id]) == r

        pending.sort(key=lambda g: sum(1 for s in b.cands[g.id] if near(g, s)))
        left = []
        for g in pending:
            options = [s for s in b.cands[g.id] if near(g, s) and legal(g, s)]
            if not options:
                left.append(g)
                continue
            best = min(options, key=lambda s: cost(g, s))
            take(g, best)
            chosen[g.id] = best.key
        pending = left
        if not pending:
            break
    return chosen

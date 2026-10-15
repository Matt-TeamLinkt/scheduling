"""Stage 2: place matchups into the league's time slots with OR-Tools CP-SAT.

Model (see docs/ENGINE.md for the full write-up):
  x[g, s] = 1 if game g starts at spot s. A spot is a concrete (slot, start, length,
  size) a game could occupy. Spots are pre-filtered per team with the same per-event
  checks `validate` uses (time window, blackouts, slot fit, season), so the solver and
  the checker can't disagree about what's legal.

  Hard: each game at most one spot (fixed games exactly one); surface capacity, team
  overlap + rest, coach overlap, all as "at any moment" sweeps; games per day.
  Solved in two phases: first fit as many games as possible (stopping as soon as all
  fit), then keep that many and make the schedule as fair as the time allows. So the
  solver always returns its best schedule plus a list of games that didn't fit, never a
  bare "no", and fairness never costs a game.
"""

from __future__ import annotations

import time as clock
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import StrEnum

from ortools.sat.python import cp_model

from .cp import Expr, total
from .goals import DEFAULT_PRIORITIES, Goal, GoalBuilder
from .greedy import greedy
from .index import LeagueIndex
from .matchups import Matchup, make_matchups
from .model import Event, EventKind, League
from .validate import _check_blackouts, _check_slot_and_season, _check_time_window

KEEP_DRAFT_WEIGHT = 10_000  # placing a game always beats keeping a draft spot
PLACING_SHARE = 0.6  # at most this share of the time limit goes to fitting games in


@dataclass(frozen=True)
class Spot:
    key: int
    slot_id: str
    surface_id: str
    venue_id: str
    start: datetime
    minutes: int
    units: int

    @property
    def end(self) -> datetime:
        return self.start + timedelta(minutes=self.minutes)

    @property
    def day(self) -> date:
        return self.start.date()


class Status(StrEnum):
    BEST = "best"  # proven best possible for the chosen priorities
    GOOD = "good"  # a valid schedule; time ran out before proving it's the best
    NO_SCHEDULE = "no_schedule"  # couldn't build a valid schedule at all


class Phase(StrEnum):
    PLACING = "placing"  # "Fitting games into your time slots…"
    IMPROVING = "improving"  # "Making the schedule fairer…"


@dataclass(frozen=True)
class Progress:
    seconds: float
    placed: int
    total: int
    phase: Phase


@dataclass
class SolveOptions:
    priorities: Sequence[Goal] = DEFAULT_PRIORITIES
    time_limit_s: float = 60.0
    workers: int = 8
    seed: int = 0
    on_progress: Callable[[Progress], None] | None = None


@dataclass
class SolveResult:
    status: Status
    events: list[Event]
    unplaced: list[Matchup]
    seconds: float
    notes: list[str] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)
    goal_scores: dict[Goal, int] = field(default_factory=dict)  # lower is better


@dataclass
class Game:
    """A matchup to place, or an existing event that must stay where it is."""

    id: str
    division_id: str
    team_ids: tuple[str, ...]
    home_team_id: str
    away_team_id: str | None
    minutes: int
    units: int | None  # None = the whole surface
    fixed: Event | None = None
    matchup: Matchup | None = None
    window: tuple[date, date] | None = None  # only place inside these dates (inclusive)
    target_week: int | None = None  # aim for this week (default: from its round)


class ModelBuilder:
    def __init__(self, league: League, games: Sequence[Game]) -> None:
        self.lg = league
        self.ix = LeagueIndex(league)
        self.games = list(games)
        self.m = cp_model.CpModel()
        self.spots: list[Spot] = []
        self._spot_ids: dict[tuple[str, datetime, int, int], Spot] = {}
        self.x: dict[tuple[str, int], cp_model.IntVar] = {}
        self.placed: dict[str, Expr] = {}
        self.cands: dict[str, list[Spot]] = {}
        self.target_week: dict[str, int] = {}

    # ── spots ──

    def spot(self, slot_id: str, start: datetime, minutes: int, units: int) -> Spot:
        k = (slot_id, start, minutes, units)
        s = self._spot_ids.get(k)
        if s is None:
            surface = self.ix.surfaces[self.ix.slots[slot_id].surface_id]
            s = Spot(len(self.spots), slot_id, surface.id, surface.venue_id, start, minutes, units)
            self.spots.append(s)
            self._spot_ids[k] = s
        return s

    def _starts(self, slot_id: str, minutes: int) -> Iterable[datetime]:
        """Back-to-back starts inside a slot: a 120-minute slot holds two 60-minute games."""
        slot = self.ix.slots[slot_id]
        t = slot.start_dt
        while t + timedelta(minutes=minutes) <= slot.end_dt:
            yield t
            t += timedelta(minutes=minutes)

    def _team_ok(self, team_id: str, division_id: str, s: Spot) -> bool:
        probe = Event(
            id="probe",
            kind=EventKind.PRACTICE,
            division_id=division_id,
            home_team_id=team_id,
            slot_id=s.slot_id,
            start=s.start,
            minutes=s.minutes,
            units=s.units,
        )
        return not (
            any(_check_slot_and_season(self.ix, probe))
            or any(_check_time_window(self.ix, probe))
            or any(_check_blackouts(self.ix, probe))
        )

    def build_candidates(self) -> None:
        cache: dict[tuple[str, int], bool] = {}
        by_shape: dict[tuple[int, int | None], list[Spot]] = {}
        for g in self.games:
            if g.fixed is not None:
                e = g.fixed
                self.cands[g.id] = [self.spot(e.slot_id, e.start, e.minutes, e.units)]
                continue
            shape = (g.minutes, g.units)
            if shape not in by_shape:
                spots = []
                for slot in self.lg.slots:
                    if slot.surface_id not in self.ix.surfaces:
                        continue
                    units = g.units or self.ix.surfaces[slot.surface_id].units
                    for start in self._starts(slot.id, g.minutes):
                        spots.append(self.spot(slot.id, start, g.minutes, units))
                by_shape[shape] = spots
            ok = []
            for s in by_shape[shape]:
                if g.window and not g.window[0] <= s.day <= g.window[1]:
                    continue
                fits = True
                for t in g.team_ids:
                    k = (t, s.key)
                    if k not in cache:
                        cache[k] = self._team_ok(t, g.division_id, s)
                    if not cache[k]:
                        fits = False
                        break
                if fits:
                    ok.append(s)
            self.cands[g.id] = ok
        self._set_target_weeks()

    def week(self, s: Spot) -> int:
        return (s.day - self.lg.season_start).days // 7

    def _set_target_weeks(self) -> None:
        """Where each game should land: its own target if given (a rescheduled game aims
        for its current week), else round r of its division at the r-th usable week."""
        by_div: dict[str, list[Game]] = defaultdict(list)
        for g in self.games:
            if g.fixed is not None:
                continue
            if g.target_week is not None:
                self.target_week[g.id] = g.target_week
            elif g.matchup is not None:
                by_div[g.division_id].append(g)
        for games in by_div.values():
            weeks = sorted({self.week(s) for g in games for s in self.cands[g.id]})
            if not weeks:
                continue
            rounds = max(g.matchup.round for g in games if g.matchup) + 1
            for g in games:
                assert g.matchup is not None
                i = min(len(weeks) - 1, g.matchup.round * len(weeks) // rounds)
                self.target_week[g.id] = weeks[i]

    # ── variables and hard constraints ──

    def build_hard(self) -> None:
        m = self.m
        for g in self.games:
            vs = []
            for s in self.cands[g.id]:
                v = m.new_bool_var(f"x[{g.id},{s.key}]")
                self.x[(g.id, s.key)] = v
                vs.append(v)
            if g.fixed is not None:
                m.add(total(vs) == 1)
            else:
                m.add(total(vs) <= 1)
            self.placed[g.id] = total(vs)

        spot_by_key = {s.key: s for s in self.spots}
        games = {g.id: g for g in self.games}

        # Surface capacity at every moment.
        by_surface: dict[str, list[tuple[datetime, datetime, int, cp_model.IntVar]]] = defaultdict(
            list
        )
        for (_gid, k), v in self.x.items():
            s = spot_by_key[k]
            by_surface[s.surface_id].append((s.start, s.end, s.units, v))
        for sid, items in by_surface.items():
            cap = self.ix.surfaces[sid].units
            for active in _sweep(items):
                if sum(u for _, _, u, _ in active) > cap:
                    m.add(total(u * v for _, _, u, v in active) <= cap)

        # Teams: no overlap, including the rest they need after each game.
        by_team: dict[str, list[tuple[datetime, datetime, int, cp_model.IntVar]]] = defaultdict(
            list
        )
        per_day: dict[tuple[str, date], list[cp_model.IntVar]] = defaultdict(list)
        for (gid, k), v in self.x.items():
            s, g = spot_by_key[k], games[gid]
            for t in g.team_ids:
                rest = timedelta(minutes=self.ix.team_rules(t).min_rest_minutes)
                by_team[t].append((s.start, s.end + rest, 1, v))
                if g.away_team_id is not None:
                    per_day[(t, s.day)].append(v)
        for items in by_team.values():
            for active in _sweep(items):
                if len(active) > 1:
                    m.add_at_most_one(v for *_, v in active)
        for (t, _), vs in per_day.items():
            limit = self.ix.team_rules(t).max_games_per_day
            if len(vs) > limit:
                m.add(total(vs) <= limit)

        # Coaches: no overlap across all their teams' games.
        for coach in self.lg.coaches:
            if len(coach.team_ids) < 2:
                continue
            teams = set(coach.team_ids)
            items = [
                (spot_by_key[k].start, spot_by_key[k].end, 1, v)
                for (gid, k), v in self.x.items()
                if teams & set(games[gid].team_ids)
            ]
            for active in _sweep(items):
                if len(active) > 1:
                    m.add_at_most_one(v for *_, v in active)

    def team_capacity(self) -> dict[str, tuple[int, int]]:
        """team -> (games it needs, most it could possibly play). A team plays at most
        max_games_per_day on each day it has any legal spot (less any games already fixed
        on that day), so that's a hard ceiling."""
        days: dict[str, set[date]] = defaultdict(set)
        need: Counter[str] = Counter()
        taken: Counter[tuple[str, date]] = Counter()
        for g in self.games:
            if g.fixed is not None:
                if g.away_team_id is not None:
                    for t in g.team_ids:
                        taken[(t, g.fixed.start.date())] += 1
                continue
            for t in g.team_ids:
                need[t] += 1
                days[t].update(s.day for s in self.cands[g.id])
        out = {}
        for t, n in need.items():
            per_day = self.ix.team_rules(t).max_games_per_day
            out[t] = (n, sum(max(0, per_day - taken[(t, d)]) for d in days[t]))
        return out

    def placed_upper_bound(self) -> int:
        """No schedule can place more free games than this (cheap, often exact)."""
        free = [g for g in self.games if g.fixed is None]
        possible = sum(1 for g in free if self.cands[g.id])
        team_slots = sum(min(n, cap) for n, cap in self.team_capacity().values())
        two_team = sum(1 for g in free if g.away_team_id is not None)
        one_team = len(free) - two_team
        return min(possible, (team_slots - one_team) // 2 + one_team)

    def objective_placed(self) -> Expr:
        return total(self.placed[g.id] for g in self.games if g.fixed is None)


def _sweep(
    items: list[tuple[datetime, datetime, int, cp_model.IntVar]],
) -> Iterable[list[tuple[datetime, datetime, int, cp_model.IntVar]]]:
    """For each distinct start time, everything in progress at that moment. A peak in
    overlap always happens at some start, so checking starts is enough."""
    items = sorted(items, key=lambda it: it[0])
    active: list[tuple[datetime, datetime, int, cp_model.IntVar]] = []
    i = 0
    while i < len(items):
        t = items[i][0]
        while i < len(items) and items[i][0] == t:
            active.append(items[i])
            i += 1
        active = [a for a in active if a[1] > t]
        yield list(active)


def games_for(league: League, matchups: Sequence[Matchup]) -> list[Game]:
    ix = LeagueIndex(league)
    out = []
    for mu in matchups:
        rules = [ix.team_rules(t) for t in mu.team_ids]
        units = [r.units for r in rules]
        out.append(
            Game(
                id=mu.id,
                division_id=mu.division_id,
                team_ids=mu.team_ids,
                home_team_id=mu.home_team_id,
                away_team_id=mu.away_team_id,
                minutes=max(r.game_minutes for r in rules),
                units=None if None in units else max(u for u in units if u is not None),
                matchup=mu,
            )
        )
    return out


class _Watcher(cp_model.CpSolverSolutionCallback):
    """Reports progress; in the placing phase, stops as soon as every game is placed."""

    def __init__(
        self,
        placed: Expr,
        goal: int,
        phase: Phase,
        t0: float,
        cb: Callable[[Progress], None] | None,
        stop_when_all: bool,
    ) -> None:
        super().__init__()
        self.placed, self.goal, self.phase, self.t0, self.cb = placed, goal, phase, t0, cb
        self.stop_when_all = stop_when_all

    def on_solution_callback(self) -> None:
        placed = int(self.value(self.placed))
        if self.cb:
            self.cb(Progress(clock.perf_counter() - self.t0, placed, self.goal, self.phase))
        if self.stop_when_all and placed >= self.goal:
            self.stop_search()


def solve(
    league: League,
    matchups: Sequence[Matchup] | None = None,
    options: SolveOptions | None = None,
) -> SolveResult:
    """Build a schedule for `league` from scratch."""
    notes: list[str] = []
    if matchups is None:
        matchups, mnotes = make_matchups(league)
        notes += [n.message for n in mnotes]
    return run(league, games_for(league, matchups), options or SolveOptions(), notes)


def run(league: League, games: list[Game], opts: SolveOptions, notes: list[str]) -> SolveResult:
    """Two phases: (1) fit as many games as possible, stopping the moment all fit;
    (2) keep that many and spend the remaining time making the schedule fairer."""
    t0 = clock.perf_counter()
    b = ModelBuilder(league, games)
    b.build_candidates()
    b.build_hard()
    placed_expr = b.objective_placed()
    free = sum(1 for g in games if g.fixed is None)
    ceiling = b.placed_upper_bound()
    stats = {
        "games": len(games),
        "spots": len(b.spots),
        "choices": len(b.x),
        "constraints": len(b.m.proto.constraints),
        "most_possible": ceiling,
    }

    def solver_for(seconds: float) -> cp_model.CpSolver:
        sv = cp_model.CpSolver()
        sv.parameters.max_time_in_seconds = max(1.0, seconds)
        sv.parameters.num_workers = opts.workers
        sv.parameters.random_seed = opts.seed
        return sv

    def left() -> float:
        return opts.time_limit_s - (clock.perf_counter() - t0)

    # Phase 0: a quick greedy draft. If it already fits every game that can fit, the
    # solver only has to make it fairer; otherwise it's phase 1's starting point.
    draft = greedy(b)
    draft_values = {(gid, k): draft.get(gid) == k for (gid, k) in b.x}
    for g in games:
        if g.fixed is not None:
            for fixed_spot in b.cands[g.id]:
                draft_values[(g.id, fixed_spot.key)] = True
    stats["draft_placed"] = len(draft)
    if len(draft) >= ceiling:
        code, best_placed, values = cp_model.FEASIBLE, len(draft), draft_values
        if opts.on_progress:
            opts.on_progress(
                Progress(clock.perf_counter() - t0, best_placed, ceiling, Phase.PLACING)
            )
    else:
        # Phase 1: place as many games as possible.
        for k, v in b.x.items():
            b.m.add_hint(v, draft_values[k])
        # Fit the missing games while moving as little of the draft as possible.
        keep = total(v for k, v in b.x.items() if draft_values[k])
        b.m.maximize(KEEP_DRAFT_WEIGHT * placed_expr + keep)
        sv1 = solver_for(left() * PLACING_SHARE)
        code = sv1.solve(
            b.m, _Watcher(placed_expr, ceiling, Phase.PLACING, t0, opts.on_progress, True)
        )
        if code not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return SolveResult(
                Status.NO_SCHEDULE,
                [],
                [g.matchup for g in games if g.matchup],
                clock.perf_counter() - t0,
                notes,
                stats,
            )
        best_placed = int(sv1.value(placed_expr))
        values = {k: sv1.boolean_value(v) for k, v in b.x.items()}
    proven = code == cp_model.OPTIMAL or best_placed >= ceiling

    # Phase 2: same number of games, as fair as possible.
    final_code = code
    scores: dict[Goal, int] = {}
    # Goals are added only now: they'd slow down the search for a complete schedule.
    goals = GoalBuilder(b)
    penalty = goals.build(opts.priorities)
    if left() > 1 and opts.priorities:
        b.m.add(placed_expr >= best_placed)
        b.m.clear_hints()  # type: ignore[no-untyped-call]
        for k, v in b.x.items():
            b.m.add_hint(v, values[k])
        b.m.minimize(penalty)
        sv2 = solver_for(left())
        code2 = sv2.solve(
            b.m, _Watcher(placed_expr, free, Phase.IMPROVING, t0, opts.on_progress, False)
        )
        if code2 in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            values = {k: sv2.boolean_value(v) for k, v in b.x.items()}
            final_code = code2
            scores = {g: int(sv2.value(e)) for g, e in goals.parts.items()}

    spot_by_key = {s.key: s for s in b.spots}
    chosen = {gid: spot_by_key[k] for (gid, k), on in values.items() if on}
    events: list[Event] = []
    unplaced: list[Matchup] = []
    for g in games:
        sp = chosen.get(g.id)
        if sp is None:
            if g.matchup is not None:
                unplaced.append(g.matchup)
            continue
        events.append(
            g.fixed
            if g.fixed is not None
            else Event(
                id=g.id,
                kind=EventKind.GAME if g.away_team_id else EventKind.PRACTICE,
                division_id=g.division_id,
                home_team_id=g.home_team_id,
                away_team_id=g.away_team_id,
                slot_id=sp.slot_id,
                start=sp.start,
                minutes=sp.minutes,
                units=sp.units,
            )
        )
    events.sort(key=lambda e: (e.start, e.slot_id, e.id))
    status = Status.BEST if final_code == cp_model.OPTIMAL and proven else Status.GOOD
    return SolveResult(status, events, unplaced, clock.perf_counter() - t0, notes, stats, scores)

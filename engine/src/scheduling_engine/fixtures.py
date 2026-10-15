"""Realistic test leagues, generated deterministically.

    small_8    one soccer division, two parks, Saturdays only. The "first-time user" case.
    league_40  hockey: 4 divisions / 40 teams, 3 arenas, U9 on half ice, shared coaches,
               siblings, holiday + tournament + venue blackouts. The typical case.
    nightmare  same 40 teams with ~10% spare ice, many shared coaches (one on 3 teams),
               lots of siblings and team blackouts, tight time windows. Intended to be
               feasible but hard; Phase 2 verifies that.

Regenerate the JSON snapshots with:  uv run python -m scheduling_engine.fixtures ../fixtures
"""

from __future__ import annotations

import random
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, time, timedelta
from pathlib import Path

from .model import (
    Blackout,
    BlackoutScope,
    Coach,
    Division,
    Family,
    League,
    RuleOverrides,
    Rules,
    Slot,
    Sport,
    Surface,
    Team,
    Venue,
)

MON, TUE, WED, THU, FRI, SAT, SUN = range(7)

FIRST_NAMES = [
    "Alex",
    "Sam",
    "Jordan",
    "Priya",
    "Chris",
    "Taylor",
    "Morgan",
    "Jamie",
    "Casey",
    "Riley",
    "Avery",
    "Quinn",
    "Dana",
    "Robin",
    "Kai",
    "Noor",
    "Mateo",
    "Sofia",
    "Liam",
    "Aisha",
    "Ethan",
    "Mei",
    "Omar",
    "Grace",
    "Lucas",
    "Zoe",
    "Ravi",
    "Hannah",
    "Diego",
    "Fatima",
    "Owen",
    "Chloe",
    "Yusuf",
    "Emma",
    "Ben",
    "Lena",
    "Arjun",
    "Maya",
    "Theo",
    "Ines",
]
LAST_NAMES = [
    "Ramsey",
    "Diaz",
    "Lee",
    "Nair",
    "Okafor",
    "Kowalski",
    "Tremblay",
    "Nguyen",
    "Singh",
    "MacLeod",
    "Rossi",
    "Haddad",
    "Kim",
    "Fraser",
    "Bouchard",
    "Patel",
    "Murphy",
    "Chen",
    "Wilson",
    "Gagnon",
    "Ali",
    "Schmidt",
    "Lopez",
    "Campbell",
    "Roy",
    "Martin",
    "Brown",
    "Hughes",
    "Ivanova",
    "Park",
]


@dataclass(frozen=True)
class SlotPattern:
    """'Every Tuesday 17:00–21:00, 60-minute slots' on one surface."""

    surface_id: str
    weekdays: tuple[int, ...]
    first: time
    last_end: time
    minutes: int


def _slots(pattern: SlotPattern, start: date, end: date, counter: list[int]) -> Iterable[Slot]:
    day = start
    while day <= end:
        if day.weekday() in pattern.weekdays:
            t = pattern.first.hour * 60 + pattern.first.minute
            stop = pattern.last_end.hour * 60 + pattern.last_end.minute
            while t + pattern.minutes <= stop:
                counter[0] += 1
                yield Slot(
                    id=f"sl-{counter[0]:04d}",
                    surface_id=pattern.surface_id,
                    date=day,
                    start=time(t // 60, t % 60),
                    end=time((t + pattern.minutes) // 60, (t + pattern.minutes) % 60),
                )
                t += pattern.minutes
        day += timedelta(days=1)


def _build_slots(patterns: list[SlotPattern], start: date, end: date) -> list[Slot]:
    counter = [0]
    return [s for p in patterns for s in _slots(p, start, end, counter)]


def _person(rng: random.Random, used: set[str]) -> str:
    while True:
        name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        if name not in used:
            used.add(name)
            return name


def _coaches(
    rng: random.Random, teams: list[Team], shared: Sequence[tuple[str, ...]]
) -> list[Coach]:
    """One head coach per team, except the given groups which share one coach."""
    used: set[str] = set()
    covered = {t for group in shared for t in group}
    groups = list(shared) + [(t.id,) for t in teams if t.id not in covered]
    groups.sort(key=lambda g: g[0])
    return [
        Coach(id=f"c-{i:02d}", name=_person(rng, used), team_ids=list(g))
        for i, g in enumerate(groups, 1)
    ]


def _families(rng: random.Random, teams: list[Team], n: int, triples: int = 0) -> list[Family]:
    """Households with kids in different divisions (siblings are different ages)."""
    by_div: dict[str, list[str]] = {}
    for t in teams:
        by_div.setdefault(t.division_id, []).append(t.id)
    divs = sorted(by_div)
    out: list[Family] = []
    used: set[str] = set()
    for i in range(1, n + 1):
        k = 3 if i <= triples and len(divs) >= 3 else 2
        picked = rng.sample(divs, k)
        team_ids = sorted(rng.choice(by_div[d]) for d in picked)
        surname = _person(rng, used).split()[1]
        out.append(Family(id=f"f-{i:02d}", name=surname, team_ids=team_ids))
    return out


# ── small_8 ─────────────────────────────────────────────────────────────────


def small_8() -> League:
    rng = random.Random(8)
    start, end = date(2027, 4, 10), date(2027, 6, 13)
    clubs = ["Falcons", "Rovers", "Comets", "Strikers", "Titans", "Wolves", "Rangers", "Kings"]
    teams = [
        Team(
            id=f"t-{i:02d}",
            name=c,
            division_id="d-u10",
            home_venue_id="v-maple" if i <= 4 else "v-river",
        )
        for i, c in enumerate(clubs, 1)
    ]
    patterns = [
        SlotPattern("s-maple-1", (SAT,), time(9), time(15), 60),
        SlotPattern("s-river-a", (SAT,), time(9), time(15), 60),
    ]
    return League(
        id="small_8",
        name="Maple Valley Soccer · U10 Spring",
        sport=Sport.SOCCER,
        season_start=start,
        season_end=end,
        rules=Rules(games_per_team=7, game_minutes=60, latest_end=time(18)),
        divisions=[Division(id="d-u10", name="U10")],
        teams=teams,
        coaches=_coaches(rng, teams, shared=[("t-01", "t-05")]),
        families=[
            Family(id="f-01", name="Nguyen", team_ids=["t-02", "t-06"]),
            Family(id="f-02", name="Okafor", team_ids=["t-03", "t-07"]),
        ],
        venues=[
            Venue(id="v-maple", name="Maple Park"),
            Venue(id="v-river", name="Riverside Fields"),
        ],
        surfaces=[
            Surface(id="s-maple-1", venue_id="v-maple", name="Field 1", units=2, lit=False),
            Surface(id="s-river-a", venue_id="v-river", name="Field A", units=2, lit=False),
        ],
        slots=_build_slots(patterns, start, end),
        blackouts=[
            Blackout(
                id="b-01",
                scope=BlackoutScope.LEAGUE,
                start_date=date(2027, 5, 29),
                end_date=date(2027, 5, 30),
                note="Long weekend",
            )
        ],
    )


# ── hockey leagues ──────────────────────────────────────────────────────────

HOCKEY_CLUBS = [
    ("North Stars", "v-north"),
    ("Riverside Rapids", "v-river"),
    ("Eastside Eagles", "v-east"),
    ("Westwood Wolves", "v-north"),
    ("Lakeshore Lynx", "v-river"),
    ("Hillcrest Hawks", "v-east"),
]
HOCKEY_SIZES = {"d-u9": 8, "d-u11": 10, "d-u13": 10, "d-u15": 12}
COLORS = ["Blue", "Red", "White", "Black", "Gold", "Green"]


def _hockey_teams() -> list[Team]:
    teams: list[Team] = []
    for div, size in HOCKEY_SIZES.items():
        label = div.removeprefix("d-").upper()
        for i in range(size):
            club, venue = HOCKEY_CLUBS[i % len(HOCKEY_CLUBS)]
            color = COLORS[i // len(HOCKEY_CLUBS)]
            teams.append(
                Team(
                    id=f"t-{div.removeprefix('d-')}-{i + 1:02d}",
                    name=f"{club} {label} {color}",
                    division_id=div,
                    home_venue_id=venue,
                )
            )
    return teams


def _hockey_venues() -> tuple[list[Venue], list[Surface]]:
    venues = [
        Venue(id="v-north", name="North Arena", latitude=43.80, longitude=-79.42),
        Venue(id="v-river", name="Riverside Arena", latitude=43.70, longitude=-79.35),
        Venue(id="v-east", name="Eastside Community Centre", latitude=43.72, longitude=-79.20),
    ]
    surfaces = [
        Surface(id="s-north-1", venue_id="v-north", name="Rink 1", units=2),
        Surface(id="s-north-2", venue_id="v-north", name="Rink 2", units=2),
        Surface(id="s-river", venue_id="v-river", name="Main Rink", units=2),
        Surface(id="s-east", venue_id="v-east", name="Rink", units=2),
    ]
    return venues, surfaces


HOCKEY_START, HOCKEY_END = date(2027, 1, 4), date(2027, 3, 28)  # 12 weeks, Mon–Sun


def league_40() -> League:
    rng = random.Random(40)
    teams = _hockey_teams()
    venues, surfaces = _hockey_venues()
    patterns = [
        # North: Saturday mornings on both rinks, 75-minute slots (fits every division).
        SlotPattern("s-north-1", (SAT,), time(7), time(13, 15), 75),
        SlotPattern("s-north-2", (SAT,), time(7), time(13, 15), 75),
        SlotPattern("s-north-1", (SUN,), time(7), time(10, 45), 75),
        # Riverside: two weeknights and Sunday mornings, 60-minute slots.
        SlotPattern("s-river", (TUE, THU), time(17), time(21), 60),
        SlotPattern("s-river", (SUN,), time(8), time(14), 60),
        # Eastside: Wednesday evening and Saturday afternoon.
        SlotPattern("s-east", (WED,), time(18), time(21), 60),
        SlotPattern("s-east", (SAT,), time(14), time(18), 60),
    ]
    shared = [
        ("t-u9-01", "t-u13-04"),
        ("t-u9-05", "t-u11-02"),
        ("t-u11-07", "t-u15-03"),
        ("t-u13-02", "t-u15-08"),
        ("t-u11-04", "t-u11-09"),  # same division: they play each other, fine
        ("t-u9-08", "t-u15-11"),
    ]
    return League(
        id="league_40",
        name="Metro Minor Hockey · Winter",
        sport=Sport.HOCKEY,
        season_start=HOCKEY_START,
        season_end=HOCKEY_END,
        rules=Rules(games_per_team=12, game_minutes=60, earliest_start=time(7)),
        divisions=[
            Division(
                id="d-u9",
                name="U9",
                rules=RuleOverrides(game_minutes=50, units=1, latest_end=time(19)),
            ),
            Division(id="d-u11", name="U11", rules=RuleOverrides(latest_end=time(20))),
            Division(id="d-u13", name="U13"),
            Division(id="d-u15", name="U15", rules=RuleOverrides(game_minutes=75)),
        ],
        teams=teams,
        coaches=_coaches(rng, teams, shared),
        families=_families(rng, teams, 30, triples=4),
        venues=venues,
        surfaces=surfaces,
        slots=_build_slots(patterns, HOCKEY_START, HOCKEY_END),
        blackouts=[
            Blackout(
                id="b-01",
                scope=BlackoutScope.LEAGUE,
                start_date=date(2027, 2, 13),
                end_date=date(2027, 2, 15),
                note="Family Day weekend",
            ),
            Blackout(
                id="b-02",
                scope=BlackoutScope.VENUE,
                target_id="v-east",
                start_date=date(2027, 3, 6),
                end_date=date(2027, 3, 7),
                note="Community centre event",
            ),
            Blackout(
                id="b-03",
                scope=BlackoutScope.TEAM,
                target_id="t-u13-03",
                start_date=date(2027, 1, 29),
                end_date=date(2027, 1, 31),
                note="Away tournament",
            ),
            Blackout(
                id="b-04",
                scope=BlackoutScope.TEAM,
                target_id="t-u13-06",
                start_date=date(2027, 1, 29),
                end_date=date(2027, 1, 31),
                note="Away tournament",
            ),
            Blackout(
                id="b-05",
                scope=BlackoutScope.DIVISION,
                target_id="d-u15",
                start_date=date(2027, 3, 20),
                end_date=date(2027, 3, 21),
                note="Regional showcase",
            ),
            Blackout(
                id="b-06",
                scope=BlackoutScope.TEAM,
                target_id="t-u11-05",
                start_date=date(2027, 2, 20),
                end_date=date(2027, 2, 20),
                start_time=time(7),
                end_time=time(12),
                note="Team photo morning",
            ),
        ],
    )


def nightmare() -> League:
    rng = random.Random(666)
    teams = _hockey_teams()
    venues, surfaces = _hockey_venues()
    patterns = [
        # Barely enough ice, and 75-minute ice (needed by U15) is scarce.
        SlotPattern("s-north-1", (SAT,), time(7), time(13, 15), 75),
        SlotPattern("s-north-2", (SAT,), time(7), time(9, 30), 75),
        SlotPattern("s-north-2", (SUN,), time(7), time(10, 45), 75),
        SlotPattern("s-river", (TUE,), time(17), time(21), 60),
        SlotPattern("s-river", (SUN,), time(8), time(12), 60),
        SlotPattern("s-east", (WED,), time(18), time(21), 60),
    ]
    # 15 shared-coach groups, one coach on three teams across divisions.
    shared: list[tuple[str, ...]] = [("t-u9-02", "t-u13-02", "t-u15-02")]
    pool = [t.id for t in teams if t.id not in shared[0]]
    rng.shuffle(pool)
    shared += [tuple(sorted(pool[i : i + 2])) for i in range(0, 28, 2)]
    team_blackouts = []
    fridays = [
        date(2027, 1, 22),
        date(2027, 2, 5),
        date(2027, 2, 26),
        date(2027, 3, 12),
    ]
    for i, tid in enumerate(rng.sample([t.id for t in teams], 12), 1):
        fri = fridays[i % len(fridays)]
        team_blackouts.append(
            Blackout(
                id=f"b-t{i:02d}",
                scope=BlackoutScope.TEAM,
                target_id=tid,
                start_date=fri,
                end_date=fri + timedelta(days=2),
                note="Away tournament",
            )
        )
    return League(
        id="nightmare",
        name="Metro Minor Hockey · Winter (tight ice)",
        sport=Sport.HOCKEY,
        season_start=HOCKEY_START,
        season_end=HOCKEY_END,
        rules=Rules(games_per_team=12, game_minutes=60, earliest_start=time(7)),
        divisions=[
            Division(
                id="d-u9",
                name="U9",
                rules=RuleOverrides(game_minutes=50, units=1, latest_end=time(18)),
            ),
            Division(id="d-u11", name="U11", rules=RuleOverrides(latest_end=time(20))),
            Division(id="d-u13", name="U13", rules=RuleOverrides(min_rest_minutes=18 * 60)),
            Division(
                id="d-u15",
                name="U15",
                rules=RuleOverrides(game_minutes=75, min_rest_minutes=18 * 60),
            ),
        ],
        teams=teams,
        coaches=_coaches(rng, teams, shared),
        families=_families(rng, teams, 60, triples=10),
        venues=venues,
        surfaces=surfaces,
        slots=_build_slots(patterns, HOCKEY_START, HOCKEY_END),
        blackouts=[
            Blackout(
                id="b-01",
                scope=BlackoutScope.LEAGUE,
                start_date=date(2027, 2, 13),
                end_date=date(2027, 2, 15),
                note="Family Day weekend",
            ),
            Blackout(
                id="b-02",
                scope=BlackoutScope.SURFACE,
                target_id="s-north-2",
                start_date=date(2027, 3, 13),
                end_date=date(2027, 3, 14),
                note="Rink 2 resurfacing",
            ),
            *team_blackouts,
        ],
    )


ALL = {"small_8": small_8, "league_40": league_40, "nightmare": nightmare}


def write_all(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, build in ALL.items():
        (directory / f"{name}.json").write_text(build().model_dump_json(indent=1) + "\n")


if __name__ == "__main__":
    write_all(Path(sys.argv[1] if len(sys.argv) > 1 else "../fixtures"))

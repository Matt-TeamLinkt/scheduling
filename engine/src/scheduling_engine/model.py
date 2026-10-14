"""League data model.

Everything the engine needs to know about one season of one league. Plain pydantic
models so the same shapes serialize to JSON for fixtures, the API and the web app.

Times are local wall-clock times in the league's timezone (no tz math needed for
scheduling; the timezone matters only when exporting to calendars).
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ── Sports ──────────────────────────────────────────────────────────────────


class Sport(StrEnum):
    HOCKEY = "hockey"
    SOCCER = "soccer"
    BASEBALL = "baseball"
    SOFTBALL = "softball"
    BASKETBALL = "basketball"
    VOLLEYBALL = "volleyball"
    OTHER = "other"


class SportPreset(Model):
    """Sensible defaults per sport, so a new league only has to pick its sport."""

    model_config = ConfigDict(frozen=True)

    surface_label: str  # what we call one playing surface: "rink", "field", ...
    full_units: int  # capacity units of a full surface (2 = can be split in half)
    part_label: str | None  # what one unit is called: "half ice", "half field"
    game_minutes: int


SPORT_PRESETS: dict[Sport, SportPreset] = {
    Sport.HOCKEY: SportPreset(
        surface_label="rink", full_units=2, part_label="half ice", game_minutes=60
    ),
    Sport.SOCCER: SportPreset(
        surface_label="field", full_units=2, part_label="half field", game_minutes=60
    ),
    Sport.BASEBALL: SportPreset(
        surface_label="diamond", full_units=1, part_label=None, game_minutes=120
    ),
    Sport.SOFTBALL: SportPreset(
        surface_label="diamond", full_units=1, part_label=None, game_minutes=90
    ),
    Sport.BASKETBALL: SportPreset(
        surface_label="court", full_units=2, part_label="half court", game_minutes=60
    ),
    Sport.VOLLEYBALL: SportPreset(
        surface_label="court", full_units=1, part_label=None, game_minutes=60
    ),
    Sport.OTHER: SportPreset(surface_label="field", full_units=1, part_label=None, game_minutes=60),
}


# ── Rules ───────────────────────────────────────────────────────────────────


class Rules(Model):
    """Scheduling rules. League defaults work for a typical community league."""

    games_per_team: int = Field(default=10, ge=0)
    game_minutes: int = Field(default=60, gt=0)
    # Capacity units one game uses. None = the whole surface it lands on.
    units: int | None = Field(default=None, gt=0)
    # Minimum gap between the end of one game and the start of the next, same team.
    min_rest_minutes: int = Field(default=0, ge=0)
    max_games_per_day: int = Field(default=1, ge=1)
    # Games must start at or after earliest_start and finish by latest_end.
    earliest_start: time = time(8, 0)
    latest_end: time = time(21, 0)

    @model_validator(mode="after")
    def _window_is_open(self) -> Self:
        if self.earliest_start >= self.latest_end:
            raise ValueError("earliest_start must be before latest_end")
        return self


class RuleOverrides(Model):
    """Per-division or per-team changes. Only fields that are set override."""

    games_per_team: int | None = Field(default=None, ge=0)
    game_minutes: int | None = Field(default=None, gt=0)
    units: int | None = Field(default=None, gt=0)
    min_rest_minutes: int | None = Field(default=None, ge=0)
    max_games_per_day: int | None = Field(default=None, ge=1)
    earliest_start: time | None = None
    latest_end: time | None = None

    def apply_to(self, base: Rules) -> Rules:
        changes = self.model_dump(exclude_none=True)
        # Re-validate the merged result so a bad combination is caught here.
        return Rules.model_validate(base.model_dump() | changes)


# ── People and teams ────────────────────────────────────────────────────────


class Division(Model):
    id: str
    name: str
    rules: RuleOverrides = RuleOverrides()


class Team(Model):
    id: str
    name: str
    division_id: str
    home_venue_id: str | None = None
    rules: RuleOverrides = RuleOverrides()


class Coach(Model):
    id: str
    name: str
    team_ids: list[str] = []
    email: str | None = None
    phone: str | None = None


class Family(Model):
    """A household with kids on one or more teams (for sibling-conflict fairness)."""

    id: str
    name: str
    team_ids: list[str] = []


# ── Facilities ──────────────────────────────────────────────────────────────


class Venue(Model):
    id: str
    name: str
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class Surface(Model):
    """One playable surface at a venue: a rink, field, diamond or court."""

    id: str
    venue_id: str
    name: str
    units: int = Field(default=1, gt=0)  # capacity units, e.g. 2 for a splittable rink
    lit: bool = True


class Slot(Model):
    """A block of time the league has on a surface."""

    id: str
    surface_id: str
    date: date
    start: time
    end: time
    cost: float | None = None

    @model_validator(mode="after")
    def _ends_after_start(self) -> Self:
        if self.end <= self.start:
            raise ValueError("a slot must end after it starts")
        return self

    @property
    def start_dt(self) -> datetime:
        return datetime.combine(self.date, self.start)

    @property
    def end_dt(self) -> datetime:
        return datetime.combine(self.date, self.end)

    @property
    def minutes(self) -> int:
        return int((self.end_dt - self.start_dt).total_seconds() // 60)


class BlackoutScope(StrEnum):
    LEAGUE = "league"
    DIVISION = "division"
    TEAM = "team"
    VENUE = "venue"
    SURFACE = "surface"


class Blackout(Model):
    """Dates (optionally part of a day) when nothing in scope may be scheduled."""

    id: str
    scope: BlackoutScope
    target_id: str | None = None  # the division/team/venue/surface id; None for league
    start_date: date
    end_date: date  # inclusive
    start_time: time | None = None  # both set = only that part of each day
    end_time: time | None = None
    note: str = ""

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if self.end_date < self.start_date:
            raise ValueError("end_date is before start_date")
        if (self.scope == BlackoutScope.LEAGUE) != (self.target_id is None):
            raise ValueError("target_id is required for every scope except league")
        if (self.start_time is None) != (self.end_time is None):
            raise ValueError("set both start_time and end_time, or neither")
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")
        return self

    def covers(self, start: datetime, end: datetime) -> bool:
        """True if the blackout overlaps the interval [start, end)."""
        day = start.date()
        if not self.start_date <= day <= self.end_date:
            return False
        if self.start_time is None or self.end_time is None:
            return True
        return start.time() < self.end_time and self.start_time < end.time()


# ── League ──────────────────────────────────────────────────────────────────


class League(Model):
    id: str
    name: str
    sport: Sport = Sport.OTHER
    timezone: str = "America/Toronto"
    season_start: date
    season_end: date
    rules: Rules = Rules()
    divisions: list[Division] = []
    teams: list[Team] = []
    coaches: list[Coach] = []
    families: list[Family] = []
    venues: list[Venue] = []
    surfaces: list[Surface] = []
    slots: list[Slot] = []
    blackouts: list[Blackout] = []

    @property
    def preset(self) -> SportPreset:
        return SPORT_PRESETS[self.sport]


# ── Schedule ────────────────────────────────────────────────────────────────


class EventKind(StrEnum):
    GAME = "game"
    PRACTICE = "practice"


class Event(Model):
    """One scheduled thing on a surface. Games have two teams, practices one."""

    id: str
    kind: EventKind = EventKind.GAME
    division_id: str
    home_team_id: str
    away_team_id: str | None = None
    slot_id: str
    start: datetime
    minutes: int = Field(gt=0)
    units: int = Field(default=1, gt=0)
    locked: bool = False

    @model_validator(mode="after")
    def _teams_make_sense(self) -> Self:
        if self.kind == EventKind.GAME and self.away_team_id is None:
            raise ValueError("a game needs an away team")
        if self.home_team_id == self.away_team_id:
            raise ValueError("a team can't play itself")
        return self

    @property
    def end(self) -> datetime:
        return self.start + timedelta(minutes=self.minutes)

    @property
    def team_ids(self) -> tuple[str, ...]:
        if self.away_team_id is None:
            return (self.home_team_id,)
        return (self.home_team_id, self.away_team_id)


class Schedule(Model):
    league_id: str
    events: list[Event] = []

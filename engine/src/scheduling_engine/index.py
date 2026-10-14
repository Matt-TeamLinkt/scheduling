"""Fast lookups over a League, plus the rule-override resolution."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from .model import (
    Coach,
    Division,
    Event,
    League,
    Rules,
    Slot,
    Surface,
    Team,
    Venue,
)


class LeagueIndex:
    def __init__(self, league: League) -> None:
        self.league = league
        self.divisions: dict[str, Division] = {d.id: d for d in league.divisions}
        self.teams: dict[str, Team] = {t.id: t for t in league.teams}
        self.coaches: dict[str, Coach] = {c.id: c for c in league.coaches}
        self.venues: dict[str, Venue] = {v.id: v for v in league.venues}
        self.surfaces: dict[str, Surface] = {s.id: s for s in league.surfaces}
        self.slots: dict[str, Slot] = {s.id: s for s in league.slots}
        self.coaches_of_team: dict[str, list[Coach]] = defaultdict(list)
        for c in league.coaches:
            for tid in c.team_ids:
                self.coaches_of_team[tid].append(c)
        self._rules: dict[str, Rules] = {}

    def division_rules(self, division_id: str) -> Rules:
        key = "d:" + division_id
        if key not in self._rules:
            div = self.divisions.get(division_id)
            base = self.league.rules
            self._rules[key] = div.rules.apply_to(base) if div else base
        return self._rules[key]

    def team_rules(self, team_id: str) -> Rules:
        """League defaults, then the division's overrides, then the team's."""
        key = "t:" + team_id
        if key not in self._rules:
            team = self.teams.get(team_id)
            if team is None:
                self._rules[key] = self.league.rules
            else:
                self._rules[key] = team.rules.apply_to(self.division_rules(team.division_id))
        return self._rules[key]

    # ── plain-language names ──

    def team_name(self, team_id: str | None) -> str:
        if team_id is None:
            return "?"
        t = self.teams.get(team_id)
        return t.name if t else f"unknown team {team_id}"

    def place(self, slot_id: str) -> str:
        slot = self.slots.get(slot_id)
        if slot is None:
            return "an unknown slot"
        surface = self.surfaces.get(slot.surface_id)
        if surface is None:
            return "an unknown surface"
        venue = self.venues.get(surface.venue_id)
        if venue is None or surface.name == venue.name:
            return surface.name
        return f"{venue.name} {surface.name}"

    def describe(self, e: Event) -> str:
        """'Falcons vs Rovers, Sat Jan 9 at 9:00 AM at North Arena Rink 1'."""
        if e.away_team_id is None:
            what = f"{self.team_name(e.home_team_id)} practice"
        else:
            what = f"{self.team_name(e.home_team_id)} vs {self.team_name(e.away_team_id)}"
        return f"{what}, {fmt_when(e.start)} at {self.place(e.slot_id)}"


def fmt_day(d: datetime) -> str:
    return f"{d:%a %b} {d.day}"


def fmt_time(d: datetime) -> str:
    hour = d.hour % 12 or 12
    return f"{hour}:{d:%M %p}"


def fmt_when(d: datetime) -> str:
    return f"{fmt_day(d)} at {fmt_time(d)}"


def fmt_minutes(m: int) -> str:
    if m < 60:
        return f"{m} min"
    h, rem = divmod(m, 60)
    hours = f"{h} hour" if h == 1 else f"{h} hours"
    return f"{hours} {rem} min" if rem else hours

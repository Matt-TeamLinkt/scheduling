"""Events summary: one row per team with what's scheduled, what families have already
seen (published) and what's still a draft. The scheduler's at-a-glance table.

A game counts as published when the published schedule has it at the same time and
place with the same teams. Anything new or changed since then is unpublished.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .index import LeagueIndex
from .matchups import Matchup
from .model import Event, League


@dataclass
class SummaryRow:
    team_id: str
    name: str
    division: str
    target: int  # games per team the rules ask for
    games: int
    published_games: int
    unpublished_games: int
    practices: int
    published_practices: int
    unpublished_practices: int
    home: int
    away: int
    waiting: int  # games in "Needs a spot"
    locked: int


def _key(e: Event) -> tuple[str, str, str, str | None, str]:
    return (e.slot_id, e.start.isoformat(), e.home_team_id, e.away_team_id, e.kind)


def events_summary(
    league: League,
    events: Sequence[Event],
    published: Sequence[Event] = (),
    waiting: Sequence[Matchup] = (),
) -> list[SummaryRow]:
    ix = LeagueIndex(league)
    out_there = {_key(e) for e in published}
    rows: list[SummaryRow] = []
    for t in league.teams:
        mine = [e for e in events if t.id in e.team_ids]
        games = [e for e in mine if e.away_team_id is not None]
        practices = [e for e in mine if e.away_team_id is None]
        pub_games = sum(_key(e) in out_there for e in games)
        pub_practices = sum(_key(e) in out_there for e in practices)
        rows.append(
            SummaryRow(
                team_id=t.id,
                name=t.name,
                division=ix.divisions[t.division_id].name if t.division_id in ix.divisions else "",
                target=ix.team_rules(t.id).games_per_team,
                games=len(games),
                published_games=pub_games,
                unpublished_games=len(games) - pub_games,
                practices=len(practices),
                published_practices=pub_practices,
                unpublished_practices=len(practices) - pub_practices,
                home=sum(e.home_team_id == t.id for e in games),
                away=sum(e.away_team_id == t.id for e in games),
                waiting=sum(t.id in m.team_ids for m in waiting),
                locked=sum(e.locked for e in mine),
            )
        )
    return rows

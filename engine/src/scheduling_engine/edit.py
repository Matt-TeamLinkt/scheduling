"""Keeping a schedule consistent when the setup changes by hand.

    events, waiting, notes = fit_to_setup(new_league, events, waiting)

Deleting a team cancels its games. Deleting a time slot (or the venue it's at) sends
its games back to the "Needs a spot" list, since the matchup itself is still good.
Nothing else changes. Notes say what happened, in plain words.
"""

from __future__ import annotations

from collections.abc import Sequence

from .index import LeagueIndex
from .matchups import Matchup
from .model import Event, League


def fit_to_setup(
    league: League, events: Sequence[Event], waiting: Sequence[Matchup]
) -> tuple[list[Event], list[Matchup], list[str]]:
    ix = LeagueIndex(league)

    def teams_ok(team_ids: Sequence[str | None], division_id: str) -> bool:
        return division_id in ix.divisions and all(t in ix.teams for t in team_ids if t)

    kept: list[Event] = []
    back: list[Matchup] = []
    cancelled = 0
    for e in events:
        if not teams_ok(e.team_ids, e.division_id):
            cancelled += 1
        elif e.slot_id not in ix.slots or ix.slots[e.slot_id].surface_id not in ix.surfaces:
            if e.away_team_id is None:
                cancelled += 1  # a practice with nowhere to go
            else:
                back.append(Matchup(e.id, e.division_id, e.home_team_id, e.away_team_id, 0))
        else:
            kept.append(e)
    still = [m for m in waiting if teams_ok(m.team_ids, m.division_id)]
    dropped = len(waiting) - len(still)

    notes = []
    if cancelled + dropped:
        n = cancelled + dropped
        notes.append(f"{n} {'game was' if n == 1 else 'games were'} removed with the teams.")
    if back:
        n = len(back)
        notes.append(
            f"{n} {'game was' if n == 1 else 'games were'} in time that's no longer available. "
            f"{'It is' if n == 1 else 'They are'} in the Needs a spot list."
        )
    return kept, [*still, *back], notes

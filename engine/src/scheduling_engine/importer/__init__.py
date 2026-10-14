"""Forgiving CSV/Excel import for teams, coaches and time slots.

Every import is two steps, so nothing changes until the scheduler has seen the preview:

    preview = preview_teams(league, data, "teams.xlsx")
    preview.summary   # "We'll add 38 teams in 4 divisions and 34 new coaches. 2 rows ..."
    preview.problems  # row-by-row notes in plain language
    league = apply_import(league, preview)
"""

from .people import preview_coaches, preview_teams
from .plan import Changes, ImportKind, ImportPreview, Level, Problem, apply_import
from .slots import preview_slots

__all__ = [
    "Changes",
    "ImportKind",
    "ImportPreview",
    "Level",
    "Problem",
    "apply_import",
    "preview_coaches",
    "preview_slots",
    "preview_teams",
]

"""Scheduling engine: league data model, rule checks and (Phase 2) the solver."""

from .model import (
    SPORT_PRESETS,
    Blackout,
    BlackoutScope,
    Coach,
    Division,
    Event,
    EventKind,
    Family,
    League,
    RuleOverrides,
    Rules,
    Schedule,
    Slot,
    Sport,
    Surface,
    Team,
    Venue,
)
from .setup_check import SetupProblem, Severity, check_setup
from .validate import Code, Violation, validate

__all__ = [
    "SPORT_PRESETS",
    "Blackout",
    "BlackoutScope",
    "Code",
    "Coach",
    "Division",
    "Event",
    "EventKind",
    "Family",
    "League",
    "RuleOverrides",
    "Rules",
    "Schedule",
    "SetupProblem",
    "Severity",
    "Slot",
    "Sport",
    "Surface",
    "Team",
    "Venue",
    "Violation",
    "check_setup",
    "validate",
]

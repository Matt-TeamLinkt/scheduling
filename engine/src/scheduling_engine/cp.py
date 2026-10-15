"""Small typed helpers over OR-Tools CP-SAT expressions."""

from __future__ import annotations

from collections.abc import Iterable

from ortools.sat.python import cp_model

Expr = cp_model.LinearExpr


def total(items: Iterable[cp_model.IntVar | cp_model.LinearExpr | int]) -> Expr:
    """Sum of solver variables/expressions, typed as a LinearExpr (builtin sum() isn't)."""
    return cp_model.LinearExpr.sum(list(items))

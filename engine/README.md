# scheduling-engine

The league data model, the hard-constraint checker, and (Phase 2) the CP-SAT solver.

```sh
uv sync                       # install
uv run pytest -q              # tests
uv run ruff check src tests && uv run ruff format --check src tests && uv run mypy src tests
uv run python -m scheduling_engine.fixtures ../fixtures   # regenerate fixture snapshots
```

- `model.py`: league, rules (league defaults → division → team overrides), facilities, events.
- `validate.py`: `validate(league, events)` returns every hard-constraint violation, in plain language. The solver's tests and the drag-and-drop UI both use it.
- `setup_check.py`: `check_setup(league)` returns problems with the setup itself (bad references, overlapping slots, tiny divisions…).
- `importer/`: forgiving CSV/Excel import (preview, then apply) for teams, coaches and time slots.
- `fixtures.py`: deterministic test leagues `small_8`, `league_40`, `nightmare`.

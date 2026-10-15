# scheduling-engine

The league data model, rule checker, importer, CP-SAT solver, fairness report and explanations. How it works: `../docs/ENGINE.md`.

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
- `matchups.py`, `greedy.py`, `solver.py`, `goals.py`: who plays whom, a fast first draft, CP-SAT placement (fit first, then fairness).
- `report.py`, `explain.py`, `regen.py`: fairness report; why games didn't fit plus verified fixes; partial regeneration.
- `bench.py`: quality benchmark over all fixtures (`--save` appends to `../bench/history.csv`).
- `fixtures.py`: deterministic test leagues `small_8`, `league_40`, `nightmare`.

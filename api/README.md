# scheduling-api

FastAPI service around the engine. Seasons are stored as a chain of versions (undo/redo, draft vs published, change log).

```sh
uv sync
uv run uvicorn scheduling_api.server:app --reload    # http://localhost:8000/api/seasons
uv run pytest -q
```

Settings (environment): `SCHEDULING_DB` (default `sqlite:///./data/scheduling.db`; use a Postgres URL in production), `SCHEDULING_WORKERS` (solver threads, default 8), `SCHEDULING_WEB_DIST` (built web app to serve; default `../web/dist`).

"""HTTP API for the web app. Thin: every rule lives in the engine.

Run locally:  uv run uvicorn scheduling_api.server:app --reload
"""

from __future__ import annotations

import os
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from scheduling_engine import Event, League, Severity, Sport, check_setup, fixtures, validate
from scheduling_engine.explain import Suggestion, capacity_check, explain
from scheduling_engine.goals import DEFAULT_PRIORITIES, GOAL_LABELS, Goal
from scheduling_engine.importer import (
    ImportPreview,
    apply_import,
    preview_coaches,
    preview_slots,
    preview_teams,
)
from scheduling_engine.index import LeagueIndex
from scheduling_engine.matchups import Matchup, make_matchups
from scheduling_engine.place import event_for, open_spots
from scheduling_engine.regen import Scope, reschedule
from scheduling_engine.report import fairness_report
from scheduling_engine.solver import SolveOptions, SolveResult, Status, solve

from .jobs import Job, Jobs
from .store import NotFound, Snapshot, Store

SAMPLES = {
    "small_8": "Small soccer league: 8 teams, Saturdays only",
    "league_40": "Hockey association: 40 teams in 4 divisions",
    "nightmare": "Hockey association with very tight ice",
}
WORKERS = int(os.environ.get("SCHEDULING_WORKERS", "8"))


# ── request bodies ──────────────────────────────────────────────────────────


class NewSeason(BaseModel):
    name: str
    sample: str | None = None
    sport: Sport = Sport.OTHER
    season_start: date | None = None
    season_end: date | None = None


class SetupChange(BaseModel):
    league: League
    action: str = "Changed the season setup"


class ScopeIn(BaseModel):
    division_ids: list[str] | None = None
    start: date | None = None
    end: date | None = None


class GenerateIn(BaseModel):
    priorities: list[Goal] | None = None
    seconds: float = 60
    fresh: bool = False  # True = start over: new matchups, ignore the current schedule
    scope: ScopeIn | None = None
    matchups_only: bool = False  # decide who plays whom; the scheduler places every game


class MoveIn(BaseModel):
    event_id: str
    slot_id: str
    start: datetime


class LockIn(BaseModel):
    locked: bool


class LockManyIn(BaseModel):
    locked: bool
    day: date | None = None  # one day ...
    week_of: date | None = None  # ... or the Monday-to-Sunday week holding this date
    venue_id: str | None = None
    division_id: str | None = None


class ApplySuggestionIn(BaseModel):
    index: int


class CloneIn(BaseModel):
    name: str
    season_start: date


# ── app ─────────────────────────────────────────────────────────────────────


def create_app(db_url: str | None = None) -> FastAPI:
    url = db_url or os.environ.get("SCHEDULING_DB", "sqlite:///./data/scheduling.db")
    if url.startswith("sqlite:///./"):
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    store = Store(url)
    jobs = Jobs()
    explained: dict[tuple[str, int], list[Suggestion]] = {}
    app = FastAPI(title="Scheduling")

    def snap_or_404(sid: str) -> Snapshot:
        try:
            return store.snapshot(sid)
        except NotFound:
            raise HTTPException(404, "That season doesn't exist.") from None

    def season_out(sid: str, message: str | None = None) -> dict[str, Any]:
        info = store.info(sid)
        snap = store.snapshot(sid)
        return {
            "id": sid,
            "name": info.name,
            "version": snap.n,
            "last_action": snap.action,
            "can_undo": info.current > 1,
            "can_redo": info.current < info.latest,
            "published_version": info.published,
            "unpublished_changes": len(store.unpublished_changes(sid)),
            "league": snap.league.model_dump(mode="json"),
            "events": [e.model_dump(mode="json") for e in snap.events],
            "unplaced": [asdict(m) for m in snap.unplaced],
            "goals": [{"id": g.value, "label": GOAL_LABELS[g]} for g in DEFAULT_PRIORITIES],
            "message": message,
        }

    # ── seasons ──

    @app.get("/api/samples")
    def samples() -> list[dict[str, str]]:
        return [{"id": k, "description": v} for k, v in SAMPLES.items()]

    @app.get("/api/seasons")
    def list_seasons() -> list[dict[str, Any]]:
        return [
            {
                "id": s.id,
                "name": s.name,
                "created_at": s.created_at.isoformat(),
                "published": s.published is not None,
            }
            for s in store.all_seasons()
        ]

    @app.post("/api/seasons")
    def create_season(body: NewSeason) -> dict[str, Any]:
        if body.sample:
            if body.sample not in fixtures.ALL:
                raise HTTPException(400, "That sample league doesn't exist.")
            league = fixtures.ALL[body.sample]()
            action = f"Started from the sample: {SAMPLES[body.sample]}"
        else:
            start = body.season_start or date.today()
            league = League(
                id="league",
                name=body.name,
                sport=body.sport,
                season_start=start,
                season_end=body.season_end or start + timedelta(weeks=12),
            )
            preset = league.preset
            league.rules = league.rules.model_copy(update={"game_minutes": preset.game_minutes})
            action = "Created the season"
        sid = store.create(body.name, league, action)
        return season_out(sid)

    @app.get("/api/seasons/{sid}")
    def get_season(sid: str) -> dict[str, Any]:
        snap_or_404(sid)
        return season_out(sid)

    @app.put("/api/seasons/{sid}/league")
    def change_setup(sid: str, body: SetupChange) -> dict[str, Any]:
        snap_or_404(sid)
        with store.lock(sid):
            store.commit(sid, body.action, league=body.league)
        return season_out(sid)

    @app.get("/api/seasons/{sid}/setup-check")
    def setup_check(sid: str) -> dict[str, Any]:
        snap = snap_or_404(sid)
        problems = check_setup(snap.league)
        capacity = (
            capacity_check(snap.league)
            if snap.league.slots
            and snap.league.teams
            and not any(p.severity == Severity.ERROR for p in problems)
            else []
        )
        return {
            "problems": [{"severity": p.severity.value, "message": p.message} for p in problems],
            "capacity": [f.message for f in capacity],
        }

    # ── import ──

    @app.post("/api/seasons/{sid}/import/{kind}")
    async def import_file(
        sid: str,
        kind: str,
        file: Annotated[UploadFile, File()],
        apply: Annotated[bool, Form()] = False,
    ) -> dict[str, Any]:
        snap = snap_or_404(sid)
        previewers = {"teams": preview_teams, "coaches": preview_coaches, "slots": preview_slots}
        if kind not in previewers:
            raise HTTPException(404, "You can import teams, coaches or slots.")
        data = await file.read()
        pv = previewers[kind](snap.league, data, file.filename or "upload.csv")
        out = _preview_out(pv)
        if apply and pv.can_import:
            with store.lock(sid):
                store.commit(
                    sid,
                    f"Imported {kind} from {pv.filename}",
                    league=apply_import(store.snapshot(sid).league, pv),
                )
            out["season"] = season_out(sid)
        return out

    # ── generate ──

    @app.post("/api/seasons/{sid}/generate")
    def generate(sid: str, body: GenerateIn) -> dict[str, Any]:
        snap_or_404(sid)
        priorities = tuple(body.priorities) if body.priorities is not None else DEFAULT_PRIORITIES

        def work(job: Job) -> dict[str, Any]:
            with store.lock(sid):
                snap = store.snapshot(sid)
                opts = SolveOptions(
                    priorities=priorities,
                    time_limit_s=body.seconds,
                    workers=WORKERS,
                    on_progress=job.on_progress,
                )
                if body.matchups_only:
                    matchups, mnotes = make_matchups(snap.league)
                    result = SolveResult(
                        Status.GOOD, [], matchups, 0.0, [n.message for n in mnotes]
                    )
                    action = "Built the matchups"
                elif body.fresh or not snap.events:
                    result = solve(snap.league, options=opts)
                    action = "Generated the schedule"
                else:
                    sc = body.scope
                    scope = Scope(
                        division_ids=frozenset(sc.division_ids) if sc and sc.division_ids else None,
                        start=sc.start if sc else None,
                        end=sc.end if sc else None,
                    )
                    result = reschedule(
                        snap.league, snap.events, scope, also_place=snap.unplaced, options=opts
                    )
                    action = f"Rescheduled {scope.describe(snap.league)}"
                return _finish(store, sid, snap, result, action)

        job = jobs.start(sid, work)
        return {"job_id": job.id}

    @app.get("/api/jobs/{job_id}")
    def job_status(job_id: str) -> dict[str, Any]:
        job = jobs.get(job_id)
        if job is None:
            raise HTTPException(404, "That job doesn't exist.")
        return {
            "state": job.state,
            "phase": job.phase,
            "placed": job.placed,
            "total": job.total,
            "seconds": round(job.seconds, 1),
            "message": job.message,
            "result": job.result,
        }

    # ── editing ──

    @app.post("/api/seasons/{sid}/check")
    def check_move(sid: str, body: MoveIn) -> dict[str, Any]:
        snap = snap_or_404(sid)
        moved, events = _moved(snap, body)
        problems = [v.message for v in validate(snap.league, events) if moved.id in v.event_ids]
        return {"ok": not problems, "problems": problems}

    @app.post("/api/seasons/{sid}/move")
    def move(sid: str, body: MoveIn) -> dict[str, Any]:
        snap = snap_or_404(sid)
        moved, events = _moved(snap, body)
        problems = [v.message for v in validate(snap.league, events) if moved.id in v.event_ids]
        ix = LeagueIndex(snap.league)
        from_tray = any(m.id == moved.id for m in snap.unplaced)
        with store.lock(sid):
            if from_tray:
                store.commit(
                    sid,
                    f"Placed {ix.describe(moved)}",
                    events=events,
                    unplaced=[m for m in snap.unplaced if m.id != moved.id],
                )
            else:
                store.commit(sid, f"Moved {ix.describe(moved)}", events=events)
        out = season_out(sid)
        out["problems"] = problems
        return out

    @app.post("/api/seasons/{sid}/events/{eid}/lock")
    def lock(sid: str, eid: str, body: LockIn) -> dict[str, Any]:
        snap = snap_or_404(sid)
        if not any(e.id == eid for e in snap.events):
            raise HTTPException(404, "That game isn't in the schedule.")
        events = [
            e.model_copy(update={"locked": body.locked}) if e.id == eid else e for e in snap.events
        ]
        e = next(x for x in events if x.id == eid)
        verb = "Locked" if body.locked else "Unlocked"
        with store.lock(sid):
            store.commit(sid, f"{verb} {LeagueIndex(snap.league).describe(e)}", events=events)
        return season_out(sid)

    @app.get("/api/seasons/{sid}/unplaced/{mid}/spots")
    def spots(sid: str, mid: str, with_problems: bool = False) -> list[dict[str, Any]]:
        snap = snap_or_404(sid)
        m = next((x for x in snap.unplaced if x.id == mid), None)
        if m is None:
            raise HTTPException(404, "That game isn't waiting for a spot.")
        return [
            asdict(c) | {"start": c.start.isoformat()}
            for c in open_spots(snap.league, snap.events, m, with_problems=with_problems)
        ]

    @app.post("/api/seasons/{sid}/events/{eid}/unschedule")
    def unschedule(sid: str, eid: str) -> dict[str, Any]:
        snap = snap_or_404(sid)
        e = next((x for x in snap.events if x.id == eid), None)
        if e is None or e.away_team_id is None:
            raise HTTPException(404, "That game isn't in the schedule.")
        back = Matchup(e.id, e.division_id, e.home_team_id, e.away_team_id, 0)
        with store.lock(sid):
            store.commit(
                sid,
                f"Took {LeagueIndex(snap.league).describe(e)} off the schedule",
                events=[x for x in snap.events if x.id != eid],
                unplaced=[*snap.unplaced, back],
            )
        return season_out(sid)

    @app.post("/api/seasons/{sid}/lock-many")
    def lock_many(sid: str, body: LockManyIn) -> dict[str, Any]:
        snap = snap_or_404(sid)
        ix = LeagueIndex(snap.league)
        chosen = {e.id for e in snap.events if _in_group(ix, e, body)}
        changing = [e for e in snap.events if e.id in chosen and e.locked != body.locked]
        verb = "Locked" if body.locked else "Unlocked"
        if not changing:
            already = "locked" if body.locked else "unlocked"
            n = len(chosen)
            msg = f"All {n} of those games are already {already}." if n else "No games match."
            return season_out(sid, msg)
        events = [
            e.model_copy(update={"locked": body.locked}) if e.id in chosen else e
            for e in snap.events
        ]
        n = len(changing)
        action = f"{verb} {n} {'game' if n == 1 else 'games'} {_group_words(ix, body)}".strip()
        with store.lock(sid):
            store.commit(sid, action, events=events)
        return season_out(sid, f"{action}.")

    @app.post("/api/seasons/{sid}/undo")
    def undo(sid: str) -> dict[str, Any]:
        snap_or_404(sid)
        with store.lock(sid):
            current = store.snapshot(sid)
            snap = store.undo(sid)
        if snap is None:
            raise HTTPException(400, "There's nothing to undo.")
        return season_out(sid, f"Undid: {current.action}")

    @app.post("/api/seasons/{sid}/redo")
    def redo(sid: str) -> dict[str, Any]:
        snap_or_404(sid)
        with store.lock(sid):
            snap = store.redo(sid)
        if snap is None:
            raise HTTPException(400, "There's nothing to redo.")
        return season_out(sid, f"Redid: {snap.action}")

    @app.get("/api/seasons/{sid}/history")
    def history(sid: str) -> list[dict[str, Any]]:
        snap_or_404(sid)
        return [
            {"version": n, "at": at.isoformat(), "action": a} for n, at, a in store.history(sid)
        ]

    # ── reports ──

    @app.get("/api/seasons/{sid}/report")
    def report(sid: str) -> dict[str, Any]:
        snap = snap_or_404(sid)
        rep = fairness_report(snap.league, snap.events)
        return {
            "summary": rep.summary,
            "teams": [asdict(t) | {"early_or_late": t.early_or_late} for t in rep.teams],
            "flags": [asdict(f) for f in rep.flags],
            "family_clashes": rep.family_clashes,
            "metrics": rep.metrics,
        }

    @app.get("/api/seasons/{sid}/explain")
    def explain_route(sid: str) -> dict[str, Any]:
        snap = snap_or_404(sid)
        result = SolveResult(Status.GOOD, snap.events, snap.unplaced, 0.0)
        ex = explain(snap.league, result, max_tries=3)
        explained[(sid, snap.n)] = ex.suggestions
        return {
            "summary": ex.summary,
            "findings": [f.message for f in ex.findings],
            "suggestions": [
                {"index": i, "message": s.message, "fixes": s.fixes, "of": s.of}
                for i, s in enumerate(ex.suggestions)
            ],
        }

    @app.post("/api/seasons/{sid}/explain/apply")
    def apply_suggestion(sid: str, body: ApplySuggestionIn) -> dict[str, Any]:
        snap = snap_or_404(sid)
        options = explained.get((sid, snap.n))
        if options is None or not 0 <= body.index < len(options):
            raise HTTPException(400, "Refresh the suggestions and try again.")
        chosen = options[body.index]

        def work(job: Job) -> dict[str, Any]:
            with store.lock(sid):
                store.commit(sid, chosen.message.split(" would ")[0], league=chosen.league)
                cur = store.snapshot(sid)
                opts = SolveOptions(
                    priorities=(), time_limit_s=20, workers=WORKERS, on_progress=job.on_progress
                )
                result = reschedule(
                    cur.league,
                    cur.events,
                    Scope(division_ids=frozenset()),
                    also_place=cur.unplaced,
                    options=opts,
                )
                return _finish(store, sid, cur, result, "Placed games that didn't fit")

        return {"job_id": jobs.start(sid, work).id}

    # ── publishing ──

    @app.get("/api/seasons/{sid}/publish-preview")
    def publish_preview(sid: str) -> dict[str, Any]:
        snap_or_404(sid)
        changes = store.unpublished_changes(sid)
        teams = {t for c in changes for t in c.team_ids}
        return {
            "changes": [{"kind": c.kind.value, "message": c.message} for c in changes],
            "teams_affected": len(teams),
        }

    @app.post("/api/seasons/{sid}/publish")
    def publish(sid: str) -> dict[str, Any]:
        snap = snap_or_404(sid)
        if not snap.events:
            raise HTTPException(400, "Generate a schedule before publishing.")
        with store.lock(sid):
            pub = store.publish(sid)
        out = season_out(sid, f"Published. {len(pub.changes)} changes went out.")
        out["publication"] = {
            "version": pub.n,
            "published_at": pub.published_at.isoformat(),
            "changes": pub.changes,
        }
        return out

    @app.get("/api/seasons/{sid}/publications")
    def publications(sid: str) -> list[dict[str, Any]]:
        snap_or_404(sid)
        return [
            {"version": p.n, "published_at": p.published_at.isoformat(), "changes": p.changes}
            for p in store.publications(sid)
        ]

    # ── templates ──

    @app.post("/api/seasons/{sid}/clone")
    def clone(sid: str, body: CloneIn) -> dict[str, Any]:
        snap = snap_or_404(sid)
        lg = _shift_league(snap.league, body.season_start)
        new = store.create(body.name, lg, f"Copied the setup from {store.info(sid).name}")
        return season_out(new)

    # ── the web app (built files), if present ──

    dist = Path(
        os.environ.get("SCHEDULING_WEB_DIST", Path(__file__).resolve().parents[3] / "web" / "dist")
    )
    if dist.is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str) -> FileResponse:
            f = dist / path
            return FileResponse(f if path and f.is_file() else dist / "index.html")

    return app


# ── helpers ─────────────────────────────────────────────────────────────────


def _preview_out(pv: ImportPreview) -> dict[str, Any]:
    ch = pv.changes
    return {
        "summary": pv.summary,
        "can_import": pv.can_import,
        "columns": [{"header": c.header, "field": c.field} for c in pv.columns],
        "problems": [
            {"row": p.row, "level": p.level.value, "message": p.message} for p in pv.problems
        ],
        "counts": {
            "divisions": len(ch.divisions),
            "teams": len(ch.teams),
            "coaches": len(ch.coaches),
            "venues": len(ch.venues),
            "surfaces": len(ch.surfaces),
            "slots": len(ch.slots),
        },
    }


def _finish(
    store: Store, sid: str, before: Snapshot, result: SolveResult, action: str
) -> dict[str, Any]:
    if result.status == Status.NO_SCHEDULE:
        return {
            "summary": " ".join(result.notes) or "No schedule could be made.",
            "notes": result.notes,
            "placed": 0,
            "unplaced": len(result.unplaced),
        }
    store.commit(sid, action, events=result.events, unplaced=result.unplaced)
    placed = len(result.events)
    if not placed and result.unplaced:
        summary = (
            f"Built {len(result.unplaced)} games. Place them from the "
            '"Needs a spot" list; the best spots are marked for you.'
        )
    elif result.unplaced:
        summary = (
            f"{placed} games scheduled. {len(result.unplaced)} didn't fit; see why "
            "and how to fix it."
        )
    else:
        summary = f"All {placed} games scheduled."
    return {
        "summary": summary,
        "notes": result.notes,
        "placed": placed,
        "unplaced": len(result.unplaced),
        "seconds": round(result.seconds, 1),
    }


def _moved(snap: Snapshot, body: MoveIn) -> tuple[Event, list[Event]]:
    """The game at its new spot, and the whole schedule with it there. The game can be
    on the schedule already or waiting for a spot."""
    ix = LeagueIndex(snap.league)
    slot = ix.slots.get(body.slot_id)
    if slot is None:
        raise HTTPException(404, "That time slot doesn't exist.")
    start = body.start.replace(tzinfo=None)
    waiting = next((m for m in snap.unplaced if m.id == body.event_id), None)
    if waiting is not None:
        new = event_for(snap.league, waiting, slot.id, start)
        return new, [*snap.events, new]
    old = next((e for e in snap.events if e.id == body.event_id), None)
    if old is None:
        raise HTTPException(404, "That game isn't in the schedule.")
    rules = [ix.team_rules(t) for t in old.team_ids]
    units_rule = [r.units for r in rules]
    units = (
        max(u for u in units_rule if u is not None)
        if None not in units_rule
        else ix.surfaces[slot.surface_id].units
    )
    moved = old.model_copy(update={"slot_id": slot.id, "start": start, "units": units})
    return moved, [moved if e.id == old.id else e for e in snap.events]


def _in_group(ix: LeagueIndex, e: Event, g: LockManyIn) -> bool:
    day = e.start.date()
    if g.day is not None and day != g.day:
        return False
    if g.week_of is not None:
        monday = g.week_of - timedelta(days=g.week_of.weekday())
        if not monday <= day <= monday + timedelta(days=6):
            return False
    if (
        g.venue_id is not None
        and ix.surfaces[ix.slots[e.slot_id].surface_id].venue_id != g.venue_id
    ):
        return False
    return g.division_id is None or e.division_id == g.division_id


def _group_words(ix: LeagueIndex, g: LockManyIn) -> str:
    """'in U11 at North Arena on Sat Jan 9', in plain words."""
    parts = []
    if g.division_id is not None and g.division_id in ix.divisions:
        parts.append(f"in {ix.divisions[g.division_id].name}")
    if g.venue_id is not None and g.venue_id in ix.venues:
        parts.append(f"at {ix.venues[g.venue_id].name}")
    if g.day is not None:
        parts.append(f"on {g.day:%a %b} {g.day.day}")
    if g.week_of is not None:
        monday = g.week_of - timedelta(days=g.week_of.weekday())
        parts.append(f"in the week of {monday:%b} {monday.day}")
    return " ".join(parts)


def _shift_league(lg: League, new_start: date) -> League:
    """Same setup for a new season: dates move by whole weeks so weekdays stay put."""
    weeks = round((new_start - lg.season_start).days / 7)
    delta = timedelta(weeks=weeks)
    out = lg.model_copy(deep=True)
    out.season_start += delta
    out.season_end += delta
    for s in out.slots:
        s.date += delta
    for b in out.blackouts:
        b.start_date += delta
        b.end_date += delta
    return out

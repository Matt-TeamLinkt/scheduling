"""Seasons as a chain of versions.

Every scheduler action (import, generate, move a game, change a rule) saves a new
version: the whole league setup plus the schedule. That gives us, almost for free:
  undo/redo   move the "current" pointer back and forward
  draft       whatever "current" points at
  published   a pointer to the version families see
  change log  diff between the last published version and the new one
A 40-team season is a few hundred KB of JSON, so whole snapshots are cheap and simple.
SQLite locally, Postgres in production (same SQLAlchemy code).
"""

from __future__ import annotations

import json
import secrets
import threading
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from scheduling_engine import Event, League
from scheduling_engine.changes import Change, diff_schedules
from scheduling_engine.matchups import Matchup
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    delete,
    insert,
    select,
    update,
)
from sqlalchemy.engine import Engine

meta = MetaData()

seasons = Table(
    "seasons",
    meta,
    Column("id", String(32), primary_key=True),
    Column("name", String(200), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("current", Integer, nullable=False),
    Column("published", Integer, nullable=True),
)

versions = Table(
    "versions",
    meta,
    Column("season_id", String(32), ForeignKey("seasons.id"), primary_key=True),
    Column("n", Integer, primary_key=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("action", String(500), nullable=False),
    Column("data", Text, nullable=False),
)

publications = Table(
    "publications",
    meta,
    Column("season_id", String(32), ForeignKey("seasons.id"), primary_key=True),
    Column("n", Integer, primary_key=True),  # the version that was published
    Column("published_at", DateTime(timezone=True), nullable=False),
    Column("changes", Text, nullable=False),
)


@dataclass
class Snapshot:
    n: int
    action: str
    league: League
    events: list[Event]
    unplaced: list[Matchup]

    def to_json(self) -> str:
        return json.dumps(
            {
                "league": self.league.model_dump(mode="json"),
                "events": [e.model_dump(mode="json") for e in self.events],
                "unplaced": [asdict(m) for m in self.unplaced],
            }
        )

    @staticmethod
    def from_row(n: int, action: str, data: str) -> Snapshot:
        d = json.loads(data)
        return Snapshot(
            n=n,
            action=action,
            league=League.model_validate(d["league"]),
            events=[Event.model_validate(e) for e in d["events"]],
            unplaced=[Matchup(**m) for m in d["unplaced"]],
        )


@dataclass
class SeasonInfo:
    id: str
    name: str
    created_at: datetime
    current: int
    published: int | None
    latest: int  # highest version number (for redo)


@dataclass
class Publication:
    n: int
    published_at: datetime
    changes: list[dict[str, Any]]


class NotFound(Exception):
    pass


class Store:
    def __init__(self, url: str) -> None:
        self.engine: Engine = create_engine(url)
        meta.create_all(self.engine)
        self._locks: dict[str, threading.Lock] = {}
        self._guard = threading.Lock()

    def lock(self, sid: str) -> threading.Lock:
        """One writer per season at a time (generation runs in a background thread)."""
        with self._guard:
            return self._locks.setdefault(sid, threading.Lock())

    # ── seasons ──

    def create(self, name: str, league: League, action: str = "Created the season") -> str:
        sid = secrets.token_hex(6)
        now = datetime.now(UTC)
        snap = Snapshot(1, action, league, [], [])
        with self.engine.begin() as c:
            c.execute(insert(seasons).values(id=sid, name=name, created_at=now, current=1))
            c.execute(
                insert(versions).values(
                    season_id=sid, n=1, created_at=now, action=action, data=snap.to_json()
                )
            )
        return sid

    def all_seasons(self) -> list[SeasonInfo]:
        with self.engine.connect() as c:
            rows = c.execute(select(seasons).order_by(seasons.c.created_at.desc())).all()
            return [self._info_from(c, r) for r in rows]

    def info(self, sid: str) -> SeasonInfo:
        with self.engine.connect() as c:
            r = c.execute(select(seasons).where(seasons.c.id == sid)).first()
            if r is None:
                raise NotFound(sid)
            return self._info_from(c, r)

    def _info_from(self, c: Any, r: Any) -> SeasonInfo:
        latest = c.execute(
            select(versions.c.n).where(versions.c.season_id == r.id).order_by(versions.c.n.desc())
        ).first()
        return SeasonInfo(r.id, r.name, r.created_at, r.current, r.published, latest[0])

    def rename(self, sid: str, name: str) -> None:
        with self.engine.begin() as c:
            c.execute(update(seasons).where(seasons.c.id == sid).values(name=name))

    # ── versions ──

    def snapshot(self, sid: str, n: int | None = None) -> Snapshot:
        info = self.info(sid)
        n = info.current if n is None else n
        with self.engine.connect() as c:
            r = c.execute(
                select(versions).where(versions.c.season_id == sid, versions.c.n == n)
            ).first()
        if r is None:
            raise NotFound(f"{sid} v{n}")
        return Snapshot.from_row(r.n, r.action, r.data)

    def commit(
        self,
        sid: str,
        action: str,
        league: League | None = None,
        events: list[Event] | None = None,
        unplaced: list[Matchup] | None = None,
    ) -> Snapshot:
        """Save a new version on top of the current one. Anything that was 'redo-able'
        is discarded, like every other app's undo history."""
        cur = self.snapshot(sid)
        snap = Snapshot(
            cur.n + 1,
            action,
            league if league is not None else cur.league,
            events if events is not None else cur.events,
            unplaced if unplaced is not None else cur.unplaced,
        )
        now = datetime.now(UTC)
        with self.engine.begin() as c:
            c.execute(delete(versions).where(versions.c.season_id == sid, versions.c.n > cur.n))
            c.execute(
                insert(versions).values(
                    season_id=sid, n=snap.n, created_at=now, action=action, data=snap.to_json()
                )
            )
            c.execute(update(seasons).where(seasons.c.id == sid).values(current=snap.n))
        return snap

    def undo(self, sid: str) -> Snapshot | None:
        info = self.info(sid)
        if info.current <= 1:
            return None
        undone = self.snapshot(sid).action
        self._move(sid, info.current - 1)
        snap = self.snapshot(sid)
        snap.action = undone
        return snap

    def redo(self, sid: str) -> Snapshot | None:
        info = self.info(sid)
        if info.current >= info.latest:
            return None
        self._move(sid, info.current + 1)
        return self.snapshot(sid)

    def _move(self, sid: str, n: int) -> None:
        with self.engine.begin() as c:
            c.execute(update(seasons).where(seasons.c.id == sid).values(current=n))

    def history(self, sid: str) -> list[tuple[int, datetime, str]]:
        with self.engine.connect() as c:
            rows = c.execute(
                select(versions.c.n, versions.c.created_at, versions.c.action)
                .where(versions.c.season_id == sid)
                .order_by(versions.c.n)
            ).all()
        return [(r.n, r.created_at, r.action) for r in rows]

    # ── publishing ──

    def unpublished_changes(self, sid: str) -> list[Change]:
        info = self.info(sid)
        cur = self.snapshot(sid)
        before = self.snapshot(sid, info.published).events if info.published else []
        return diff_schedules(cur.league, before, cur.events)

    def publish(self, sid: str) -> Publication:
        info = self.info(sid)
        changes = self.unpublished_changes(sid)
        now = datetime.now(UTC)
        payload = [
            {
                "kind": ch.kind.value,
                "event_id": ch.event_id,
                "team_ids": list(ch.team_ids),
                "message": ch.message,
            }
            for ch in changes
        ]
        with self.engine.begin() as c:
            c.execute(
                delete(publications).where(
                    publications.c.season_id == sid, publications.c.n == info.current
                )
            )
            c.execute(
                insert(publications).values(
                    season_id=sid, n=info.current, published_at=now, changes=json.dumps(payload)
                )
            )
            c.execute(update(seasons).where(seasons.c.id == sid).values(published=info.current))
        return Publication(info.current, now, payload)

    def publications(self, sid: str) -> list[Publication]:
        with self.engine.connect() as c:
            rows = c.execute(
                select(publications)
                .where(publications.c.season_id == sid)
                .order_by(publications.c.published_at.desc())
            ).all()
        return [Publication(r.n, r.published_at, json.loads(r.changes)) for r in rows]

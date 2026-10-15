"""Background schedule generation with progress the web app can poll."""

from __future__ import annotations

import secrets
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from scheduling_engine.solver import Progress


@dataclass
class Job:
    id: str
    season_id: str
    state: str = "running"  # running | done | failed
    phase: str = "starting"  # starting | placing | improving
    placed: int = 0
    total: int = 0
    seconds: float = 0.0
    message: str = "Getting started…"
    result: dict[str, Any] = field(default_factory=dict)
    started: float = field(default_factory=time.monotonic)

    def on_progress(self, p: Progress) -> None:
        self.phase = p.phase.value
        self.placed, self.total, self.seconds = p.placed, p.total, p.seconds
        if p.phase.value == "placing":
            self.message = f"Fitting games into your time slots… {p.placed} of {p.total}"
        else:
            self.message = "Every game that can fit is in. Making the schedule fairer…"


class Jobs:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}

    def start(self, season_id: str, work: Callable[[Job], dict[str, Any]]) -> Job:
        job = Job(id=secrets.token_hex(6), season_id=season_id)
        self._jobs[job.id] = job

        def runner() -> None:
            try:
                job.result = work(job)
                job.state = "done"
                job.message = job.result.get("summary", "Done.")
            except Exception as exc:  # report, don't crash the server
                job.state = "failed"
                job.message = f"Something went wrong while scheduling: {exc}"
            job.seconds = time.monotonic() - job.started

        threading.Thread(target=runner, daemon=True).start()
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

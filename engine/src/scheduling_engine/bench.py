"""Quality benchmark: solve every fixture, check it, measure it, keep a history.

    uv run python -m scheduling_engine.bench                 # all fixtures, 60 s each
    uv run python -m scheduling_engine.bench --time 30 small_8 league_40
    uv run python -m scheduling_engine.bench --label "try rematch goal" --save

--save appends one row per fixture to ../bench/history.csv (with the git commit), so
we can see whether a change makes schedules better or worse over time.
"""

from __future__ import annotations

import argparse
import csv
import subprocess
from datetime import datetime
from pathlib import Path

from .fixtures import ALL
from .report import fairness_report
from .solver import SolveOptions, solve
from .validate import validate

HISTORY = Path(__file__).resolve().parents[3] / "bench" / "history.csv"
COLUMNS = [
    "when", "commit", "label", "fixture", "seconds", "status", "games", "unplaced",
    "violations", "short_of_target", "home_away_worst", "early_late_spread",
    "back_to_back_days", "longest_gap_days", "quickest_rematch_days", "family_clashes",
    "travel_km", "away_from_home_venue", "flags",
]  # fmt: skip


def run_one(name: str, seconds: float, workers: int) -> dict[str, object]:
    lg = ALL[name]()
    r = solve(lg, options=SolveOptions(time_limit_s=seconds, workers=workers))
    rep = fairness_report(lg, r.events)
    row: dict[str, object] = {
        "fixture": name,
        "seconds": round(r.seconds, 1),
        "status": r.status.value,
        "unplaced": len(r.unplaced),
        "violations": len(validate(lg, r.events)),
        "flags": len(rep.flags),
    }
    row.update(rep.metrics)
    return row


def _commit() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                             text=True, check=True)  # fmt: skip
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("fixtures", nargs="*", default=list(ALL))
    ap.add_argument("--time", type=float, default=60.0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--label", default="")
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()

    rows = []
    for name in args.fixtures:
        row = run_one(name, args.time, args.workers)
        row.update(when=datetime.now().isoformat(timespec="seconds"), commit=_commit(),
                   label=args.label)  # fmt: skip
        rows.append(row)
        shown = {k: row[k] for k in COLUMNS[3:] if k in row}
        print("  ".join(f"{k}={v}" for k, v in shown.items()), flush=True)

    if args.save:
        HISTORY.parent.mkdir(parents=True, exist_ok=True)
        new = not HISTORY.exists()
        with HISTORY.open("a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
            if new:
                w.writeheader()
            w.writerows(rows)
        print(f"saved to {HISTORY}")


if __name__ == "__main__":
    main()

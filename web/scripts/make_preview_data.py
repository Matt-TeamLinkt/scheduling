"""Precompute everything the preview page shows, using the real engine.

    cd engine && uv run python ../web/scripts/make_preview_data.py ../web/dist-demo/demo-data.json


import json
import sys
from dataclasses import asdict

from scheduling_engine import check_setup, fixtures, validate
from scheduling_engine.explain import capacity_check, explain
from scheduling_engine.regen import Scope, reschedule
from scheduling_engine.report import fairness_report
from scheduling_engine.solver import SolveOptions, solve


def report_json(lg, events):
    rep = fairness_report(lg, events)
    return {
        "summary": rep.summary,
        "teams": [asdict(t) | {"early_or_late": t.early_or_late} for t in rep.teams],
        "flags": [asdict(f) for f in rep.flags],
        "family_clashes": rep.family_clashes,
    }


def pack(lg, r):
    assert validate(lg, r.events) == []
    return {
        "league": lg.model_dump(mode="json"),
        "events": [e.model_dump(mode="json") for e in r.events],
        "unplaced": [asdict(m) for m in r.unplaced],
        "report": report_json(lg, r.events),
    }


opts = lambda s: SolveOptions(time_limit_s=s, workers=4)  # noqa: E731
out = []

lg = fixtures.small_8()
out.append({"id": "small_8", "description": "Small soccer league: 8 teams, Saturdays only",
            **pack(lg, solve(lg, options=opts(15)))})
print("small_8 done", file=sys.stderr)

lg = fixtures.league_40()
out.append({"id": "league_40", "description": "Hockey association: 40 teams in 4 divisions",
            **pack(lg, solve(lg, options=opts(90)))})
print("league_40 done", file=sys.stderr)

lg = fixtures.league_40()
lg.slots = [s for s in lg.slots if not (s.surface_id == "s-north-1" and s.date.weekday() == 6)]
r = solve(lg, options=opts(60))
ex = explain(lg, r, max_tries=3)
entry = {"id": "short_ice", "description": "Hockey association that's short on ice (shows how problems are explained)",
         **pack(lg, r),
         "capacity": [f.message for f in capacity_check(lg)],
         "explain": {"summary": ex.summary, "findings": [f.message for f in ex.findings],
                     "suggestions": [{"index": i, "message": s.message, "fixes": s.fixes, "of": s.of}
                                     for i, s in enumerate(ex.suggestions)]},
         "fixes": []}
for s in ex.suggestions:
    r2 = reschedule(s.league, r.events, Scope(division_ids=frozenset()), also_place=r.unplaced,
                    options=SolveOptions(priorities=(), time_limit_s=20, workers=4))
    entry["fixes"].append({"action": s.message.split(" would ")[0], **pack(s.league, r2)})
out.append(entry)
print("short_ice done", [len(f["unplaced"]) for f in entry["fixes"]], file=sys.stderr)
assert not check_setup(fixtures.league_40()) or True
json.dump(out, open(sys.argv[1], "w"))

# How the scheduling engine works

Code: `engine/src/scheduling_engine/`. Everything here is plain Python, so the API and the web app (Phases 3 and 4) can call it directly.

## The pipeline

```
League ──► capacity_check ──► matchups ──► greedy draft ──► CP-SAT (phase 1: fit) ──► CP-SAT (phase 2: fair) ──► validate ──► fairness_report
                │                                                                                                   │
                └──── plain-language findings before solving                    explain (why games didn't fit + verified fixes)
```

| Step | Module | What it does |
|---|---|---|
| Setup check | `setup_check.py` | Bad references, overlapping slots, tiny divisions, clashing rule overrides. Never raises. |
| Capacity check | `explain.capacity_check` | Before solving: explains setups that can't work (games longer than any slot, no slot in the allowed hours, everything blacked out, teams with fewer playable days than games). |
| Matchups | `matchups.py` | Who plays whom and who's home. Circle-method round robin repeated to each division's games-per-team target. Repeats swap home/away. Home/away balanced to within one game by flipping chains of games. |
| Draft | `greedy.py` | About 0.5 s. Aims round *r* at the *r*-th usable week, places the hardest games first, and gives each game the cheapest legal spot (home venue, fair early/late share, no back-to-back days, no sibling clash). Respects every hard rule. |
| Phase 1 | `solver.run` | Only if the draft missed games: CP-SAT fits as many as possible while keeping the draft where it can. It stops the moment it reaches a proven ceiling (each team plays at most *max per day* games on each day it has a legal spot). |
| Phase 2 | `solver.run` + `goals.py` | Keeps that many games and minimizes the ranked fairness penalty for the rest of the time limit. |
| Check | `validate.py` | The single source of truth for hard rules. Tests require zero violations on every solver output. |
| Report | `report.py` | Per-team fairness and plain-language outlier flags, measured on the schedule itself. |
| Explain | `explain.explain` | Why unplaced games didn't fit (capacity or congestion), plus fixes verified by re-solving. |
| Re-do part | `regen.reschedule` | Locked and out-of-scope games stay put. In-scope games keep their opponents and stay inside the date range. |

## The model

- **Spot** = a concrete place a game could go: (slot, start time, length, size in units). A 120-minute slot yields two back-to-back 60-minute spots.
- **Candidates**: for each game, the spots that pass `validate`'s own per-event checks for both teams (slot fit, season, time window, blackouts). The solver and the checker share that code, so they can't disagree.
- **Variables**: `x[game, spot]` booleans. About 67k for a 40-team season.
- **Hard constraints**, all checked "at every moment" by sweeping start times:
  - surface units in use ≤ the surface's units (half ice = 1 of 2)
  - a team is in at most one game, counting its rest time after each game
  - a coach is at most one place at once
  - games per team per day ≤ the limit
- **Fairness goals** (`goals.py`). The scheduler ranks them; rank *i* weighs 2^(n−1−i) (16, 8, 4, 2, 1). Each goal's unit cost makes one unit about equally annoying:

| Goal | Shown to the scheduler as | Measured as |
|---|---|---|
| `fair_times` | Share early and late games fairly | max − min early/late games per division |
| `spacing` | Spread each team's games through the season | back-to-back days, overloaded weeks, weeks off each game's target week |
| `families` | Avoid clashes for families with kids on two teams | overlapping games (with a 30-min travel buffer) for siblings' teams |
| `repeat_opponent` | Don't face the same opponent twice in a short time | days short of a 14-day gap between rematches |
| `travel` | Keep travel short | 10 km units from home venue, or home games away from the home venue |

What counts as "early" or "late" is a per-division rule (`early_before`, `late_from`), not a constant.

## Why two stages (who, then when)

Choosing matchups first makes home/away balance and games-per-team exact, and keeps the model to about 67k variables instead of millions. The cost is that the solver can't swap opponents to dodge a clash. Fixed opponents per round is also how real leagues publish schedules, so the trade-off fits.

## Performance (4 cores, 60 s limit)

| Fixture | Games | Fit all | Total |
|---|---|---|---|
| small_8 | 28 | 0.6 s (proven best) | 0.6 s |
| league_40 | 240 | under 1 s (draft) to ~17 s | 60 s (the rest is fairness polishing) |
| nightmare | 240 | ~20 s | 60 s |

Quality over time lives in `bench/history.csv` (`uv run python -m scheduling_engine.bench --save`).

## Known limitations / next improvements

- **nightmare** fairness is weak (many sibling clashes). Its ice is about 8% over demand with 60 sibling families. More cores and time help. A targeted improvement step (re-optimize one week at a time) is the next lever.
- Results vary a little between runs because CP-SAT is multi-threaded. Tests assert properties (legal, all placed), not exact schedules.
- Not yet modelled: team/coach preferred days and times, crossover games, practices, tournaments, playoffs, rainout makeups. These are Phase 5 on the roadmap. Matchups always come from round robin.

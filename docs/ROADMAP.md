# Roadmap

Status: **approved 2026-10-14**, Phase 1 in progress. Adjusted from the original brief after the [audit](AUDIT.md).

## Decisions
- **2026-10-14 · Standalone product.** We own the data model for leagues, teams, people and facilities. No dependency on another platform's registration data. CSV import is the on-ramp.
- **2026-10-14 · Engine = Python + OR-Tools CP-SAT** ("best long-term and cheapest"). OR-Tools is free (Apache 2.0). A server is required anyway for publishing, iCal and notifications, so a Python engine adds no hosting cost. It is the only option that can explain infeasible schedules properly.
- **Hosting plan (cheapest that scales):** one container (FastAPI serves the API and the built web app) on a small instance, plus managed Postgres. Solves run in a background worker in the same container until volume justifies splitting it out.

What changed from the brief: the existing code is a single-file browser prototype with no backend or tests, so Phase 1 has to include **standing up the real app skeleton**. The prototype's best UX pieces get ported in Phase 3 rather than rebuilt from scratch.

## Proposed stack (needs your OK)

- **Engine:** Python 3.12 with OR-Tools CP-SAT, as a pure library with no web code inside. Tested with pytest and fixtures.
- **API:** FastAPI wrapping the engine. Solves run as background jobs with progress reporting.
- **DB:** Postgres in production, SQLite for local development and tests, through SQLAlchemy and Alembic.
- **Web:** React + TypeScript + Vite, using the TeamLinkt design tokens (`colors_and_type.css`) as-is.
- **Layout:** `engine/`, `api/`, `web/`, `fixtures/`, `prototype/` (the current dc file, kept as UX reference), `docs/`.

## Phase 1 · Foundation
1. Move the prototype to `prototype/` and fix its asset paths so it opens locally.
2. Scaffold `engine/`, `api/`, `web/` with lint, type checking, test runners, and CI.
3. **Data model:** organization → league → season → divisions → teams; coaches and families (people ↔ teams); venues → surfaces (sport preset, size, splittable, lights); time slots on a surface (length, split unit, cost); blackouts scoped to league, division, team, or venue/surface; rules with league defaults plus division and team overrides; events (game, practice, tournament, one-off) with draft/published state.
4. **Fixtures:** `small_8` (one division, 2 venues), `league_40` (4 divisions × 10, shared venues, half-ice), `nightmare` (tight facility time, many shared coaches, siblings across divisions, blackouts). Each fixture has a generator script and a frozen JSON snapshot.
5. **One validator:** `validate(schedule, league) -> [Violation]` for every hard constraint, with plain-language messages. One test per constraint proves it catches a violation. The UI and the engine will both use it.
6. **Forgiving CSV/Excel import** for teams, coaches, and slots: preview, fuzzy column matching, and per-row problems flagged rather than a failed import.

## Phase 2 · Engine
1. CP-SAT model for all 7 hard constraints. Every fixture run must produce zero validator violations, enforced by tests.
2. Soft constraints, set through a **priority ranking** (drag to reorder "what matters most"). The ranking maps to weights internally.
3. **Explanations:** when the model is infeasible, find the minimal set of conflicting rules and turn it into actions, e.g. "Adding one more Saturday slot at North Arena would resolve 6 of the 8 conflicts" (found by trying a short list of candidate relaxations).
4. **Fairness report** after every run: home/away, early/late slot share, games per team, rest gaps, repeat opponents, with outliers flagged.
5. Locking plus partial regeneration (by division, date range, or "everything not locked").
6. **Quality tracking:** `make bench` runs every fixture and appends metrics (solve time, violations, fairness scores) to `bench/history.csv`. Regressions fail CI.

## Phase 3 · Scheduler experience
Port the prototype's board, availability builder, capacity check, conflict modal, and reports. Add: season calendar plus views by team, venue, and division; drag-and-drop with live validator checks; draft vs published; undo/redo for every action; save and clone a season template.

## Phase 4 · Families and coaches
Mobile-first public schedule pages with no login, per-team iCal feeds, change notifications only to affected teams (built from the publish diff), and coach conflict or change requests.

## Phase 5 · Season reality
Rainout/closure handling with ranked makeup suggestions (least disruption first), practices from the shared pool ("2 per week, 1 on a weekday"), crossover games, and playoff brackets seeded from standings.

## Phase 6 · Extras
Referee and official assignment, facility cost tracking, multi-league organizations, a public API.

## Progress
- [x] Phase 1.1 Prototype moved to `prototype/`, asset paths fixed.
- [x] Phase 1.2 `engine/` scaffold with lint, strict types, tests, CI. (`api/` and `web/` get scaffolded when first needed, in Phase 2 and 3.)
- [x] Phase 1.3 Data model (`engine/src/scheduling_engine/model.py`).
- [x] Phase 1.4 Fixtures `small_8`, `league_40`, `nightmare` (feasibility of `nightmare` confirmed in Phase 2).
- [x] Phase 1.5 Hard-constraint checker plus setup checks, with one test group per constraint.
- [x] Phase 1.6 Forgiving CSV/Excel import for teams (with coach columns), coaches and time slots (`engine/src/scheduling_engine/importer/`). Families/siblings import comes with rosters in Phase 4.

**Phase 1 complete.**

- [x] Phase 2.1 Matchups: round robin to games-per-team target, home/away balanced within one.
- [x] Phase 2.2 CP-SAT placement with all 7 hard rules; fit-first then fairness; greedy draft; proven ceiling.
- [x] Phase 2.3 Five ranked fairness goals (plain-language labels, rank → weight).
- [x] Phase 2.4 Fairness report with outlier flags.
- [x] Phase 2.5 Locking and partial regeneration (division / date range).
- [x] Phase 2.6 Explanations: capacity check, why games didn't fit, fixes verified by re-solving.
- [x] Phase 2.7 Quality benchmark (`bench/history.csv`).

**Phase 2 complete.** Design: `docs/ENGINE.md`. Open engine work: fairness on very tight leagues (nightmare), team/coach preferred days and times (needs a model field), rainout makeups (Phase 5).

- [x] Phase 3.1 API: versioned seasons (undo/redo), import preview/apply, generate jobs with progress, live move check, move/lock, explain + one-click fixes, publish with change log, copy setup to a new season.
- [x] Phase 3.2 Change log between schedules (`engine/changes.py`), with the teams affected.
- [x] Phase 3.3 Web app: Home, Setup (imports, rules with advanced toggle, blackouts, copy setup), Schedule (generate with ranked priorities, date board with drag and drop and live green/red checks, lock, by-team view, didn't-fit panel), Fairness, Publish, undo/redo.
- [x] Phase 3.4 End-to-end test (`web/e2e/flow.mjs`) covering sample → generate → drag → undo → lock → fairness → publish → import.

Still open in Phase 3: a week and month overview (the board shows one day), a by-venue list view, editing teams and slots one at a time in the UI (today: import or sample), deleting things with an undoable confirmation, user accounts and sign-in (single-scheduler for now), and running the e2e test in CI.

**2026-10-15 · Phase 4 (families and coaches) skipped for now** at the product owner's request. The change log already records which teams each change affects, so notifications can be added later without rework.

## Phase 3b · After the build (approved 2026-10-23)
From the product owner's "next steps" list. Order agreed: manage the schedule after it's built first, then views and reporting, then real-world seasons, then AI help.

Defaults taken while the open questions are pending: a coach's "unavailable" times are a firm rule and their preferences are soft; spreadsheet publishing starts as an Excel/CSV download; AI features wait until the Claude API cost question is answered.

**Step 1 · Managing the schedule after it's built**
- [x] 1. "Needs a spot" tray: games that didn't fit stay as matchups; pick one and the open spots light up, best three marked "Suggested" (legal by `validate`, ranked by fairness).
- [x] 2. "Build matchups only": every game goes to the tray for hand placement, with the same suggestions. Also "Take off the schedule" to send a game back to the tray.
- [x] 3. Lock (and unlock) a whole day, week, venue or division in one undoable step.
- [x] 4. Add and edit teams, venues and available times in the app, not only by import.
- [x] 5. Coach restrictions: unavailable days and times (firm), preferred times (soft, shown in the fairness report).

**Step 2 · Views and reporting**
- [ ] 6. Week and month calendars, by-venue view, and an events summary table per team (games and practices, published and unpublished, home/away, division filter, search).
- [ ] 7. Fuller fairness summary: per division and per team, outliers highlighted, "what stands out" notes.
- [ ] 8. Publish to a spreadsheet (Excel download: full schedule plus a sheet per team).

**Step 3 · Real-world seasons**
- [ ] 9. Import existing games and practices (preview then apply; imported games are locked and scheduled around).
- [ ] 10. Practice scheduling from the same facility pool.

**Step 4 · AI help** (needs a decision on the Claude API cost)
- [ ] 11. Rule setter: type a rule in plain words, confirm the rule changes it understood.
- [ ] 12. Improvement suggestions, each verified by re-running the schedule before it's shown.

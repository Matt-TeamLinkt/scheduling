# Phase 0 audit

Date: 2026-10-14. Audited commit: `a33b0d0` ("Add files via upload"), the only commit in the repo.

## 1. What's actually here

This repo is **a design prototype, not an application codebase.** It holds:

| File | What it is |
|---|---|
| `Scheduling Workspace.dc.html` | The whole product: one Claude Design "dc" file, with about 500 lines of template and about 620 lines of logic in a `Component extends DCLogic` class. |
| `support.js` | Generated dc runtime (marked "do not edit"). At page load it pulls React 18.3.1 and Babel standalone from unpkg and compiles the template in the browser. |
| `_ds_bundle.js`, `colors_and_type.css`, `_ds_manifest.json`, `_adherence.oxlintrc.json`, `*.ttf`, `check.png`, `README.md` | TeamLinkt design system export: tokens, Be Vietnam Pro fonts, a lint config for token use, and an unused component bundle (Button, Card, ScheduleGrid, …). |

- **Stack:** browser only. There's no server, database, auth, build step, package manifest, or tests.
- **Persistence:** one `localStorage` key (`tl_sched_v1`), so data lives in one browser on one machine.
- **Doesn't run as uploaded.** The HTML loads `_ds/teamlinkt-design-system-019dd02c-…/colors_and_type.css` and `…/_ds_bundle.js`, and the CSS loads `fonts/*.ttf`. None of those paths exist (the files sit at the repo root), so the page renders unstyled. It also depends on unpkg at runtime. I verified it works after moving the files into the expected layout (see CLAUDE.md).

### Data model (implicit, in component state)
`season{start,end}`, `settings{gamesPerTeam, defaultDuration, divisionOnly}`, `divisions[{id,name,duration,color}]`, `tiers[]`, `zones[]`, `teams[{divisionId,tierId,zoneId,homeFacilityId}]`, `coaches[{teamIds[]}]`, `facilities[{id,name}]`, `slots[{facilityId,date,start,end}]`, `blackouts[{date, scope: 'global'|facilityId|divisionId, note}]`, `pool[]` (unscheduled matchups), `placements[]` (matchup + slotId + overrides), `conflictLog[]`.

### How "scheduling" works today
1. **Generate** builds a pool of *matchups only*, using a greedy pair picker per division+tier group. It aims for the games-per-team target, penalizes repeat pairings and cross-zone pairs, and skips any pair of teams that share a coach.
2. The scheduler **drags every game by hand** into a slot.
3. On drop, `checkPlacement` warns about: slot already taken, blackout, cross-zone, game longer than the slot, and coach overlap. The scheduler can "Place anyway", and that override is logged.

**There is no automatic slot assignment.** For 40 teams × 10 games, that's about 200 manual drags.

## 2. What works and is worth keeping

These are good product ideas, and the code is clear enough to port:
- **Availability builder:** "every Saturday 9–5, 60-minute slots, 10-minute gap" turns into a slot list with a live preview ("24 slots · 6 per day across 4 dates · skips 1 blackout date"). This is exactly the right level of abstraction for a volunteer.
- **Capacity check:** "Short on room: 120 games needed but only 96 slots. Add about 24 more." This is the seed of the "explain itself" feature.
- **Plain-language conflict modal** with an override log. Good tone, and it already matches the vision.
- **Reports panel:** games per team against target, a team-vs-team matrix, an in-zone vs cross-zone split, and games per location. This is an early fairness report.
- **Tiers and zones** are real league concepts. A zone is a reasonable stand-in for travel until we have geography.
- **Visual language:** it follows the TeamLinkt design system closely (tokens, type, tone).

## 3. Bugs and fragile spots (all verified by running the code)

| # | Severity | Finding |
|---|---|---|
| B1 | **Critical** | **A team can be double-booked.** `checkPlacement` only catches overlaps through a *shared coach*. A team with no coach on file can be placed at 9:00 on two fields with no warning. When the team does have a coach, the warning says "coach conflict", which is misleading. This breaks hard constraint #1. |
| B2 | **High** | **Silent data change on every reload.** `migrate()` gives a tier and zone to any team that has none, so a team the scheduler set to "None" gets moved back into Tier 1 / North on the next page load. If the scheduler deletes all tiers or zones, the defaults come back. |
| B3 | **High** | **Silent data loss on delete.** Deleting a facility deletes its slots *and every game placed in them*. Those games aren't returned to the pool. Deleting a division deletes its teams. Neither asks for confirmation, and there's no undo. |
| B4 | **High** | **The generator gives degenerate results when groups are small.** Matchups are only made inside a division+tier group. The sample league has 2 teams per group, so Generate makes **Falcons v Rovers six times**. Nothing warns the scheduler. |
| B5 | Medium | **Teams that share a coach never play each other**, and this happens silently. In a 3-team group where two teams share a coach, those two get 2 games each against a target of 4, with no explanation. |
| B6 | Medium | **Overlapping slots are allowed on the same surface.** The availability builder only removes a duplicate when the start time is identical. A 75-minute pattern laid over existing 60-minute slots creates overlaps such as 09:30–10:45 against 09:00–10:00, which means two games on one field. |
| B7 | Medium | Placed games lose `tierId`, because `applyPlacement` and `removePlacement` don't copy it. The tier chip disappears until reload, when `migrate` puts it back from team A. |
| B8 | Low | The date header shows "Blackout date" for any blackout on that date, even a single-facility or single-division one. The season start and end dates aren't enforced on slots. |
| B9 | Low | `Generate` replaces the whole pool, including matchups the scheduler added by hand. |
| B10 | Low | The capacity check counts slots rather than minutes. It ignores division durations, blackouts, and whether a slot is long enough. |

## 4. Gaps against the vision

| Area | Status |
|---|---|
| Hard constraints | #1 team overlap: **missing** (B1). #2 surface sizing or splitting: **missing**. #3 blackouts: league/facility/division only, **no team-level**, and they're warnings rather than rules. #4 only in slots: yes, by construction. #5 coach overlap: **yes** (only for manual drops). #6 minimum rest: **missing**. #7 age time windows: **missing**. |
| Soft constraints | Repeat-opponent and cross-zone penalties exist, but only when picking matchups. Home/away, time-slot fairness, spacing, siblings, preferences, and back-to-back opponents are **missing**. There's no home/away concept at all: `homeFacilityId` is shown but never used. |
| Engine | No solver, no slot assignment, no explanations beyond the drop modal, no locking or partial regeneration, no rainouts. |
| Event types / formats | Games only. No practices, tournaments, crossovers, or playoffs. |
| Facilities | A facility is just a name. No venues→surfaces, sizes, splitting, lights, cost, or address. |
| Customization | One league-level settings block. No division or team overrides, no templates, no "advanced" layer. |
| Import | **Missing.** Everything is typed in by hand. |
| Experience | One date at a time per facility. No team/division/season views, draft/publish, change log, notifications, public pages, iCal, PDF/CSV export, or undo. |
| Users | Single user, single browser. No coach or parent access. |
| Quality | **No tests, fixtures, or metrics tracking.** |

## 5. Architecture decisions that will block us

1. **The dc single-file format can't hold a product.** All logic, view-model, and styling live in one class inside an HTML script tag, compiled by Babel in the browser. There's no module system, no type checking, and no way to unit test except by scraping the script out (I did that for this audit). Every feature in Phases 2 to 6 would make this harder.
2. **No server.** Publishing, public schedule pages, iCal feeds, notifications, coach requests, and multi-user access all need a backend and a database. That covers most of Phases 3 to 6.
3. **localStorage is the only copy of a league's season.** Clearing browser data or switching laptops loses everything.
4. **The engine doesn't belong in the browser.** CP-SAT isn't available in JavaScript in any production-grade form. A 40-team solve also shouldn't block the UI thread.
5. **UI checks and engine rules would be separate implementations.** Today the "rules" are just the drop warnings. If drag-and-drop checks and the solver use different code, they will disagree. We need **one validator** that both the engine tests and the UI call.

**Recommendation:** keep the prototype in `prototype/` as the UX reference, and build the product as a proper app that ports its interaction patterns and design tokens. This is a rebuild of the code but not of the product thinking, and I'd reuse the availability builder, capacity check, conflict copy, and reports almost one to one.

## 6. Engine tradeoff: CP-SAT vs heuristic

| | **OR-Tools CP-SAT (Python)** — recommended | Heuristic + local search (TypeScript) |
|---|---|---|
| Hard constraints | Guaranteed, because the solver proves them. | Best effort. Needs a separate repair step. |
| Soft constraints | Weighted objective. Priority ranking maps cleanly to weights. | Hand-tuned scoring. Quality is fragile. |
| "Why can't it fit?" | Solve with assumption literals and get an **unsat core**: the minimal set of rules in conflict. That turns into "these 6 games can't fit because…". | Has to be inferred after the fact. Usually vague. |
| Partial regen / locking | Fix the locked variables and re-solve. Easy. | Possible, but complex. |
| 40 teams in under a minute | Yes. About 200 games × a few hundred slots is a small model. Time-limited solve with progress callbacks. | Yes. |
| Runs offline / in browser | No. Needs a server. | Yes. |
| Cost | Adds Python to the stack. | Single language, much more engine code to write and maintain. |

We need a server anyway (see §5.2), so the main argument for a browser heuristic goes away. **I recommend a Python engine on CP-SAT behind a small API.** It's the only option that meets the "explain itself" requirement properly.

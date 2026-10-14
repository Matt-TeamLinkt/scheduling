# CLAUDE.md

## Product
A youth sports scheduling tool for volunteer league schedulers (typically ~40 teams across several divisions, working at night after work). Load teams and facility time, set rules, generate a fair schedule in minutes, fix problems with a click, publish to families. The two guiding words are **easy** and **customizable**: smart defaults on the main path, optional depth behind "advanced" or per-division settings. Plain language everywhere. Never use solver jargon in the UI.

Primary user: the league scheduler. Then coaches, parents/players, and later referee assignors.

## Current state (as of Phase 0, 2026-10-14)
- The repo is a **design prototype**, not an app yet. See `docs/AUDIT.md` for the full audit and `docs/ROADMAP.md` for the plan (awaiting approval).
- `prototype/Scheduling Workspace.dc.html`: a single-file Claude Design "dc" prototype, kept as the UX reference. All logic is in the `Component` class in the `<script data-dc-script>` block. State is in `localStorage` key `tl_sched_v1`.
- `prototype/support.js`: generated dc runtime. **Do not edit.** It loads React 18.3.1 and Babel from unpkg at runtime.
- `design-system/`: TeamLinkt design system (tokens in `colors_and_type.css`, fonts in `fonts/`). `design-system/README.md` is the **brand and voice guide**: sentence case, no emoji, `--tl-*` tokens, Be Vietnam Pro, Material Symbols Rounded. Follow it for all UI.
- No backend, build, package manifest, or tests exist yet.

## Running the prototype
```sh
python3 -m http.server 8000   # from the repo root; open http://localhost:8000/prototype/Scheduling%20Workspace.dc.html
```
It needs unpkg.com reachable. In the cloud sandbox unpkg is blocked; get React with `npm pack react@18.3.1 react-dom@18.3.1 @babel/standalone@7.29.0` and serve it through Playwright `page.route`. Chromium is at `/opt/pw-browsers`. Don't run `playwright install`.

## Testing the prototype logic
There are no tests yet. For a quick check, pull the script block out of the HTML and run it in Node with a stub `class DCLogic { setState(u){…} }`, then call `seed()`, `genPool()`, `checkPlacement()` and `avBuild()` directly.

## Working conventions
- Plan before coding anything bigger than a small fix, and wait for approval.
- Work in small, testable increments. Commit after each working step. Work on a branch, never directly on `main`.
- Every hard constraint gets a test proving it's never violated. Run the fixtures (small 8-team, 40-team multi-division, nightmare) on every engine change once they exist.
- Don't silently rewrite working code. Explain why a refactor is needed and what it unlocks.
- When a requirement conflicts with how the app is built, flag it and recommend a path.
- Keep this file updated as the stack lands (how to run, how to test, layout).

## Known issues to keep in mind
Team double-booking isn't detected (only coach overlap is). `migrate()` overwrites "no tier/zone" on reload. Deleting a facility or division silently deletes games or teams. Details: `docs/AUDIT.md` §3.

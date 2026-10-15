# Scheduling

A youth sports scheduling tool for league schedulers: load teams and facility time, set rules, generate a fair schedule in minutes, fix problems with a click, publish to families.

| Folder | What's in it |
|---|---|
| `engine/` | Python scheduling engine: data model, rule checks, solver (Phase 2). |
| `fixtures/` | Realistic test leagues used by every engine test. |
| `prototype/` | The original single-file UX prototype, kept as the design reference. |
| `design-system/` | TeamLinkt brand tokens, fonts and the voice guide. |
| `docs/` | Audit, roadmap, decisions. |

## Try it

You need [uv](https://docs.astral.sh/uv/getting-started/installation/) and [Node.js](https://nodejs.org) 20 or newer.

```sh
git clone https://github.com/Matt-TeamLinkt/scheduling.git
cd scheduling
git checkout phase-3-app
./start.sh          # then open http://localhost:8000
```

Pick a sample league ("Try it"), press **Generate schedule**, then drag games around, check the Fairness tab and publish. Your seasons are saved in `api/data/`.

See `CLAUDE.md` for how to run and test everything.

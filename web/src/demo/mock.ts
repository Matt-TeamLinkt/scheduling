// Preview mode: answers the app's /api calls inside the browser, so the real UI can be
// shared as a static page. Schedules, fairness reports and explanations were made
// ahead of time by the real engine and loaded from demo-data.json next to the page. The drag check
// here is a simplified copy of the engine's rules, good enough to try the app.
// Built only with VITE_DEMO=1; the real app never loads this file.
import type { Blackout, GameEvent, League, Matchup } from "../api";
import { fmtDay, fmtTime, minutes } from "../format";

interface Sample {
  id: string; description: string; league: League; events: GameEvent[]; unplaced: Matchup[];
  report: unknown; capacity?: string[];
  explain?: { summary: string; findings: string[]; suggestions: { index: number; message: string; fixes: number; of: number }[] };
  fixes?: { action: string; league: League; events: GameEvent[]; unplaced: Matchup[]; report: unknown }[];
}
let SAMPLES: Sample[] = [];
const GOALS = [
  { id: "fair_times", label: "Share early and late games fairly" },
  { id: "spacing", label: "Spread each team's games through the season" },
  { id: "families", label: "Avoid clashes for families with kids on two teams" },
  { id: "repeat_opponent", label: "Don't face the same opponent twice in a short time" },
  { id: "travel", label: "Keep travel short" },
];

interface Version { action: string; league: League; events: GameEvent[]; unplaced: Matchup[]; report: unknown; fixedBy?: number }
interface Pub { version: number; published_at: string; changes: { kind: string; message: string }[] }
interface SeasonState { id: string; name: string; sample: Sample | null; versions: Version[]; current: number; published: number | null; pubs: Pub[] }

const seasons = new Map<string, SeasonState>();
const jobs = new Map<string, { polls: number; seasonId: string; finish: () => Record<string, unknown> }>();
let counter = 0;
const newId = () => `demo${++counter}`;
const clone = <T,>(x: T): T => JSON.parse(JSON.stringify(x));
const cur = (s: SeasonState) => s.versions[s.current];

function commit(s: SeasonState, v: Partial<Version> & { action: string }) {
  const base = cur(s);
  s.versions = s.versions.slice(0, s.current + 1);
  s.versions.push({ league: base.league, events: base.events, unplaced: base.unplaced, report: base.report, ...v });
  s.current = s.versions.length - 1;
}

// ── plain-language helpers ──
const teamName = (lg: League, id: string | null) => lg.teams.find((t) => t.id === id)?.name ?? "?";
const place = (lg: League, slotId: string) => {
  const sl = lg.slots.find((x) => x.id === slotId);
  const sf = sl && lg.surfaces.find((x) => x.id === sl.surface_id);
  const v = sf && lg.venues.find((x) => x.id === sf.venue_id);
  return !sf ? "?" : v && v.name !== sf.name ? `${v.name} ${sf.name}` : sf.name;
};
const what = (lg: League, e: GameEvent) => `${teamName(lg, e.home_team_id)} vs ${teamName(lg, e.away_team_id)}`;
const describe = (lg: League, e: GameEvent) => `${what(lg, e)}, ${fmtDay(e.start)} at ${fmtTime(e.start)} at ${place(lg, e.slot_id)}`;
const endMin = (e: GameEvent) => minutes(e.start) + e.minutes;
const sameDay = (a: GameEvent, b: GameEvent) => a.start.slice(0, 10) === b.start.slice(0, 10);
const overlap = (a: GameEvent, b: GameEvent) => sameDay(a, b) && minutes(a.start) < endMin(b) && minutes(b.start) < endMin(a);

function rules(lg: League, teamId: string) {
  const t = lg.teams.find((x) => x.id === teamId);
  const d = lg.divisions.find((x) => x.id === t?.division_id);
  const pick = <K extends keyof League["rules"]>(k: K) =>
    (t?.rules[k] ?? d?.rules[k] ?? lg.rules[k]) as League["rules"][K];
  return {
    perDay: pick("max_games_per_day"), earliest: minutes(pick("earliest_start")),
    latest: minutes(pick("latest_end")), restMin: pick("min_rest_minutes"),
  };
}

function blackoutHits(lg: League, b: Blackout, e: GameEvent): boolean {
  const day = e.start.slice(0, 10);
  if (day < b.start_date || day > b.end_date) return false;
  const sl = lg.slots.find((x) => x.id === e.slot_id);
  const sf = sl && lg.surfaces.find((x) => x.id === sl.surface_id);
  switch (b.scope) {
    case "league": return true;
    case "division": return e.division_id === b.target_id;
    case "team": return e.home_team_id === b.target_id || e.away_team_id === b.target_id;
    case "venue": return sf?.venue_id === b.target_id;
    case "surface": return sf?.id === b.target_id;
  }
  return false;
}

/** Simplified version of the engine's validate(): problems involving `moved`. */
function check(lg: League, events: GameEvent[], moved: GameEvent): string[] {
  const out: string[] = [];
  const slot = lg.slots.find((x) => x.id === moved.slot_id)!;
  if (endMin(moved) > minutes(slot.end)) {
    out.push(`${describe(lg, moved)} runs past the end of the time slot (${fmtTime(slot.end)}).`);
  }
  const others = events.filter((e) => e.id !== moved.id);
  const surface = lg.surfaces.find((x) => x.id === slot.surface_id)!;
  const onSurface = others.filter((e) => lg.slots.find((x) => x.id === e.slot_id)?.surface_id === surface.id && overlap(e, moved));
  if (onSurface.reduce((n, e) => n + e.units, moved.units) > surface.units) {
    out.push(`${place(lg, moved.slot_id)} is already taken then: ${onSurface.map((e) => what(lg, e)).join("; ")}.`);
  }
  for (const t of [moved.home_team_id, moved.away_team_id].filter(Boolean) as string[]) {
    const r = rules(lg, t);
    const theirs = others.filter((e) => e.home_team_id === t || e.away_team_id === t);
    const clash = theirs.find((e) => overlap(e, moved));
    if (clash) out.push(`${teamName(lg, t)} are booked twice at the same time: ${describe(lg, clash)}.`);
    else if (theirs.filter((e) => sameDay(e, moved)).length + 1 > r.perDay) {
      out.push(`${teamName(lg, t)} already play on ${fmtDay(moved.start)}. The limit is ${r.perDay} game${r.perDay === 1 ? "" : "s"} a day.`);
    }
    if (minutes(moved.start) < r.earliest || endMin(moved) > r.latest) {
      out.push(`${teamName(lg, t)} should only play between ${fmtTime(`${Math.floor(r.earliest / 60)}:${String(r.earliest % 60).padStart(2, "0")}`)} and ${fmtTime(`${Math.floor(r.latest / 60)}:${String(r.latest % 60).padStart(2, "0")}`)}.`);
    }
  }
  for (const c of lg.coaches.filter((c) => c.team_ids.length > 1)) {
    const mine = c.team_ids.filter((t) => t === moved.home_team_id || t === moved.away_team_id);
    if (!mine.length) continue;
    const clash = others.find((e) => overlap(e, moved) && c.team_ids.some((t) => (t === e.home_team_id || t === e.away_team_id) && !mine.includes(t)));
    if (clash) out.push(`${c.name} coaches in two places at once: ${describe(lg, clash)}.`);
  }
  for (const b of lg.blackouts) if (blackoutHits(lg, b, moved)) out.push(`${fmtDay(moved.start)} is a blackout${b.note ? ` (${b.note})` : ""}.`);
  return out;
}

function diff(lg: League, before: GameEvent[], after: GameEvent[]) {
  const old = new Map(before.map((e) => [e.id, e]));
  const out: { kind: string; message: string; teams: (string | null)[] }[] = [];
  for (const e of after) {
    const o = old.get(e.id);
    const teams = [e.home_team_id, e.away_team_id];
    if (!o) out.push({ kind: "added", teams, message: `New: ${describe(lg, e)}.` });
    else if (o.start !== e.start || o.slot_id !== e.slot_id) {
      out.push({ kind: "moved", teams, message: `${what(lg, e)} moved from ${fmtDay(o.start)} at ${fmtTime(o.start)} at ${place(lg, o.slot_id)} to ${fmtDay(e.start)} at ${fmtTime(e.start)} at ${place(lg, e.slot_id)}.` });
    }
  }
  const now = new Set(after.map((e) => e.id));
  for (const o of before) if (!now.has(o.id)) out.push({ kind: "cancelled", teams: [o.home_team_id, o.away_team_id], message: `Cancelled: ${describe(lg, o)}.` });
  return out;
}

function out(s: SeasonState, message: string | null = null) {
  const v = cur(s);
  const pubEvents = s.published === null ? [] : s.versions[s.published].events;
  return {
    id: s.id, name: s.name, version: s.current + 1, last_action: v.action,
    can_undo: s.current > 0, can_redo: s.current < s.versions.length - 1,
    published_version: s.published === null ? null : s.published + 1,
    unpublished_changes: diff(v.league, pubEvents, v.events).length,
    league: v.league, events: v.events, unplaced: v.unplaced, goals: GOALS, message,
  };
}

class HttpError extends Error { constructor(public status: number, msg: string) { super(msg); } }

function route(method: string, path: string, body: Record<string, unknown> | null): unknown {
  const p = path.split("/").filter(Boolean); // ["seasons", id, ...]
  if (path === "/samples") return SAMPLES.map((s) => ({ id: s.id, description: s.description }));
  if (path === "/seasons" && method === "GET") {
    return [...seasons.values()].reverse().map((s) => ({ id: s.id, name: s.name, created_at: "", published: s.published !== null }));
  }
  if (path === "/seasons" && method === "POST") {
    const sample = SAMPLES.find((x) => x.id === body?.sample) ?? null;
    const league: League = sample ? clone(sample.league) : {
      id: "league", name: String(body?.name), sport: String(body?.sport ?? "other"), timezone: "America/Toronto",
      season_start: String(body?.season_start), season_end: String(body?.season_end),
      rules: { games_per_team: 10, game_minutes: 60, units: null, min_rest_minutes: 0, max_games_per_day: 1,
        earliest_start: "08:00:00", latest_end: "21:00:00", early_before: "08:00:00", late_from: "20:30:00" },
      divisions: [], teams: [], coaches: [], families: [], venues: [], surfaces: [], slots: [], blackouts: [],
    };
    const s: SeasonState = {
      id: newId(), name: String(body?.name), sample, current: 0, published: null, pubs: [],
      versions: [{ action: sample ? `Started from the sample: ${sample.description}` : "Created the season", league, events: [], unplaced: [], report: null }],
    };
    seasons.set(s.id, s);
    return out(s);
  }
  if (p[0] === "jobs") {
    const j = jobs.get(p[1]);
    if (!j) throw new HttpError(404, "That job doesn't exist.");
    j.polls++;
    if (j.polls < 3) return { state: "running", phase: j.polls < 2 ? "placing" : "improving", placed: j.polls < 2 ? 180 : 240, total: 240, seconds: j.polls, message: j.polls < 2 ? "Fitting games into your time slots…" : "Every game that can fit is in. Making the schedule fairer…", result: {} };
    const result = j.finish();
    jobs.delete(p[1]);
    return { state: "done", phase: "done", placed: 0, total: 0, seconds: 3, message: String(result.summary), result };
  }
  const s = seasons.get(p[1]);
  if (!s) throw new HttpError(404, "That season doesn't exist.");
  const v = cur(s);
  const action = p[2];
  const startJob = (finish: () => Record<string, unknown>) => {
    const id = newId();
    jobs.set(id, { polls: 0, seasonId: s.id, finish });
    return { job_id: id };
  };

  switch (action) {
    case undefined: return out(s);
    case "league":
      commit(s, { action: String(body?.action ?? "Changed the season setup"), league: body?.league as League });
      return out(s);
    case "setup-check": return { problems: [], capacity: s.sample?.capacity ?? [] };
    case "import": throw new HttpError(400, "Importing your own files needs the full app. In this preview, start from one of the sample leagues.");
    case "clone": throw new HttpError(400, "Copying a setup needs the full app.");
    case "generate":
      return startJob(() => {
        if (!s.sample) return { summary: "This preview can only generate the sample leagues. Add teams and slots in the full app.", placed: 0 };
        if (v.events.length && !body?.fresh) return { summary: "This is already the best schedule the engine found for this sample." };
        const smp = s.sample;
        commit(s, { action: "Generated the schedule", events: clone(smp.events), unplaced: clone(smp.unplaced), report: smp.report });
        return { summary: smp.unplaced.length ? `${smp.events.length} games scheduled. ${smp.unplaced.length} didn't fit; see why and how to fix it.` : `All ${smp.events.length} games scheduled.` };
      });
    case "check": case "move": {
      const old = v.events.find((e) => e.id === body?.event_id)!;
      const slot = v.league.slots.find((x) => x.id === body?.slot_id)!;
      const moved: GameEvent = { ...old, slot_id: slot.id, start: String(body?.start).slice(0, 19) };
      const events = v.events.map((e) => (e.id === old.id ? moved : e));
      const problems = check(v.league, events, moved);
      if (action === "check") return { ok: !problems.length, problems };
      commit(s, { action: `Moved ${describe(v.league, moved)}`, events });
      return { ...out(s), problems };
    }
    case "events": {
      const locked = Boolean(body?.locked);
      const events = v.events.map((e) => (e.id === p[3] ? { ...e, locked } : e));
      const e = events.find((x) => x.id === p[3])!;
      commit(s, { action: `${locked ? "Locked" : "Unlocked"} ${describe(v.league, e)}`, events });
      return out(s);
    }
    case "undo": {
      if (s.current === 0) throw new HttpError(400, "There's nothing to undo.");
      const undone = v.action;
      s.current--;
      return out(s, `Undid: ${undone}`);
    }
    case "redo": {
      if (s.current >= s.versions.length - 1) throw new HttpError(400, "There's nothing to redo.");
      s.current++;
      return out(s, `Redid: ${cur(s).action}`);
    }
    case "report":
      return v.report ?? { summary: "Generate a schedule first.", teams: [], flags: [], family_clashes: [] };
    case "explain":
      if (!v.unplaced.length) return { summary: "Every game fits.", findings: [], suggestions: [] };
      return s.sample?.explain && v.fixedBy === undefined ? s.sample.explain : { summary: `${v.unplaced.length} games didn't fit.`, findings: [], suggestions: [] };
    case "publish-preview": {
      const before = s.published === null ? [] : s.versions[s.published].events;
      const changes = diff(v.league, before, v.events);
      const teams = new Set(changes.flatMap((c) => c.teams).filter(Boolean));
      return { changes: changes.map(({ kind, message }) => ({ kind, message })), teams_affected: teams.size };
    }
    case "publish": {
      const before = s.published === null ? [] : s.versions[s.published].events;
      const changes = diff(v.league, before, v.events).map(({ kind, message }) => ({ kind, message }));
      s.published = s.current;
      s.pubs.unshift({ version: s.current + 1, published_at: new Date().toISOString(), changes });
      return out(s, `Published. ${changes.length} changes went out.`);
    }
    case "publications": return s.pubs;
  }
  throw new HttpError(404, "Not available in the preview.");
}

function applySuggestion(seasonId: string, index: number) {
  const s = seasons.get(seasonId)!;
  const fix = s.sample?.fixes?.[index];
  if (!fix) throw new HttpError(400, "Refresh the suggestions and try again.");
  const id = newId();
  jobs.set(id, {
    polls: 0, seasonId,
    finish: () => {
      commit(s, { action: fix.action, league: clone(fix.league), events: clone(fix.events), unplaced: clone(fix.unplaced), report: fix.report, fixedBy: index });
      return { summary: fix.unplaced.length ? `${fix.events.length} games scheduled. ${fix.unplaced.length} still didn't fit.` : `All ${fix.events.length} games scheduled.` };
    },
  });
  return { job_id: id };
}

export async function installMockApi() {
  const realFetch = window.fetch.bind(window);
  SAMPLES = await (await realFetch("demo-data.json")).json();
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    const i = url.indexOf("/api/");
    if (i < 0) return realFetch(input, init);
    const path = url.slice(i + 4);
    const method = init?.method ?? "GET";
    const body = typeof init?.body === "string" ? JSON.parse(init.body) : null;
    await new Promise((r) => setTimeout(r, 60));
    try {
      const m = path.match(/^\/seasons\/([^/]+)\/explain\/apply$/);
      const data = m ? applySuggestion(m[1], Number(body?.index)) : route(method, path, body);
      return new Response(JSON.stringify(data), { status: 200, headers: { "Content-Type": "application/json" } });
    } catch (e) {
      const status = e instanceof HttpError ? e.status : 500;
      return new Response(JSON.stringify({ detail: (e as Error).message }), { status, headers: { "Content-Type": "application/json" } });
    }
  };
}

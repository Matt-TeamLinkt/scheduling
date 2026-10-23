// Shapes mirror the engine's pydantic models (engine/src/scheduling_engine/model.py).

export interface RuleSet {
  games_per_team: number;
  game_minutes: number;
  units: number | null;
  min_rest_minutes: number;
  max_games_per_day: number;
  earliest_start: string; // "08:00:00"
  latest_end: string;
  early_before: string;
  late_from: string;
}
export type RuleOverrides = { [K in keyof RuleSet]?: RuleSet[K] | null };

export interface Division { id: string; name: string; rules: RuleOverrides }
export interface Team { id: string; name: string; division_id: string; home_venue_id: string | null; rules: RuleOverrides }
export interface Coach { id: string; name: string; team_ids: string[]; email: string | null; phone: string | null }
export interface Venue { id: string; name: string; address: string | null }
export interface Surface { id: string; venue_id: string; name: string; units: number; lit: boolean }
export interface Slot { id: string; surface_id: string; date: string; start: string; end: string; cost: number | null }
export interface Blackout {
  id: string; scope: string; target_id: string | null; start_date: string; end_date: string;
  start_time: string | null; end_time: string | null; note: string;
}
export interface League {
  id: string; name: string; sport: string; timezone: string;
  season_start: string; season_end: string; rules: RuleSet;
  divisions: Division[]; teams: Team[]; coaches: Coach[]; families: { id: string; name: string; team_ids: string[] }[];
  venues: Venue[]; surfaces: Surface[]; slots: Slot[]; blackouts: Blackout[];
}
export interface GameEvent {
  id: string; kind: "game" | "practice"; division_id: string; home_team_id: string;
  away_team_id: string | null; slot_id: string; start: string; minutes: number; units: number; locked: boolean;
}
export interface Matchup { id: string; division_id: string; home_team_id: string; away_team_id: string; round: number }
export interface SpotChoice {
  slot_id: string; start: string; minutes: number; units: number; score: number;
  good: string[]; watch: string[]; suggested: boolean; problems: string[];
}
export interface Goal { id: string; label: string }

export interface Season {
  id: string; name: string; version: number; last_action: string;
  can_undo: boolean; can_redo: boolean; published_version: number | null; unpublished_changes: number;
  league: League; events: GameEvent[]; unplaced: Matchup[]; goals: Goal[]; message: string | null;
  problems?: string[];
}

export interface ImportPreview {
  summary: string; can_import: boolean;
  columns: { header: string; field: string | null }[];
  problems: { row: number | null; level: "skipped" | "check" | "note"; message: string }[];
  counts: Record<string, number>;
  season?: Season;
}

export interface Job {
  state: "running" | "done" | "failed"; phase: string; placed: number; total: number;
  seconds: number; message: string; result: { summary?: string; notes?: string[]; unplaced?: number };
}

export interface Report {
  summary: string;
  teams: {
    team_id: string; name: string; division: string; games: number; target: number; home: number; away: number;
    early: number; late: number; early_or_late: number; back_to_back_days: number; busiest_week: number;
    longest_gap_days: number; quickest_rematch_days: number | null; travel_km: number; away_from_home_venue: number;
  }[];
  flags: { message: string; team_ids: string[] }[];
  family_clashes: string[];
}

export interface Explanation {
  summary: string; findings: string[];
  suggestions: { index: number; message: string; fixes: number; of: number }[];
}

export interface Change { kind: string; message: string }

export class ApiError extends Error {}

async function call<T>(method: string, path: string, body?: unknown): Promise<T> {
  const init: RequestInit = { method, headers: {} };
  if (body instanceof FormData) init.body = body;
  else if (body !== undefined) {
    init.body = JSON.stringify(body);
    init.headers = { "Content-Type": "application/json" };
  }
  const r = await fetch(`/api${path}`, init);
  if (!r.ok) {
    let msg = "Something went wrong. Please try again.";
    try {
      const d = await r.json();
      if (typeof d.detail === "string") msg = d.detail;
    } catch {
      /* keep the generic message */
    }
    throw new ApiError(msg);
  }
  return r.json() as Promise<T>;
}

export const api = {
  samples: () => call<{ id: string; description: string }[]>("GET", "/samples"),
  seasons: () => call<{ id: string; name: string; created_at: string; published: boolean }[]>("GET", "/seasons"),
  create: (body: { name: string; sample?: string; sport?: string; season_start?: string; season_end?: string }) =>
    call<Season>("POST", "/seasons", body),
  season: (id: string) => call<Season>("GET", `/seasons/${id}`),
  setLeague: (id: string, league: League, action: string) =>
    call<Season>("PUT", `/seasons/${id}/league`, { league, action }),
  setupCheck: (id: string) =>
    call<{ problems: { severity: string; message: string }[]; capacity: string[] }>("GET", `/seasons/${id}/setup-check`),
  importFile: (id: string, kind: string, file: File, apply: boolean) => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("apply", String(apply));
    return call<ImportPreview>("POST", `/seasons/${id}/import/${kind}`, fd);
  },
  generate: (id: string, body: { priorities?: string[]; seconds?: number; fresh?: boolean;
    scope?: { division_ids?: string[] | null; start?: string | null; end?: string | null }; matchups_only?: boolean }) =>
    call<{ job_id: string }>("POST", `/seasons/${id}/generate`, body),
  job: (jobId: string) => call<Job>("GET", `/jobs/${jobId}`),
  check: (id: string, event_id: string, slot_id: string, start: string) =>
    call<{ ok: boolean; problems: string[] }>("POST", `/seasons/${id}/check`, { event_id, slot_id, start }),
  move: (id: string, event_id: string, slot_id: string, start: string) =>
    call<Season>("POST", `/seasons/${id}/move`, { event_id, slot_id, start }),
  lock: (id: string, eid: string, locked: boolean) => call<Season>("POST", `/seasons/${id}/events/${eid}/lock`, { locked }),
  lockMany: (id: string, body: { locked: boolean; day?: string; week_of?: string; venue_id?: string; division_id?: string }) =>
    call<Season>("POST", `/seasons/${id}/lock-many`, body),
  spots: (id: string, mid: string, withProblems = false) =>
    call<SpotChoice[]>("GET", `/seasons/${id}/unplaced/${mid}/spots?with_problems=${withProblems}`),
  unschedule: (id: string, eid: string) => call<Season>("POST", `/seasons/${id}/events/${eid}/unschedule`),
  undo: (id: string) => call<Season>("POST", `/seasons/${id}/undo`),
  redo: (id: string) => call<Season>("POST", `/seasons/${id}/redo`),
  report: (id: string) => call<Report>("GET", `/seasons/${id}/report`),
  explain: (id: string) => call<Explanation>("GET", `/seasons/${id}/explain`),
  applySuggestion: (id: string, index: number) => call<{ job_id: string }>("POST", `/seasons/${id}/explain/apply`, { index }),
  publishPreview: (id: string) => call<{ changes: Change[]; teams_affected: number }>("GET", `/seasons/${id}/publish-preview`),
  publish: (id: string) => call<Season>("POST", `/seasons/${id}/publish`),
  publications: (id: string) =>
    call<{ version: number; published_at: string; changes: Change[] }[]>("GET", `/seasons/${id}/publications`),
  clone: (id: string, name: string, season_start: string) => call<Season>("POST", `/seasons/${id}/clone`, { name, season_start }),
};

/** Poll a background job until it finishes, reporting progress. */
export async function waitForJob(jobId: string, onProgress: (j: Job) => void): Promise<Job> {
  for (;;) {
    const j = await api.job(jobId);
    onProgress(j);
    if (j.state !== "running") return j;
    await new Promise((r) => setTimeout(r, 500));
  }
}

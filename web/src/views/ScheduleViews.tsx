// More ways to look at the same schedule: a week, a month, one venue, and a per-team
// summary table. The day board (Schedule.tsx) is still where games are moved.
import { useEffect, useMemo, useState } from "react";
import type { Ctx } from "../App";
import { api, type GameEvent, type SummaryRow } from "../api";
import { divisionColor, fmtDay, fmtTime, isoDate, Lookup, minutes, parseDate, plural } from "../format";
import { Icon, Note } from "../ui";

type ViewProps = Pick<Ctx, "season" | "toast"> & {
  look: Lookup; day: string; setDay: (d: string) => void; openDay: (d: string) => void; division: string;
};

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function addDays(iso: string, n: number): string {
  const d = parseDate(iso);
  d.setDate(d.getDate() + n);
  return isoDate(d);
}
function mondayOf(iso: string): string {
  return addDays(iso, -((parseDate(iso).getDay() + 6) % 7));
}
function byDay(events: GameEvent[]): Map<string, GameEvent[]> {
  const m = new Map<string, GameEvent[]>();
  for (const e of [...events].sort((a, b) => a.start.localeCompare(b.start))) {
    const d = e.start.slice(0, 10);
    if (!m.has(d)) m.set(d, []);
    m.get(d)!.push(e);
  }
  return m;
}
function isBlackout(season: Ctx["season"], d: string) {
  return season.league.blackouts.some((b) => b.scope === "league" && b.start_date <= d && d <= b.end_date);
}

/** A step-through header: "‹  Week of Mon Jan 4  ›". */
function Stepper({ label, prev, next }: { label: string; prev: () => void; next: () => void }) {
  return (
    <div className="row" style={{ marginBottom: 12 }}>
      <button className="icon-btn" aria-label="Previous" onClick={prev}><Icon name="chevron_left" /></button>
      <h2 style={{ minWidth: 220, textAlign: "center" }}>{label}</h2>
      <button className="icon-btn" aria-label="Next" onClick={next}><Icon name="chevron_right" /></button>
    </div>
  );
}

// ── week ────────────────────────────────────────────────────────────────────

export function WeekView({ season, look, day, setDay, openDay, division }: ViewProps) {
  const monday = mondayOf(day);
  const days = Array.from({ length: 7 }, (_, i) => addDays(monday, i));
  const games = useMemo(() => byDay(season.events), [season.events]);
  const lg = season.league;
  return (
    <div className="grid-scroll">
      <Stepper label={`Week of ${fmtDay(monday)}`} prev={() => setDay(addDays(monday, -7))} next={() => setDay(addDays(monday, 7))} />
      <div className="week">
        {days.map((d) => {
          const list = games.get(d) ?? [];
          return (
            <div key={d} className={`week-day${isBlackout(season, d) ? " blackout" : ""}`}>
              <button className="week-head" onClick={() => openDay(d)} title="Open this day on the board">
                <b>{fmtDay(d)}</b><span className="muted small">{list.length ? plural(list.length, "game") : ""}</span>
              </button>
              {list.map((g) => (
                <div key={g.id} className="mini-game" style={{ borderLeftColor: divisionColor(lg, g.division_id), opacity: division && g.division_id !== division ? 0.3 : 1 }}
                  title={`${look.matchup(g)}\n${look.place(g.slot_id)}`}>
                  <div className="row small" style={{ gap: 4 }}>
                    <b>{fmtTime(g.start)}</b>
                    <span style={{ color: divisionColor(lg, g.division_id) }}>{look.division(g.division_id)}</span>
                    {g.locked && <Icon name="lock" style={{ fontSize: 12, color: "var(--tl-blue)" }} />}
                  </div>
                  <div className="mini-who">{look.matchup(g)}</div>
                  <div className="muted" style={{ fontSize: 11 }}>{look.place(g.slot_id)}</div>
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── month ───────────────────────────────────────────────────────────────────

export function MonthView({ season, look, day, setDay, openDay, division }: ViewProps) {
  const first = `${day.slice(0, 7)}-01`;
  const start = mondayOf(first);
  const month = parseDate(first).getMonth();
  const weeks = useMemo(() => {
    const out: string[][] = [];
    for (let w = start; ; w = addDays(w, 7)) {
      if (out.length && parseDate(w).getMonth() !== month) break;
      out.push(Array.from({ length: 7 }, (_, i) => addDays(w, i)));
      if (out.length > 6) break;
    }
    return out;
  }, [start, month]);
  const games = useMemo(() => byDay(season.events.filter((e) => !division || e.division_id === division)), [season.events, division]);
  const slotDays = useMemo(() => new Set(season.league.slots.map((s) => s.date)), [season.league.slots]);
  const lg = season.league;
  const title = parseDate(first).toLocaleDateString("en-US", { month: "long", year: "numeric" });
  const shift = (n: number) => { const d = parseDate(first); d.setMonth(d.getMonth() + n); setDay(isoDate(d)); };
  return (
    <div className="grid-scroll">
      <Stepper label={title} prev={() => shift(-1)} next={() => shift(1)} />
      <div className="month">
        {WEEKDAYS.map((w) => <div key={w} className="month-dow muted small">{w}</div>)}
        {weeks.flat().map((d) => {
          const list = games.get(d) ?? [];
          const counts = new Map<string, number>();
          for (const g of list) counts.set(g.division_id, (counts.get(g.division_id) ?? 0) + 1);
          const inMonth = parseDate(d).getMonth() === month;
          return (
            <button key={d} className={`month-day${inMonth ? "" : " out"}${isBlackout(season, d) ? " blackout" : ""}${slotDays.has(d) ? " has-time" : ""}`}
              onClick={() => openDay(d)} title={list.length ? `${plural(list.length, "game")}. Click to open the day.` : slotDays.has(d) ? "Time available, no games yet" : ""}>
              <span className="month-num">{parseDate(d).getDate()}</span>
              {list.length > 0 && <span className="month-total">{plural(list.length, "game")}</span>}
              <span className="row wrap" style={{ gap: 3 }}>
                {[...counts.entries()].map(([div, n]) => (
                  <span key={div} className="month-chip" style={{ background: divisionColor(lg, div) }}>{look.division(div)} {n}</span>
                ))}
              </span>
            </button>
          );
        })}
      </div>
      <p className="muted small" style={{ marginTop: 8 }}>Days with available time have a blue edge. Click a day to open it on the board.</p>
    </div>
  );
}

// ── one venue ───────────────────────────────────────────────────────────────

export function VenueView({ season, look, openDay }: ViewProps) {
  const lg = season.league;
  const [venue, setVenue] = useState(lg.venues[0]?.id ?? "");
  const surfaces = new Set(lg.surfaces.filter((s) => s.venue_id === venue).map((s) => s.id));
  const slots = lg.slots.filter((s) => surfaces.has(s.surface_id));
  const slotIds = new Set(slots.map((s) => s.id));
  const games = season.events.filter((e) => slotIds.has(e.slot_id)).sort((a, b) => a.start.localeCompare(b.start));
  const hours = slots.reduce((n, s) => n + (minutes(s.end) - minutes(s.start)) * (lg.surfaces.find((x) => x.id === s.surface_id)?.units ?? 1), 0) / 60;
  const used = games.reduce((n, g) => n + g.minutes * g.units, 0) / 60;
  const days = byDay(games);
  return (
    <div className="grid-scroll">
      <div className="row" style={{ marginBottom: 12 }}>
        <select className="input" value={venue} onChange={(e) => setVenue(e.target.value)} aria-label="Venue">
          {lg.venues.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
        </select>
        <span className="muted small">{plural(games.length, "game")} · {Math.round(used)} of {Math.round(hours)} hours used{lg.surfaces.some((s) => surfaces.has(s.id) && s.units > 1) ? " (half-surface games count half)" : ""}</span>
      </div>
      {games.length === 0 ? <Note>No games at this venue yet.</Note> : (
        <div className="card" style={{ padding: 0 }}>
          <table className="data">
            <thead><tr><th>Date</th><th>Time</th><th>Field</th><th>Division</th><th>Game</th><th></th></tr></thead>
            <tbody>
              {[...days.entries()].map(([d, list]) => list.map((g, i) => (
                <tr key={g.id}>
                  <td>{i === 0 && <button className="link" onClick={() => openDay(d)}>{fmtDay(d)}</button>}</td>
                  <td>{fmtTime(g.start)}</td>
                  <td>{lg.surfaces.find((s) => s.id === lg.slots.find((x) => x.id === g.slot_id)?.surface_id)?.name}</td>
                  <td><span style={{ color: divisionColor(lg, g.division_id), fontWeight: 600 }}>{look.division(g.division_id)}</span></td>
                  <td>{look.matchup(g)}</td>
                  <td>{g.locked && <Icon name="lock" style={{ fontSize: 16, color: "var(--tl-blue)" }} />}</td>
                </tr>
              )))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── events summary: one row per team ────────────────────────────────────────

type SortKey = "name" | "division" | "games" | "published_games" | "unpublished_games" | "practices" | "home" | "waiting";

export function SummaryView({ season, toast }: ViewProps) {
  const [rows, setRows] = useState<SummaryRow[] | null>(null);
  const [division, setDivision] = useState("");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<{ key: SortKey; up: boolean }>({ key: "division", up: true });
  useEffect(() => { api.summary(season.id).then(setRows).catch(() => setRows([])); }, [season.id, season.version, season.published_version]);
  if (!rows) return <div className="grid-scroll"><p className="muted">Loading…</p></div>;

  const divisions = [...new Set(rows.map((r) => r.division))];
  const shown = rows
    .filter((r) => (!division || r.division === division) && r.name.toLowerCase().includes(search.trim().toLowerCase()))
    .sort((a, b) => {
      const x = a[sort.key], y = b[sort.key];
      const c = typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y)) || a.name.localeCompare(b.name);
      return sort.up ? c : -c;
    });
  const practices = rows.some((r) => r.practices > 0);
  const sum = (k: keyof SummaryRow) => shown.reduce((n, r) => n + (r[k] as number), 0);
  const head = (key: SortKey, label: string, num = true) => (
    <th className={num ? "num" : ""}>
      <button className="th-sort" onClick={() => setSort({ key, up: sort.key === key ? !sort.up : true })}>
        {label}{sort.key === key && <Icon name={sort.up ? "arrow_upward" : "arrow_downward"} style={{ fontSize: 14 }} />}
      </button>
    </th>
  );
  return (
    <div className="grid-scroll">
      <div className="row wrap" style={{ marginBottom: 12 }}>
        <select className="input" value={division} onChange={(e) => setDivision(e.target.value)} aria-label="Division">
          <option value="">All divisions</option>
          {divisions.map((d) => <option key={d}>{d}</option>)}
        </select>
        <input className="input" placeholder="Search teams" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search teams" />
        <span className="spacer" />
        <DownloadButton season={season} toast={toast} />
      </div>
      <div className="card" style={{ padding: 0 }}>
        <table className="data">
          <thead>
            <tr>
              {head("name", "Team", false)}{head("division", "Division", false)}
              {head("games", "Games")}{head("published_games", "Published")}{head("unpublished_games", "Not published yet")}
              {practices && head("practices", "Practices")}
              {head("home", "Home / away")}{head("waiting", "Needs a spot")}
            </tr>
          </thead>
          <tbody>
            {shown.map((r) => (
              <tr key={r.team_id}>
                <td style={{ fontWeight: 500 }}>{r.name}</td>
                <td>{r.division}</td>
                <td className={`num${r.games < r.target ? " flag" : ""}`}>{r.games}{r.games < r.target && ` of ${r.target}`}</td>
                <td className="num">{r.published_games}</td>
                <td className="num">{r.unpublished_games || ""}</td>
                {practices && <td className="num">{r.practices}{r.unpublished_practices ? ` (${r.unpublished_practices} new)` : ""}</td>}
                <td className={`num${Math.abs(r.home - r.away) >= 2 ? " flag" : ""}`}>{r.home} / {r.away}</td>
                <td className={`num${r.waiting ? " flag" : ""}`}>{r.waiting || ""}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td style={{ fontWeight: 600 }}>{plural(shown.length, "team")}</td><td />
              <td className="num" style={{ fontWeight: 600 }}>{sum("games")}</td>
              <td className="num">{sum("published_games")}</td>
              <td className="num">{sum("unpublished_games") || ""}</td>
              {practices && <td className="num">{sum("practices")}</td>}
              <td className="num">{sum("home")} / {sum("away")}</td>
              <td className="num">{sum("waiting") || ""}</td>
            </tr>
          </tfoot>
        </table>
      </div>
      <p className="muted small" style={{ marginTop: 8 }}>Each game counts once for each of its two teams, so the totals are twice the number of games.</p>
    </div>
  );
}

export function DownloadButton({ season, toast, which = "draft", label = "Download for Excel" }: Pick<Ctx, "season" | "toast"> & { which?: "draft" | "published"; label?: string }) {
  if (import.meta.env.VITE_DEMO === "1") {
    return <button className="btn btn-ghost" onClick={() => toast("Downloading a spreadsheet needs the full app.")}><Icon name="download" style={{ fontSize: 18 }} />{label}</button>;
  }
  return (
    <a className="btn btn-ghost" href={`/api/seasons/${season.id}/export.xlsx?which=${which}`} download>
      <Icon name="download" style={{ fontSize: 18 }} />{label}
    </a>
  );
}

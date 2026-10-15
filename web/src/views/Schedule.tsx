import { useEffect, useMemo, useRef, useState } from "react";
import type { Ctx } from "../App";
import { api, ApiError, waitForJob, type Explanation, type GameEvent, type Season, type Slot } from "../api";
import { divisionColor, fmtDay, fmtTime, Lookup, minutes, plural } from "../format";
import { Icon, Modal, Note, Progress } from "../ui";
import { GenerateDialog } from "./GenerateDialog";

const PX_PER_MIN = 1.1;

export function Schedule({ season, setSeason, toast }: Ctx) {
  const lg = season.league;
  const look = useMemo(() => new Lookup(lg), [lg]);
  const [generating, setGenerating] = useState(false);
  const [view, setView] = useState<"date" | "team">("date");
  const [division, setDivision] = useState("");
  const dates = useMemo(() => [...new Set(lg.slots.map((s) => s.date))].sort(), [lg.slots]);
  const [day, setDay] = useState<string>(() => season.events[0]?.start.slice(0, 10) ?? dates[0] ?? "");
  useEffect(() => { if (!dates.includes(day) && dates.length) setDay(dates[0]); }, [dates, day]);
  // After a schedule is generated, show the first day that has games.
  const firstGameDay = season.events.reduce<string | null>((m, e) => (!m || e.start < m ? e.start : m), null)?.slice(0, 10);
  const hadGames = useRef(season.events.length > 0);
  useEffect(() => {
    if (!hadGames.current && firstGameDay) setDay(firstGameDay);
    hadGames.current = season.events.length > 0;
  }, [firstGameDay, season.events.length]);

  if (!lg.teams.length || !lg.slots.length) {
    return (
      <div className="page">
        <Note tone="warn">Add your teams and time slots on the Setup tab first. That's all the schedule needs.</Note>
      </div>
    );
  }

  return (
    <div className="board">
      <div className="board-main">
        <div className="board-bar">
          <button className="btn btn-primary" onClick={() => setGenerating(true)}>
            <Icon name="auto_awesome" style={{ fontSize: 18 }} />{season.events.length ? "Generate again" : "Generate schedule"}
          </button>
          <div className="tabs">
            <button className={`tab${view === "date" ? " active" : ""}`} onClick={() => setView("date")}>By date</button>
            <button className={`tab${view === "team" ? " active" : ""}`} onClick={() => setView("team")}>By team</button>
          </div>
          {view === "date" && (
            <select className="input" value={division} onChange={(e) => setDivision(e.target.value)} aria-label="Highlight a division">
              <option value="">All divisions</option>
              {lg.divisions.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
          )}
          <div className="spacer" />
          <span className="muted small">{plural(season.events.length, "game")} scheduled
            {season.unplaced.length > 0 && <> · <span style={{ color: "var(--tl-warning)", fontWeight: 600 }}>{season.unplaced.length} didn't fit</span></>}
          </span>
        </div>
        {view === "date" ? (
          <DateView {...{ season, setSeason, toast, look, day, setDay, dates, division }} />
        ) : (
          <TeamView {...{ season, setSeason, toast, look }} />
        )}
      </div>
      <Side {...{ season, setSeason, toast }} />
      {generating && (
        <GenerateDialog season={season} onClose={() => setGenerating(false)}
          onDone={(s, summary) => { setGenerating(false); setSeason(s); toast(summary); }} />
      )}
    </div>
  );
}

// ── by date: surfaces as columns, time running down ─────────────────────────

function DateView({ season, setSeason, toast, look, day, setDay, dates, division }: Pick<Ctx, "season" | "setSeason" | "toast"> & {
  look: Lookup; day: string; setDay: (d: string) => void; dates: string[]; division: string;
}) {
  const lg = season.league;
  const daySlots = lg.slots.filter((s) => s.date === day);
  const surfaces = lg.surfaces.filter((sf) => daySlots.some((s) => s.surface_id === sf.id));
  const lo = Math.floor(Math.min(...daySlots.map((s) => minutes(s.start))) / 60) * 60;
  const hi = Math.ceil(Math.max(...daySlots.map((s) => minutes(s.end))) / 60) * 60;
  const height = (hi - lo) * PX_PER_MIN;
  const idx = dates.indexOf(day);
  const blackout = lg.blackouts.find((b) => b.scope === "league" && b.start_date <= day && day <= b.end_date);

  const [dragId, setDragId] = useState<string | null>(null);
  const [over, setOver] = useState<string | null>(null);
  const checks = useRef(new Map<string, { ok: boolean; problems: string[] }>());
  const [, force] = useState(0);
  const [pending, setPending] = useState<{ event: GameEvent; slot: Slot; problems: string[] } | null>(null);
  useEffect(() => { checks.current.clear(); }, [season.version]);

  const startOf = (s: Slot) => `${s.date}T${s.start}`;
  const check = async (eventId: string, s: Slot) => {
    const k = `${eventId}|${s.id}`;
    if (checks.current.has(k)) return checks.current.get(k)!;
    const r = await api.check(season.id, eventId, s.id, startOf(s));
    checks.current.set(k, r);
    force((n) => n + 1);
    return r;
  };
  const doMove = async (event: GameEvent, s: Slot) => {
    try {
      const next = await api.move(season.id, event.id, s.id, startOf(s));
      setSeason(next);
      toast(`Moved ${look.matchup(event)} to ${fmtDay(s.date)} ${fmtTime(s.start)}. Undo with Ctrl+Z.`);
    } catch (e) { toast((e as ApiError).message); }
  };
  const drop = async (s: Slot) => {
    const event = season.events.find((e) => e.id === dragId);
    setOver(null);
    setDragId(null);
    if (!event || (event.slot_id === s.id && event.start === startOf(s))) return;
    const r = await check(event.id, s);
    if (r.ok) doMove(event, s);
    else setPending({ event, slot: s, problems: r.problems });
  };
  const lock = async (e: GameEvent) => {
    try { setSeason(await api.lock(season.id, e.id, !e.locked)); } catch (err) { toast((err as ApiError).message); }
  };

  return (
    <>
      <div className="days">
        <button className="icon-btn" aria-label="Previous day" disabled={idx <= 0} onClick={() => setDay(dates[idx - 1])}><Icon name="chevron_left" /></button>
        {dates.map((d) => {
          const bo = lg.blackouts.some((b) => b.scope === "league" && b.start_date <= d && d <= b.end_date);
          return (
            <button key={d} className={`day-chip${d === day ? " on" : ""}${bo ? " blackout" : ""}`} onClick={() => setDay(d)}
              title={bo ? "Blackout date" : `${season.events.filter((e) => e.start.startsWith(d)).length} games`}>
              {fmtDay(d)}
            </button>
          );
        })}
        <button className="icon-btn" aria-label="Next day" disabled={idx >= dates.length - 1} onClick={() => setDay(dates[idx + 1])}><Icon name="chevron_right" /></button>
      </div>
      <div className="grid-scroll">
        {blackout && <div style={{ marginBottom: 12 }}><Note tone="bad" icon="block">Blackout: {blackout.note || "no games this day"}.</Note></div>}
        <p className="muted small" style={{ marginBottom: 10 }}>Drag a game to move it. While you drag, green means it fits there and red means it would break a rule.</p>
        <div className="cols">
          <div className="gutter" style={{ height: height + 36 }}>
            {Array.from({ length: (hi - lo) / 60 + 1 }, (_, i) => (
              <span key={i} style={{ top: 36 + i * 60 * PX_PER_MIN - 7 }}>{fmtTime(`${String((lo + i * 60) / 60).padStart(2, "0")}:00`)}</span>
            ))}
          </div>
          {surfaces.map((sf) => (
            <div className="col" key={sf.id}>
              <div className="col-head"><Icon name="stadium" style={{ fontSize: 16, color: "var(--tl-fg-muted)" }} />{look.venue(sf.venue_id)?.name === sf.name ? sf.name : `${look.venue(sf.venue_id)?.name} · ${sf.name}`}</div>
              <div className="col-body" style={{ height }}>
                {daySlots.filter((s) => s.surface_id === sf.id).map((s) => {
                  const games = season.events.filter((e) => e.slot_id === s.id);
                  const k = dragId ? checks.current.get(`${dragId}|${s.id}`) : undefined;
                  const cls = over === s.id ? (k ? (k.ok ? " ok" : " bad") : " over") : "";
                  return (
                    <div key={s.id} className={`slot${games.length ? "" : " empty"}${cls}`} title={k && !k.ok ? k.problems.join("\n") : undefined}
                      style={{ top: (minutes(s.start) - lo) * PX_PER_MIN + 2, height: (minutes(s.end) - minutes(s.start)) * PX_PER_MIN - 4 }}
                      onDragOver={(e) => e.preventDefault()}
                      onDragEnter={(e) => { e.preventDefault(); setOver(s.id); if (dragId) check(dragId, s); }}
                      onDrop={(e) => { e.preventDefault(); drop(s); }}>
                      {games.length === 0 && <span>{fmtTime(s.start)}–{fmtTime(s.end)} · open</span>}
                      {games.map((g) => (
                        <div key={g.id} className={`game${g.locked ? " locked" : ""}`} draggable={!g.locked}
                          onDragStart={(e) => { e.dataTransfer.effectAllowed = "move"; setDragId(g.id); }}
                          onDragEnd={() => { setDragId(null); setOver(null); }}
                          title={`${look.matchup(g)}\n${fmtDay(g.start)} ${fmtTime(g.start)} · ${g.minutes} min\n${look.place(g.slot_id)}`}
                          style={{ borderLeftColor: divisionColor(lg, g.division_id), opacity: division && g.division_id !== division ? 0.25 : 1 }}>
                          <div className="meta">
                            <span style={{ color: divisionColor(lg, g.division_id), fontWeight: 600 }}>{look.division(g.division_id)}</span>
                            <span>{fmtTime(g.start)}</span>
                            <span className="spacer" />
                            <button className="icon-btn" style={{ width: 20, height: 20 }} aria-label={g.locked ? "Unlock game" : "Lock game"}
                              title={g.locked ? "Locked: generating again won't move it. Click to unlock." : "Lock this game so generating again won't move it"}
                              onClick={() => lock(g)}>
                              <Icon name={g.locked ? "lock" : "lock_open"} style={{ fontSize: 14, color: g.locked ? "var(--tl-blue)" : undefined }} />
                            </button>
                          </div>
                          <div className="who">{look.team(g.home_team_id)}</div>
                          {g.away_team_id && <div className="who" style={{ fontWeight: 500 }}>vs {look.team(g.away_team_id)}</div>}
                        </div>
                      ))}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>
      {pending && (
        <Modal title="This move breaks a rule" subtitle={`${look.matchup(pending.event)} → ${look.place(pending.slot.id)}, ${fmtDay(pending.slot.date)} ${fmtTime(pending.slot.start)}`}
          onClose={() => setPending(null)}
          footer={<>
            <button className="btn btn-ghost" onClick={() => setPending(null)}>Cancel</button>
            <button className="btn btn-warn" onClick={() => { doMove(pending.event, pending.slot); setPending(null); }}>Move anyway</button>
          </>}>
          {pending.problems.map((p, i) => <Note key={i} tone="bad">{p}</Note>)}
          <p className="muted small">If you move it anyway, the problem will show on the Fairness tab and the schedule check until it's fixed.</p>
        </Modal>
      )}
    </>
  );
}

// ── by team ─────────────────────────────────────────────────────────────────

function TeamView({ season, setSeason, toast, look }: Pick<Ctx, "season" | "setSeason" | "toast"> & { look: Lookup }) {
  const lg = season.league;
  const [team, setTeam] = useState(lg.teams[0]?.id ?? "");
  const games = season.events.filter((e) => e.home_team_id === team || e.away_team_id === team)
    .sort((a, b) => a.start.localeCompare(b.start));
  const lock = async (e: GameEvent) => {
    try { setSeason(await api.lock(season.id, e.id, !e.locked)); } catch (err) { toast((err as ApiError).message); }
  };
  return (
    <div className="grid-scroll">
      <div className="row" style={{ marginBottom: 12 }}>
        <select className="input" value={team} onChange={(e) => setTeam(e.target.value)} aria-label="Team">
          {lg.divisions.map((d) => (
            <optgroup key={d.id} label={d.name}>
              {lg.teams.filter((t) => t.division_id === d.id).map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
            </optgroup>
          ))}
        </select>
        <span className="muted small">{plural(games.length, "game")} · {games.filter((g) => g.home_team_id === team).length} at home</span>
      </div>
      <div className="card" style={{ padding: 0 }}>
        <table className="data">
          <thead><tr><th>Date</th><th>Time</th><th>Opponent</th><th></th><th>Where</th><th></th></tr></thead>
          <tbody>
            {games.map((g) => {
              const home = g.home_team_id === team;
              return (
                <tr key={g.id}>
                  <td>{fmtDay(g.start)}</td>
                  <td>{fmtTime(g.start)}</td>
                  <td>{look.team(home ? g.away_team_id : g.home_team_id)}</td>
                  <td><span className={`chip ${home ? "chip-blue" : ""}`}>{home ? "Home" : "Away"}</span></td>
                  <td>{look.place(g.slot_id)}</td>
                  <td>
                    <button className="icon-btn" onClick={() => lock(g)} aria-label={g.locked ? "Unlock game" : "Lock game"}>
                      <Icon name={g.locked ? "lock" : "lock_open"} style={{ fontSize: 16, color: g.locked ? "var(--tl-blue)" : undefined }} />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── side panel: games that didn't fit, with fixes ───────────────────────────

function Side({ season, setSeason, toast }: Pick<Ctx, "season" | "setSeason" | "toast">) {
  const [ex, setEx] = useState<Explanation | null>(null);
  const [applying, setApplying] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  useEffect(() => {
    setEx(null);
    if (season.unplaced.length) api.explain(season.id).then(setEx).catch(() => setEx(null));
  }, [season.id, season.version, season.unplaced.length]);

  const apply = async (index: number, message: string) => {
    setApplying(message);
    try {
      const { job_id } = await api.applySuggestion(season.id, index);
      const j = await waitForJob(job_id, (x) => setProgress(x.total ? x.placed / x.total : 0.2));
      const s: Season = await api.season(season.id);
      setSeason(s);
      toast(j.result.summary ?? j.message);
    } catch (e) { toast((e as ApiError).message); }
    finally { setApplying(null); }
  };

  const locked = season.events.filter((e) => e.locked).length;
  return (
    <aside className="board-side">
      <div>
        <h2>At a glance</h2>
        <div className="stack" style={{ marginTop: 8 }}>
          <div className="row"><Icon name="event" style={{ color: "var(--tl-fg-muted)" }} />{plural(season.events.length, "game")} scheduled</div>
          {locked > 0 && <div className="row"><Icon name="lock" style={{ color: "var(--tl-fg-muted)" }} />{plural(locked, "game")} locked</div>}
          <div className="row muted small"><Icon name="history" style={{ fontSize: 18 }} />Last change: {season.last_action}</div>
        </div>
      </div>
      {season.unplaced.length > 0 && (
        <div className="stack">
          <h2>{plural(season.unplaced.length, "game")} didn't fit</h2>
          {!ex && <p className="muted small">Working out why…</p>}
          {ex?.findings.map((f, i) => <Note key={i} tone="warn">{f}</Note>)}
          {ex && ex.suggestions.length > 0 && <h3 style={{ marginTop: 8 }}>Ways to fix it</h3>}
          {ex?.suggestions.map((s) => (
            <div key={s.index} className="card" style={{ padding: 12 }}>
              <p>{s.message}</p>
              <button className="btn btn-soft" style={{ marginTop: 8 }} disabled={!!applying} onClick={() => apply(s.index, s.message)}>Do this</button>
            </div>
          ))}
          {applying && <><Progress value={progress} /><p className="muted small">Applying the change and placing the missing games…</p></>}
        </div>
      )}
    </aside>
  );
}

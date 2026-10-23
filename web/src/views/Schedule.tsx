import { useEffect, useMemo, useRef, useState } from "react";
import type { Ctx } from "../App";
import { api, ApiError, waitForJob, type Explanation, type GameEvent, type Matchup, type Season, type Slot, type SpotChoice } from "../api";
import { divisionColor, fmtDay, fmtTime, isoDate, Lookup, minutes, parseDate, plural } from "../format";
import { Icon, Modal, Note, Progress } from "../ui";
import { GenerateDialog } from "./GenerateDialog";
import { MonthView, SummaryView, VenueView, WeekView } from "./ScheduleViews";

const PX_PER_MIN = 1.1;

export function Schedule({ season, setSeason, toast }: Ctx) {
  const lg = season.league;
  const look = useMemo(() => new Lookup(lg), [lg]);
  const [generating, setGenerating] = useState(false);
  const [locking, setLocking] = useState(false);
  const [view, setView] = useState<"date" | "week" | "month" | "venue" | "team" | "summary">("date");
  const [division, setDivision] = useState("");
  // A game from the "Needs a spot" list that's being placed, and where it can go.
  const [picked, setPicked] = useState<string | null>(null);
  const [spots, setSpots] = useState<SpotChoice[] | null>(null);
  const [dragId, setDragId] = useState<string | null>(null);
  useEffect(() => { if (picked && !season.unplaced.some((m) => m.id === picked)) setPicked(null); }, [picked, season.unplaced]);
  useEffect(() => {
    setSpots(null);
    if (!picked) return;
    let live = true;
    api.spots(season.id, picked, true).then((r) => live && setSpots(r)).catch(() => live && setSpots([]));
    return () => { live = false; };
  }, [picked, season.id, season.version]);
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
            {([["date", "Day"], ["week", "Week"], ["month", "Month"], ["venue", "By venue"], ["team", "By team"], ["summary", "Summary"]] as const).map(([v, label]) => (
              <button key={v} className={`tab${view === v ? " active" : ""}`} onClick={() => setView(v)}>{label}</button>
            ))}
          </div>
          {(view === "date" || view === "week" || view === "month") && (
            <select className="input" value={division} onChange={(e) => setDivision(e.target.value)} aria-label="Highlight a division">
              <option value="">All divisions</option>
              {lg.divisions.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
          )}
          {season.events.length > 0 && (
            <button className="btn btn-ghost" onClick={() => setLocking(true)}><Icon name="lock" style={{ fontSize: 18 }} />Lock games</button>
          )}
          <div className="spacer" />
          <span className="muted small">{plural(season.events.length, "game")} scheduled
            {season.unplaced.length > 0 && <> · <span style={{ color: "var(--tl-warning)", fontWeight: 600 }}>{season.unplaced.length} need a spot</span></>}
          </span>
        </div>
        {view === "date" && <DateView {...{ season, setSeason, toast, look, day, setDay, dates, division, picked, spots, dragId, setDragId }} />}
        {view === "team" && <TeamView {...{ season, setSeason, toast, look }} />}
        {view !== "date" && view !== "team" && (() => {
          const props = { season, toast, look, day, setDay, division, openDay: (d: string) => { setDay(d); setView("date"); } };
          return view === "week" ? <WeekView {...props} /> : view === "month" ? <MonthView {...props} />
            : view === "venue" ? <VenueView {...props} /> : <SummaryView {...props} />;
        })()}
      </div>
      <Side {...{ season, setSeason, toast, look, picked, setPicked, spots, setDragId }}
        showDay={(d) => { setView("date"); setDay(d); }} />
      {locking && <LockDialog {...{ season, setSeason, toast, day }} onClose={() => setLocking(false)} />}
      {generating && (
        <GenerateDialog season={season} onClose={() => setGenerating(false)}
          onDone={(s, summary) => { setGenerating(false); setSeason(s); toast(summary); }} />
      )}
    </div>
  );
}

// ── by date: surfaces as columns, time running down ─────────────────────────

function DateView({ season, setSeason, toast, look, day, setDay, dates, division, picked, spots, dragId, setDragId }: Pick<Ctx, "season" | "setSeason" | "toast"> & {
  look: Lookup; day: string; setDay: (d: string) => void; dates: string[]; division: string;
  picked: string | null; spots: SpotChoice[] | null; dragId: string | null; setDragId: (id: string | null) => void;
}) {
  const lg = season.league;
  const daySlots = lg.slots.filter((s) => s.date === day);
  const surfaces = lg.surfaces.filter((sf) => daySlots.some((s) => s.surface_id === sf.id));
  const lo = Math.floor(Math.min(...daySlots.map((s) => minutes(s.start))) / 60) * 60;
  const hi = Math.ceil(Math.max(...daySlots.map((s) => minutes(s.end))) / 60) * 60;
  const height = (hi - lo) * PX_PER_MIN;
  const idx = dates.indexOf(day);
  const blackout = lg.blackouts.find((b) => b.scope === "league" && b.start_date <= day && day <= b.end_date);

  const [over, setOver] = useState<string | null>(null);
  const checks = useRef(new Map<string, { ok: boolean; problems: string[] }>());
  const [, force] = useState(0);
  const [pending, setPending] = useState<{ event: GameEvent | Matchup; slot: Slot; problems: string[] } | null>(null);
  useEffect(() => { checks.current.clear(); }, [season.version]);

  // Where the picked game can go on this day: slot id -> its best spot there.
  const spotIn = useMemo(() => {
    const m = new Map<string, SpotChoice>();
    for (const c of spots ?? []) {
      const had = m.get(c.slot_id);
      if (!had || (had.problems.length && !c.problems.length)) m.set(c.slot_id, c);
    }
    return m;
  }, [spots]);
  const spotDays = useMemo(() => new Set((spots ?? []).filter((c) => !c.problems.length).map((c) => c.start.slice(0, 10))), [spots]);

  const startFor = (id: string, s: Slot) => {
    const c = id === picked ? spotIn.get(s.id) : undefined;
    return c ? c.start : `${s.date}T${s.start}`;
  };
  const check = async (id: string, s: Slot) => {
    const k = `${id}|${s.id}`;
    if (checks.current.has(k)) return checks.current.get(k)!;
    const r = await api.check(season.id, id, s.id, startFor(id, s));
    checks.current.set(k, r);
    force((n) => n + 1);
    return r;
  };
  const doMove = async (item: GameEvent | Matchup, s: Slot) => {
    const waiting = !("slot_id" in item);
    const start = startFor(item.id, s);
    try {
      const next = await api.move(season.id, item.id, s.id, start);
      setSeason(next);
      toast(`${waiting ? "Placed" : "Moved"} ${look.matchup(item)} on ${fmtDay(s.date)} at ${fmtTime(start)}. Undo with Ctrl+Z.`);
    } catch (e) { toast((e as ApiError).message); }
  };
  const drop = async (s: Slot) => {
    const item = season.events.find((e) => e.id === dragId) ?? season.unplaced.find((m) => m.id === dragId);
    setOver(null);
    setDragId(null);
    if (!item || ("slot_id" in item && item.slot_id === s.id && item.start === startFor(item.id, s))) return;
    const r = await check(item.id, s);
    if (r.ok) doMove(item, s);
    else setPending({ event: item, slot: s, problems: r.problems });
  };
  const offBoard = async (e: GameEvent) => {
    try {
      setSeason(await api.unschedule(season.id, e.id));
      toast(`Took ${look.matchup(e)} off the schedule. It's in the "Needs a spot" list.`);
    } catch (err) { toast((err as ApiError).message); }
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
            <button key={d} className={`day-chip${d === day ? " on" : ""}${bo ? " blackout" : ""}${spotDays.has(d) ? " has-spot" : ""}`} onClick={() => setDay(d)}
              title={bo ? "Blackout date" : spotDays.has(d) ? "The game you picked can go on this day" : `${season.events.filter((e) => e.start.startsWith(d)).length} games`}>
              {fmtDay(d)}
            </button>
          );
        })}
        <button className="icon-btn" aria-label="Next day" disabled={idx >= dates.length - 1} onClick={() => setDay(dates[idx + 1])}><Icon name="chevron_right" /></button>
      </div>
      <div className="grid-scroll">
        {blackout && <div style={{ marginBottom: 12 }}><Note tone="bad" icon="block">Blackout: {blackout.note || "no games this day"}.</Note></div>}
        <p className="muted small" style={{ marginBottom: 10 }}>
          {picked && spots
            ? `Placing ${look.matchup(season.unplaced.find((m) => m.id === picked) ?? { home_team_id: "", away_team_id: null })}. Green outlines are open spots; starred ones are suggested. Click one to put the game there.`
            : "Drag a game to move it. While you drag, green means it fits there and red means it would break a rule."}
        </p>
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
                  const sp = picked ? spotIn.get(s.id) : undefined;
                  const target = sp && !sp.problems.length ? (sp.suggested ? " spot best" : " spot") : "";
                  const item = picked ? season.unplaced.find((m) => m.id === picked) : undefined;
                  return (
                    <div key={s.id} className={`slot${games.length ? "" : " empty"}${cls}${target}`}
                      title={k && !k.ok ? k.problems.join("\n") : sp ? [...sp.good, ...sp.watch, ...sp.problems].join("\n") : undefined}
                      onClick={target && item ? () => doMove(item, s) : undefined}
                      style={{ top: (minutes(s.start) - lo) * PX_PER_MIN + 2, height: (minutes(s.end) - minutes(s.start)) * PX_PER_MIN - 4 }}
                      onDragOver={(e) => e.preventDefault()}
                      onDragEnter={(e) => { e.preventDefault(); setOver(s.id); if (dragId) check(dragId, s); }}
                      onDrop={(e) => { e.preventDefault(); drop(s); }}>
                      {target && <span className="spot-tag"><Icon name={sp?.suggested ? "star" : "add"} style={{ fontSize: 14 }} />{sp?.suggested ? "Suggested" : "Open"} · {fmtTime(sp!.start)}</span>}
                      {games.length === 0 && !target && <span>{fmtTime(s.start)}–{fmtTime(s.end)} · open</span>}
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
                              onClick={(ev) => { ev.stopPropagation(); lock(g); }}>
                              <Icon name={g.locked ? "lock" : "lock_open"} style={{ fontSize: 14, color: g.locked ? "var(--tl-blue)" : undefined }} />
                            </button>
                            {!g.locked && g.away_team_id && (
                              <button className="icon-btn" style={{ width: 20, height: 20 }} aria-label="Take off the schedule"
                                title="Take this game off the schedule. It goes to the Needs a spot list so you can place it somewhere else."
                                onClick={(ev) => { ev.stopPropagation(); offBoard(g); }}>
                                <Icon name="remove_circle_outline" style={{ fontSize: 14 }} />
                              </button>
                            )}
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
        <Modal title="This move breaks a rule" subtitle={`${look.matchup(pending.event)} → ${look.place(pending.slot.id)}, ${fmtDay(pending.slot.date)} ${fmtTime(startFor(pending.event.id, pending.slot))}`}
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

// ── side panel: games that need a spot, where they can go, and fixes ─────────

function Side({ season, setSeason, toast, look, picked, setPicked, spots, setDragId, showDay }: Pick<Ctx, "season" | "setSeason" | "toast"> & {
  look: Lookup; picked: string | null; setPicked: (id: string | null) => void; spots: SpotChoice[] | null;
  setDragId: (id: string | null) => void; showDay: (day: string) => void;
}) {
  const lg = season.league;
  const [ex, setEx] = useState<Explanation | null>(null);
  const [applying, setApplying] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [filter, setFilter] = useState("");
  const [showAll, setShowAll] = useState(false);
  // Explanations only make sense after generating, not for matchups built to place by hand.
  // Right after a generate they load by themselves; otherwise on request (they take a few seconds).
  const explainable = season.unplaced.length > 0 && season.events.length > 0;
  const justGenerated = /^(Generated|Rescheduled|Placed games that didn't fit)/.test(season.last_action);
  const [asked, setAsked] = useState(false);
  useEffect(() => { setEx(null); setAsked(false); }, [season.id, season.version]);
  const wantEx = explainable && (justGenerated || asked);
  useEffect(() => {
    if (wantEx) api.explain(season.id).then(setEx).catch(() => setEx(null));
  }, [season.id, season.version, wantEx]);

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
  const place = async (m: Matchup, c: SpotChoice) => {
    try {
      setSeason(await api.move(season.id, m.id, c.slot_id, c.start));
      toast(`Placed ${look.matchup(m)} on ${fmtDay(c.start)} at ${fmtTime(c.start)}. Undo with Ctrl+Z.`);
    } catch (e) { toast((e as ApiError).message); }
  };

  const locked = season.events.filter((e) => e.locked).length;
  const waiting = season.unplaced.filter((m) => !filter || m.division_id === filter);
  const shown = showAll ? waiting : waiting.slice(0, 8);
  const current = season.unplaced.find((m) => m.id === picked);
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
          <h2>{season.unplaced.length === 1 ? "1 game needs a spot" : `${season.unplaced.length} games need a spot`}</h2>
          <p className="muted small">Pick a game to see the best places for it, or drag it onto the board.</p>
          {season.unplaced.length > 8 && (
            <select className="input" value={filter} onChange={(e) => setFilter(e.target.value)} aria-label="Division">
              <option value="">All divisions</option>
              {lg.divisions.filter((d) => season.unplaced.some((m) => m.division_id === d.id)).map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
          )}
          <div className="tray">
            {shown.map((m) => (
              <div key={m.id} className="stack" style={{ gap: 8 }}>
              <button className={`tray-item${picked === m.id ? " on" : ""}`} draggable
                onDragStart={(e) => { e.dataTransfer.effectAllowed = "move"; setDragId(m.id); }}
                onDragEnd={() => setDragId(null)}
                onClick={() => setPicked(picked === m.id ? null : m.id)} aria-pressed={picked === m.id}>
                <span className="dot" style={{ background: divisionColor(lg, m.division_id) }} />
                <span className="tray-who">{look.matchup(m)}</span>
                <span className="muted small">{look.division(m.division_id)}</span>
              </button>
              {picked === m.id && <SpotList m={m} spots={spots} look={look} place={place} showDay={showDay} />}
              </div>
            ))}
          </div>
          {waiting.length > 8 && (
            <button className="btn btn-ghost btn-sm" onClick={() => setShowAll(!showAll)}>{showAll ? "Show fewer" : `Show all ${waiting.length}`}</button>
          )}
          {current && !shown.includes(current) && <SpotList m={current} spots={spots} look={look} place={place} showDay={showDay} />}
        </div>
      )}
      {explainable && (
        <div className="stack">
          <h2>{justGenerated ? "Why games didn't fit" : "Not enough room?"}</h2>
          {!wantEx && <button className="btn btn-ghost btn-sm" style={{ alignSelf: "flex-start" }} onClick={() => setAsked(true)}>Find changes that make room</button>}
          {wantEx && !ex && <p className="muted small">Working out why…</p>}
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

function SpotList({ m, spots, look, place, showDay }: {
  m: Matchup; spots: SpotChoice[] | null; look: Lookup; place: (m: Matchup, c: SpotChoice) => void; showDay: (d: string) => void;
}) {
  if (!spots) return <p className="muted small">Finding open spots for {look.matchup(m)}…</p>;
  const legal = spots.filter((c) => !c.problems.length);
  const best = legal.filter((c) => c.suggested);
  const misses = spots.filter((c) => c.problems.length).slice(0, 3);
  return (
    <div className="stack" aria-label="Where it can go">
      {legal.length > 0 ? (
        <>
          <p className="muted small">Best spots. {plural(legal.length, "open spot")} in the season; they're outlined in green on the board.</p>
          {best.map((c) => (
            <div key={c.slot_id + c.start} className="card spot-card">
              <div className="row"><Icon name="star" style={{ fontSize: 18, color: "var(--tl-blue)" }} /><b>{fmtDay(c.start)} at {fmtTime(c.start)}</b></div>
              <div className="muted small">{look.place(c.slot_id)}</div>
              {c.good.map((g, i) => <div key={i} className="row small"><Icon name="check" style={{ fontSize: 16, color: "var(--tl-success)" }} />{g}</div>)}
              {c.watch.map((w, i) => <div key={i} className="row small muted"><Icon name="info" style={{ fontSize: 16 }} />{w}</div>)}
              <div className="row" style={{ marginTop: 6 }}>
                <button className="btn btn-soft btn-sm" onClick={() => place(m, c)}>Place here</button>
                <button className="btn btn-ghost btn-sm" onClick={() => showDay(c.start.slice(0, 10))}>Show on board</button>
              </div>
            </div>
          ))}
        </>
      ) : (
        <>
          <Note tone="warn">No open spot works for {look.matchup(m)} right now. Here are the closest options and the rule each one breaks.</Note>
          {misses.map((c) => (
            <div key={c.slot_id + c.start} className="card spot-card">
              <b>{fmtDay(c.start)} at {fmtTime(c.start)}</b>
              <div className="muted small">{look.place(c.slot_id)}</div>
              {c.problems.map((p, i) => <div key={i} className="row small" style={{ color: "var(--tl-error)" }}><Icon name="error" style={{ fontSize: 16 }} />{p}</div>)}
              <div className="row" style={{ marginTop: 6 }}>
                <button className="btn btn-warn btn-sm" onClick={() => place(m, c)}>Place anyway</button>
                <button className="btn btn-ghost btn-sm" onClick={() => showDay(c.start.slice(0, 10))}>Show on board</button>
              </div>
            </div>
          ))}
          {!misses.length && <p className="muted small">There's no time slot long enough for this game. Add time on the Setup tab.</p>}
        </>
      )}
    </div>
  );
}

// ── lock a whole day, week, venue or division ───────────────────────────────

function mondayOf(iso: string): string {
  const d = parseDate(iso);
  d.setDate(d.getDate() - ((d.getDay() + 6) % 7));
  return isoDate(d);
}

function LockDialog({ season, setSeason, toast, day, onClose }: Pick<Ctx, "season" | "setSeason" | "toast"> & { day: string; onClose: () => void }) {
  const lg = season.league;
  const [when, setWhen] = useState<"day" | "week" | "season">("day");
  const [venue, setVenue] = useState("");
  const [division, setDivision] = useState("");
  const [busy, setBusy] = useState(false);
  const monday = mondayOf(day);
  const slotVenue = useMemo(() => new Map(lg.slots.map((sl) => [sl.id, lg.surfaces.find((sf) => sf.id === sl.surface_id)?.venue_id])), [lg]);
  const games = season.events.filter((e) => {
    const d = e.start.slice(0, 10);
    if (when === "day" && d !== day) return false;
    if (when === "week" && mondayOf(d) !== monday) return false;
    if (venue && slotVenue.get(e.slot_id) !== venue) return false;
    return !division || e.division_id === division;
  });
  const locked = games.filter((e) => e.locked).length;
  const go = async (lock: boolean) => {
    setBusy(true);
    try {
      const next = await api.lockMany(season.id, {
        locked: lock, day: when === "day" ? day : undefined, week_of: when === "week" ? day : undefined,
        venue_id: venue || undefined, division_id: division || undefined,
      });
      setSeason(next);
      toast(next.message ?? "Done.");
      onClose();
    } catch (e) { toast((e as ApiError).message); }
    finally { setBusy(false); }
  };
  return (
    <Modal title="Lock games" onClose={onClose}
      subtitle="Locked games stay exactly where they are when you generate again. You can still move them by hand after unlocking."
      footer={<>
        <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
        <button className="btn btn-ghost" disabled={busy || locked === 0} onClick={() => go(false)}>Unlock {locked || ""}</button>
        <button className="btn btn-primary" disabled={busy || locked === games.length} onClick={() => go(true)}>
          <Icon name="lock" style={{ fontSize: 18 }} />Lock {games.length - locked || ""}
        </button>
      </>}>
      <div className="stack">
        <label className="row" style={{ cursor: "pointer" }}><input type="radio" checked={when === "day"} onChange={() => setWhen("day")} />{fmtDay(day)}</label>
        <label className="row" style={{ cursor: "pointer" }}><input type="radio" checked={when === "week"} onChange={() => setWhen("week")} />The week of {fmtDay(monday)}</label>
        <label className="row" style={{ cursor: "pointer" }}><input type="radio" checked={when === "season"} onChange={() => setWhen("season")} />The whole season</label>
      </div>
      <div className="row wrap">
        <label className="field">Venue
          <select className="input" value={venue} onChange={(e) => setVenue(e.target.value)}>
            <option value="">Every venue</option>
            {lg.venues.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
          </select>
        </label>
        <label className="field">Division
          <select className="input" value={division} onChange={(e) => setDivision(e.target.value)}>
            <option value="">Every division</option>
            {lg.divisions.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
        </label>
      </div>
      <Note>{games.length === 0 ? "No games match." : `${plural(games.length, "game")} ${games.length === 1 ? "matches" : "match"}, ${locked} already locked.`}</Note>
    </Modal>
  );
}

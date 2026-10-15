import { useEffect, useMemo, useState } from "react";
import type { Ctx } from "../App";
import { api, ApiError, type Blackout, type League, type RuleOverrides, type RuleSet } from "../api";
import { fmtDay, plural } from "../format";
import { Icon, Note } from "../ui";
import { ImportDialog, type ImportKind } from "./ImportDialog";

// Rule fields in plain language. Basic ones are always shown; the rest sit behind
// "Show advanced settings" so a first-time user never has to think about them.
type Field = { key: keyof RuleSet; label: string; kind: "number" | "time" | "hours" | "half"; advanced: boolean };
const FIELDS: Field[] = [
  { key: "games_per_team", label: "Games per team", kind: "number", advanced: false },
  { key: "game_minutes", label: "Game length (minutes)", kind: "number", advanced: false },
  { key: "units", label: "Half the surface", kind: "half", advanced: true },
  { key: "max_games_per_day", label: "Most games in a day", kind: "number", advanced: true },
  { key: "min_rest_minutes", label: "Rest between games (hours)", kind: "hours", advanced: true },
  { key: "earliest_start", label: "Earliest start", kind: "time", advanced: true },
  { key: "latest_end", label: "Finish by", kind: "time", advanced: true },
  { key: "early_before", label: "Counts as early before", kind: "time", advanced: true },
  { key: "late_from", label: "Counts as late from", kind: "time", advanced: true },
];

function show(f: Field, v: unknown): string {
  if (v === null || v === undefined) return "";
  if (f.kind === "time") return String(v).slice(0, 5);
  if (f.kind === "hours") return String(Number(v) / 60);
  if (f.kind === "half") return v === 1 ? "yes" : "no";
  return String(v);
}
function parse(f: Field, raw: string): unknown {
  if (raw === "") return null;
  if (f.kind === "time") return `${raw}:00`;
  if (f.kind === "hours") return Math.round(Number(raw) * 60);
  if (f.kind === "half") return raw === "yes" ? 1 : null;
  return Number(raw);
}

export function Setup({ season, setSeason, toast }: Ctx) {
  const lg = season.league;
  const [importing, setImporting] = useState<ImportKind | null>(null);
  const [checks, setChecks] = useState<{ problems: { severity: string; message: string }[]; capacity: string[] } | null>(null);
  const [advanced, setAdvanced] = useState(false);
  const [draft, setDraft] = useState<League>(lg);
  useEffect(() => setDraft(lg), [lg]);
  useEffect(() => { api.setupCheck(season.id).then(setChecks); }, [season.id, season.version]);

  const dirty = JSON.stringify(draft.rules) !== JSON.stringify(lg.rules) ||
    JSON.stringify(draft.divisions) !== JSON.stringify(lg.divisions);
  const hours = useMemo(() => lg.slots.reduce((n, s) => {
    const [a, b] = [s.start, s.end].map((t) => Number(t.slice(0, 2)) * 60 + Number(t.slice(3, 5)));
    return n + (b - a);
  }, 0) / 60, [lg.slots]);
  const sharedCoaches = lg.coaches.filter((c) => c.team_ids.length > 1).length;

  const saveRules = async () => {
    try {
      setSeason(await api.setLeague(season.id, draft, "Changed the rules"));
      toast("Rules saved.");
    } catch (e) { toast((e as ApiError).message); }
  };
  const setLeagueRule = (f: Field, raw: string) => {
    const v = parse(f, raw);
    if (v === null && f.kind !== "half") return;
    setDraft({ ...draft, rules: { ...draft.rules, [f.key]: v } as RuleSet });
  };
  const setDivRule = (divId: string, f: Field, raw: string) => {
    setDraft({
      ...draft,
      divisions: draft.divisions.map((d) => d.id !== divId ? d :
        { ...d, rules: { ...d.rules, [f.key]: parse(f, raw) } as RuleOverrides }),
    });
  };

  const fields = FIELDS.filter((f) => advanced || !f.advanced);

  return (
    <div className="page">
      <div className="row">
        <div style={{ flex: 1 }}>
          <h1>Setup</h1>
          <p className="muted" style={{ marginTop: 4 }}>Teams and time slots are all you need. The default rules work for most community leagues.</p>
        </div>
      </div>

      <div className="grid3">
        <SetupCard icon="groups" title="Teams" done={lg.teams.length > 0}
          text={lg.teams.length ? `${plural(lg.teams.length, "team")} in ${plural(lg.divisions.length, "division")}` : "No teams yet"}
          action="Import teams" onAction={() => setImporting("teams")} />
        <SetupCard icon="stadium" title="Time slots" done={lg.slots.length > 0}
          text={lg.slots.length ? `${plural(lg.slots.length, "slot")} · ${Math.round(hours)} hours at ${plural(lg.venues.length, "venue")}` : "No time slots yet"}
          action="Import time slots" onAction={() => setImporting("slots")} />
        <SetupCard icon="sports" title="Coaches (optional)" done={lg.coaches.length > 0}
          text={lg.coaches.length ? `${plural(lg.coaches.length, "coach", "coaches")}${sharedCoaches ? `, ${sharedCoaches} on more than one team` : ""}` : "Add coaches so nobody is booked twice"}
          action="Import coaches" onAction={() => setImporting("coaches")} disabled={!lg.teams.length} />
      </div>

      {checks && (checks.problems.length > 0 || checks.capacity.length > 0) && (
        <div className="stack">
          {checks.problems.map((p, i) => <Note key={i} tone={p.severity === "error" ? "bad" : "warn"}>{p.message}</Note>)}
          {checks.capacity.map((m, i) => <Note key={`c${i}`} tone="warn">{m}</Note>)}
        </div>
      )}

      {lg.divisions.length > 0 && (
        <div className="card">
          <div className="card-head">
            <h2 style={{ flex: 1 }}>Rules</h2>
            <label className="row small muted" style={{ gap: 6, cursor: "pointer" }}>
              <input type="checkbox" checked={advanced} onChange={(e) => setAdvanced(e.target.checked)} />
              Show advanced settings
            </label>
          </div>
          <p className="muted small" style={{ marginBottom: 12 }}>Set it once for everyone, then change only what's different for a division. Blank means "same as everyone".</p>
          <div style={{ overflowX: "auto" }}>
            <table className="data">
              <thead>
                <tr><th></th>{fields.map((f) => <th key={f.key}>{f.label}</th>)}</tr>
              </thead>
              <tbody>
                <tr>
                  <td style={{ fontWeight: 600 }}>Everyone</td>
                  {fields.map((f) => (
                    <td key={f.key}><RuleInput f={f} value={show(f, draft.rules[f.key])} onChange={(v) => setLeagueRule(f, v)} /></td>
                  ))}
                </tr>
                {draft.divisions.map((d) => (
                  <tr key={d.id}>
                    <td style={{ fontWeight: 500 }}>{d.name} <span className="muted small">{plural(lg.teams.filter((t) => t.division_id === d.id).length, "team")}</span></td>
                    {fields.map((f) => (
                      <td key={f.key}>
                        <RuleInput f={f} value={show(f, d.rules[f.key])} placeholder={show(f, draft.rules[f.key])}
                          onChange={(v) => setDivRule(d.id, f, v)} />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="row" style={{ marginTop: 12 }}>
            <button className="btn btn-primary" disabled={!dirty} onClick={saveRules}>Save rules</button>
            {dirty && <button className="btn btn-ghost" onClick={() => setDraft(lg)}>Discard changes</button>}
          </div>
        </div>
      )}

      <Blackouts {...{ season, setSeason, toast }} />
      <CopySetup {...{ season, toast }} />

      {importing && (
        <ImportDialog season={season} kind={importing} onClose={() => setImporting(null)}
          onDone={(s, summary) => { setImporting(null); setSeason(s); toast(summary); }} />
      )}
    </div>
  );
}

function SetupCard({ icon, title, text, action, onAction, done, disabled }: {
  icon: string; title: string; text: string; action: string; onAction: () => void; done: boolean; disabled?: boolean;
}) {
  return (
    <div className="card" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <div className="row">
        <Icon name={done ? "check_circle" : icon} style={{ color: done ? "var(--tl-success)" : "var(--tl-fg-muted)" }} />
        <h2>{title}</h2>
      </div>
      <p className="muted" style={{ flex: 1 }}>{text}</p>
      <div><button className={`btn ${done ? "btn-soft" : "btn-primary"}`} onClick={onAction} disabled={disabled}>{action}</button></div>
    </div>
  );
}

function RuleInput({ f, value, placeholder, onChange }: { f: Field; value: string; placeholder?: string; onChange: (v: string) => void }) {
  if (f.kind === "half") {
    return (
      <select className="input" value={value} onChange={(e) => onChange(e.target.value)} aria-label={f.label}>
        {placeholder !== undefined && <option value="">Same ({placeholder})</option>}
        <option value="no">no</option>
        <option value="yes">yes</option>
      </select>
    );
  }
  return (
    <input className="input" style={{ width: f.kind === "time" ? 110 : 80 }} type={f.kind === "time" ? "time" : "number"}
      min={0} value={value} placeholder={placeholder} aria-label={f.label} onChange={(e) => onChange(e.target.value)} />
  );
}

function Blackouts({ season, setSeason, toast }: Pick<Ctx, "season" | "setSeason" | "toast">) {
  const lg = season.league;
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [target, setTarget] = useState("league");
  const [note, setNote] = useState("");
  const targets = [
    { value: "league", label: "Whole league" },
    ...lg.divisions.map((d) => ({ value: `division:${d.id}`, label: `Division · ${d.name}` })),
    ...lg.teams.map((t) => ({ value: `team:${t.id}`, label: `Team · ${t.name}` })),
    ...lg.venues.map((v) => ({ value: `venue:${v.id}`, label: `Venue · ${v.name}` })),
  ];
  const label = (b: Blackout) => targets.find((t) => t.value === (b.scope === "league" ? "league" : `${b.scope}:${b.target_id}`))?.label ?? b.scope;
  const save = async (blackouts: Blackout[], action: string) => {
    try { setSeason(await api.setLeague(season.id, { ...lg, blackouts }, action)); }
    catch (e) { toast((e as ApiError).message); }
  };
  const add = () => {
    const [scope, id] = target.split(":");
    const b: Blackout = {
      id: `b-${Date.now().toString(36)}`, scope, target_id: id ?? null, start_date: start, end_date: end || start,
      start_time: null, end_time: null, note: note.trim(),
    };
    save([...lg.blackouts, b], `Added a blackout on ${fmtDay(start)}`);
    setStart(""); setEnd(""); setNote("");
  };
  return (
    <div className="card">
      <div className="card-head"><h2>Blackout dates</h2></div>
      <div className="stack" style={{ marginBottom: 12 }}>
        {lg.blackouts.length === 0 && <p className="muted">No blackout dates.</p>}
        {lg.blackouts.map((b) => (
          <div key={b.id} className="list-row">
            <Icon name="block" style={{ color: "var(--tl-error)", fontSize: 18 }} />
            <div style={{ width: 200 }}>{fmtDay(b.start_date)}{b.end_date !== b.start_date && ` to ${fmtDay(b.end_date)}`}</div>
            <span className="chip">{label(b)}</span>
            <div className="muted" style={{ flex: 1 }}>{b.note}</div>
            <button className="icon-btn" aria-label="Remove blackout"
              onClick={() => save(lg.blackouts.filter((x) => x.id !== b.id), `Removed the blackout on ${fmtDay(b.start_date)}`)}>
              <Icon name="delete" style={{ fontSize: 18 }} />
            </button>
          </div>
        ))}
      </div>
      <div className="row wrap" style={{ alignItems: "flex-end" }}>
        <label className="field">From<input className="input" type="date" value={start} onChange={(e) => setStart(e.target.value)} /></label>
        <label className="field">To (optional)<input className="input" type="date" value={end} onChange={(e) => setEnd(e.target.value)} /></label>
        <label className="field">Who it applies to
          <select className="input" value={target} onChange={(e) => setTarget(e.target.value)}>
            {targets.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
        </label>
        <label className="field" style={{ flex: 1, minWidth: 160 }}>Note<input className="input" value={note} placeholder="e.g. Holiday weekend" onChange={(e) => setNote(e.target.value)} /></label>
        <button className="btn btn-soft" disabled={!start} onClick={add}>Add</button>
      </div>
    </div>
  );
}

function CopySetup({ season, toast }: Pick<Ctx, "season" | "toast">) {
  const [name, setName] = useState("");
  const [start, setStart] = useState("");
  const copy = async () => {
    try {
      const s = await api.clone(season.id, name.trim(), start);
      window.location.hash = `#/s/${s.id}/setup`;
      toast("Setup copied. Dates moved to the new season, same days of the week.");
    } catch (e) { toast((e as ApiError).message); }
  };
  return (
    <div className="card">
      <div className="card-head"><h2>Use this setup next season</h2></div>
      <p className="muted small" style={{ marginBottom: 12 }}>Copies teams, coaches, venues, time slots, rules and blackouts. Dates move to the new season and stay on the same days of the week.</p>
      <div className="row wrap" style={{ alignItems: "flex-end" }}>
        <label className="field" style={{ flex: 1 }}>New season name<input className="input" value={name} onChange={(e) => setName(e.target.value)} /></label>
        <label className="field">First day<input className="input" type="date" value={start} onChange={(e) => setStart(e.target.value)} /></label>
        <button className="btn btn-soft" disabled={!name.trim() || !start} onClick={copy}>Copy setup</button>
      </div>
    </div>
  );
}

// Add and edit teams, venues and time slots by hand (the import is the other way in).
// Every change saves the whole setup as one undoable step; the API keeps the schedule
// consistent with it (deleted teams cancel their games, deleted time sends games to
// "Needs a spot").
import { useMemo, useState } from "react";
import type { Ctx } from "../App";
import { api, ApiError, type Coach, type League, type Slot, type Team, type TimeOff, type Venue } from "../api";
import { fmtDay, fmtTime, isoDate, parseDate, plural } from "../format";
import { Icon, Modal, Note } from "../ui";

let seq = 0;
const uid = (prefix: string) => `${prefix}-${Date.now().toString(36)}${(seq++).toString(36)}`;
const key = (name: string) => name.trim().toLowerCase().replace(/\s+/g, " ");
const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const EVERY = ["Mondays", "Tuesdays", "Wednesdays", "Thursdays", "Fridays", "Saturdays", "Sundays"];
const weekday = (iso: string) => (parseDate(iso).getDay() + 6) % 7; // Monday = 0

type Save = (league: League, action: string) => Promise<boolean>;

export function useSave({ season, setSeason, toast }: Pick<Ctx, "season" | "setSeason" | "toast">): Save {
  return async (league, action) => {
    try {
      const next = await api.setLeague(season.id, league, action);
      setSeason(next);
      toast(next.message ? `${action}. ${next.message}` : `${action}. Undo with Ctrl+Z.`);
      return true;
    } catch (e) {
      toast((e as ApiError).message);
      return false;
    }
  };
}

// ── teams ───────────────────────────────────────────────────────────────────

export function TeamsEditor(ctx: Pick<Ctx, "season" | "setSeason" | "toast">) {
  const lg = ctx.season.league;
  const save = useSave(ctx);
  const [editing, setEditing] = useState<Team | "new" | null>(null);
  const [open, setOpen] = useState(false);
  const coachesOf = (t: string) => lg.coaches.filter((c) => c.team_ids.includes(t)).map((c) => c.name).join(", ");
  return (
    <div className="card">
      <div className="card-head">
        <h2 style={{ flex: 1 }}>Teams</h2>
        <button className="btn btn-soft" onClick={() => setEditing("new")}><Icon name="add" style={{ fontSize: 18 }} />Add a team</button>
      </div>
      {lg.teams.length === 0 ? <p className="muted">No teams yet. Add them one at a time here, or import a spreadsheet above.</p> : (
        <>
          <button className="btn btn-ghost btn-sm" onClick={() => setOpen(!open)}>
            {open ? "Hide the team list" : `Show all ${plural(lg.teams.length, "team")}`}
          </button>
          {open && lg.divisions.map((d) => (
            <div key={d.id} style={{ marginTop: 12 }}>
              <DivisionHead {...{ lg, save, d }} />
              <table className="data">
                <tbody>
                  {lg.teams.filter((t) => t.division_id === d.id).map((t) => (
                    <tr key={t.id}>
                      <td style={{ fontWeight: 500 }}>{t.name}</td>
                      <td className="muted">{lg.venues.find((v) => v.id === t.home_venue_id)?.name ?? ""}</td>
                      <td className="muted">{coachesOf(t.id)}</td>
                      <td style={{ width: 40 }}>
                        <button className="icon-btn" aria-label={`Edit ${t.name}`} onClick={() => setEditing(t)}><Icon name="edit" style={{ fontSize: 18 }} /></button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </>
      )}
      {editing && <TeamDialog {...{ lg, save, season: ctx.season }} team={editing === "new" ? null : editing} onClose={() => setEditing(null)} />}
    </div>
  );
}

function DivisionHead({ lg, save, d }: { lg: League; save: Save; d: League["divisions"][number] }) {
  const [renaming, setRenaming] = useState<string | null>(null);
  const empty = !lg.teams.some((t) => t.division_id === d.id);
  if (renaming !== null) {
    return (
      <div className="row" style={{ marginBottom: 6 }}>
        <input className="input" value={renaming} autoFocus aria-label="Division name" onChange={(e) => setRenaming(e.target.value)} />
        <button className="btn btn-soft btn-sm" disabled={!renaming.trim()} onClick={async () => {
          if (await save({ ...lg, divisions: lg.divisions.map((x) => (x.id === d.id ? { ...x, name: renaming.trim() } : x)) }, `Renamed ${d.name} to ${renaming.trim()}`)) setRenaming(null);
        }}>Save</button>
        <button className="btn btn-ghost btn-sm" onClick={() => setRenaming(null)}>Cancel</button>
      </div>
    );
  }
  return (
    <div className="row" style={{ marginBottom: 6 }}>
      <h3>{d.name}</h3>
      <button className="icon-btn" style={{ width: 26, height: 26 }} aria-label={`Rename ${d.name}`} onClick={() => setRenaming(d.name)}><Icon name="edit" style={{ fontSize: 16 }} /></button>
      {empty && <button className="btn btn-ghost btn-sm" onClick={() => save({ ...lg, divisions: lg.divisions.filter((x) => x.id !== d.id) }, `Deleted the ${d.name} division`)}>Delete this empty division</button>}
    </div>
  );
}

function TeamDialog({ lg, save, season, team, onClose }: {
  lg: League; save: Save; season: Ctx["season"]; team: Team | null; onClose: () => void;
}) {
  const [name, setName] = useState(team?.name ?? "");
  const [division, setDivision] = useState(team?.division_id ?? lg.divisions[0]?.id ?? "new");
  const [newDivision, setNewDivision] = useState("");
  const [venue, setVenue] = useState(team?.home_venue_id ?? "");
  const [coaches, setCoaches] = useState(team ? lg.coaches.filter((c) => c.team_ids.includes(team.id)).map((c) => c.name).join(", ") : "");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const games = team ? season.events.filter((e) => e.home_team_id === team.id || e.away_team_id === team.id).length : 0;
  const clash = lg.teams.some((t) => t.id !== team?.id && key(t.name) === key(name));
  const ok = name.trim() && !clash && (division !== "new" || newDivision.trim());

  const submit = async () => {
    let divisions = lg.divisions;
    let divId = division;
    if (division === "new") {
      const existing = lg.divisions.find((d) => key(d.name) === key(newDivision));
      divId = existing?.id ?? uid("d");
      if (!existing) divisions = [...divisions, { id: divId, name: newDivision.trim(), rules: {} }];
    }
    const id = team?.id ?? uid("t");
    const t: Team = { id, name: name.trim(), division_id: divId, home_venue_id: venue || null, rules: team?.rules ?? {} };
    const teams = team ? lg.teams.map((x) => (x.id === id ? t : x)) : [...lg.teams, t];
    // Coaches are matched by name, so one person on two teams is one coach (and can't be double-booked).
    const wanted = coaches.split(",").map((c) => c.trim()).filter(Boolean);
    let list = lg.coaches.map((c) => ({ ...c, team_ids: c.team_ids.filter((x) => x !== id) }));
    for (const n of wanted) {
      const found = list.find((c) => key(c.name) === key(n));
      if (found) found.team_ids = [...found.team_ids, id];
      else list = [...list, { id: uid("c"), name: n, team_ids: [id], email: null, phone: null }];
    }
    list = list.filter((c) => c.team_ids.length > 0 || lg.coaches.find((o) => o.id === c.id)?.team_ids.length === 0);
    if (await save({ ...lg, divisions, teams, coaches: list }, team ? `Changed ${t.name}` : `Added ${t.name}`)) onClose();
  };
  const remove = async () => {
    if (!team) return;
    const next: League = {
      ...lg,
      teams: lg.teams.filter((x) => x.id !== team.id),
      coaches: lg.coaches.map((c) => ({ ...c, team_ids: c.team_ids.filter((x) => x !== team.id) })).filter((c) => c.team_ids.length),
      families: lg.families.map((f) => ({ ...f, team_ids: f.team_ids.filter((x) => x !== team.id) })),
      blackouts: lg.blackouts.filter((b) => !(b.scope === "team" && b.target_id === team.id)),
    };
    if (await save(next, `Deleted ${team.name}`)) onClose();
  };

  return (
    <Modal title={team ? `Edit ${team.name}` : "Add a team"} onClose={onClose}
      footer={<>
        {team && !confirmDelete && <button className="btn btn-ghost" style={{ marginRight: "auto" }} onClick={() => setConfirmDelete(true)}>Delete team</button>}
        <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" disabled={!ok} onClick={submit}>{team ? "Save" : "Add team"}</button>
      </>}>
      {confirmDelete && (
        <Note tone="bad">
          {games ? `Deleting ${team!.name} cancels their ${plural(games, "scheduled game")}. ` : ""}You can undo this.
          <div style={{ marginTop: 8 }}><button className="btn btn-warn btn-sm" onClick={remove}>Delete {team!.name}</button></div>
        </Note>
      )}
      <label className="field">Team name<input className="input" value={name} autoFocus onChange={(e) => setName(e.target.value)} placeholder="e.g. Hawks U11 Blue" /></label>
      {clash && <Note tone="warn">There's already a team called {name.trim()}.</Note>}
      <div className="row wrap">
        <label className="field" style={{ flex: 1 }}>Division
          <select className="input" value={division} onChange={(e) => setDivision(e.target.value)}>
            {lg.divisions.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
            <option value="new">New division…</option>
          </select>
        </label>
        {division === "new" && <label className="field" style={{ flex: 1 }}>New division name<input className="input" value={newDivision} onChange={(e) => setNewDivision(e.target.value)} placeholder="e.g. U11" /></label>}
      </div>
      <label className="field">Home venue (optional)
        <select className="input" value={venue} onChange={(e) => setVenue(e.target.value)}>
          <option value="">No home venue</option>
          {lg.venues.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
        </select>
      </label>
      <label className="field">Coaches (optional)
        <input className="input" value={coaches} onChange={(e) => setCoaches(e.target.value)} placeholder="e.g. Sam Lee, Priya Shah" />
      </label>
      <p className="muted small">Separate names with commas. Use the same name on every team someone coaches, so they're never booked in two places at once.</p>
    </Modal>
  );
}

// ── venues and time ─────────────────────────────────────────────────────────

interface Pattern { surface_id: string; day: number; start: string; end: string; slots: Slot[]; parts: number }

export function FacilitiesEditor(ctx: Pick<Ctx, "season" | "setSeason" | "toast">) {
  const lg = ctx.season.league;
  const save = useSave(ctx);
  const [venueDialog, setVenueDialog] = useState<Venue | "new" | null>(null);
  const [adding, setAdding] = useState<string | null>(null); // surface id
  const [expanded, setExpanded] = useState<string | null>(null);
  // Time is shown as weekly patterns ("Saturdays 7:00 AM to 3:00 PM, 12 dates"), the way schedulers think about it.
  const patterns = useMemo(() => {
    const m = new Map<string, Pattern>();
    for (const s of [...lg.slots].sort((a, b) => a.date.localeCompare(b.date))) {
      const k = `${s.surface_id}|${weekday(s.date)}|${s.start}|${s.end}`;
      if (!m.has(k)) m.set(k, { surface_id: s.surface_id, day: weekday(s.date), start: s.start, end: s.end, slots: [], parts: 1 });
      m.get(k)!.slots.push(s);
    }
    // Back-to-back blocks on the same dates read as one: "Saturdays 9:00 AM to 3:00 PM, in 6 slots".
    const merged = new Map<string, Pattern>();
    const sorted = [...m.values()].sort((a, b) => a.start.localeCompare(b.start));
    const last = new Map<string, Pattern>();
    for (const p of sorted) {
      const group = `${p.surface_id}|${p.day}|${p.slots.map((s) => s.date).join(",")}`;
      const prev = last.get(group);
      if (prev && prev.end === p.start) {
        prev.end = p.end;
        prev.slots = [...prev.slots, ...p.slots];
        prev.parts += 1;
      } else {
        const copy = { ...p, slots: [...p.slots] };
        merged.set(`${group}|${p.start}`, copy);
        last.set(group, copy);
      }
    }
    return [...merged.entries()].sort(([, a], [, b]) => a.day - b.day || a.start.localeCompare(b.start));
  }, [lg.slots]);
  const gamesIn = (ids: Set<string>) => ctx.season.events.filter((e) => ids.has(e.slot_id)).length;
  const removeSlots = (slots: Slot[], action: string) => {
    const ids = new Set(slots.map((s) => s.id));
    const n = gamesIn(ids);
    if (n && !window.confirm(`${plural(n, "scheduled game")} ${n === 1 ? "is" : "are"} in this time. ${n === 1 ? "It goes" : "They go"} to the Needs a spot list. Continue?`)) return;
    save({ ...lg, slots: lg.slots.filter((s) => !ids.has(s.id)) }, action);
  };

  return (
    <div className="card">
      <div className="card-head">
        <h2 style={{ flex: 1 }}>Venues and available time</h2>
        <button className="btn btn-soft" onClick={() => setVenueDialog("new")}><Icon name="add" style={{ fontSize: 18 }} />Add a venue</button>
      </div>
      {lg.venues.length === 0 && <p className="muted">No venues yet. Add one, then add the times you have it each week.</p>}
      <div className="stack">
        {lg.venues.map((v) => (
          <div key={v.id} className="venue">
            <div className="row">
              <Icon name="stadium" style={{ color: "var(--tl-fg-muted)" }} />
              <h3 style={{ flex: 1 }}>{v.name} {v.address && <span className="muted small" style={{ fontWeight: 400 }}>· {v.address}</span>}</h3>
              <button className="icon-btn" aria-label={`Edit ${v.name}`} onClick={() => setVenueDialog(v)}><Icon name="edit" style={{ fontSize: 18 }} /></button>
            </div>
            {lg.surfaces.filter((sf) => sf.venue_id === v.id).map((sf) => (
              <div key={sf.id} className="surface">
                <div className="row">
                  <b style={{ flex: 1 }}>{sf.name}{sf.units > 1 && <span className="muted small" style={{ fontWeight: 400 }}> · can be split in half</span>}</b>
                  <button className="btn btn-ghost btn-sm" onClick={() => setAdding(sf.id)}><Icon name="add" style={{ fontSize: 16 }} />Add time</button>
                </div>
                {patterns.filter(([, p]) => p.surface_id === sf.id).map(([k, p]) => (
                  <div key={k}>
                    <div className="row small pattern">
                      <span style={{ width: 110 }}>{p.slots.length === 1 ? fmtDay(p.slots[0].date) : EVERY[p.day]}</span>
                      <span style={{ width: 240 }}>{fmtTime(p.start)} to {fmtTime(p.end)}{p.parts > 1 && <span className="muted">, in {p.parts} slots</span>}</span>
                      <button className="link muted" onClick={() => setExpanded(expanded === k ? null : k)}>
                        {p.slots.length / p.parts === 1 ? "1 date" : `${p.slots.length / p.parts} dates, ${fmtDay(p.slots[0].date)} to ${fmtDay(p.slots[p.slots.length / p.parts - 1].date)}`}
                      </button>
                      <span className="spacer" />
                      <button className="icon-btn" style={{ width: 28, height: 28 }} aria-label="Remove this time"
                        onClick={() => removeSlots(p.slots, `Removed ${EVERY[p.day]} ${fmtTime(p.start)} to ${fmtTime(p.end)} at ${sf.name}`)}>
                        <Icon name="delete" style={{ fontSize: 16 }} />
                      </button>
                    </div>
                    {expanded === k && (
                      <div className="row wrap" style={{ gap: 6, margin: "4px 0 8px" }}>
                        {p.slots.slice(0, p.slots.length / p.parts).map((s) => (
                          <span key={s.id} className="chip">{fmtDay(s.date)}
                            <button className="chip-x" aria-label={`Remove ${fmtDay(s.date)}`}
                              onClick={() => removeSlots(p.slots.filter((x) => x.date === s.date), `Removed ${fmtDay(s.date)} ${fmtTime(p.start)} to ${fmtTime(p.end)} at ${sf.name}`)}>
                              <Icon name="close" style={{ fontSize: 14 }} />
                            </button>
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
                {!patterns.some(([, p]) => p.surface_id === sf.id) && <p className="muted small">No time here yet.</p>}
              </div>
            ))}
          </div>
        ))}
      </div>
      {venueDialog && <VenueDialog {...{ lg, save }} venue={venueDialog === "new" ? null : venueDialog} games={(ids) => gamesIn(ids)} onClose={() => setVenueDialog(null)} />}
      {adding && <TimeDialog {...{ lg, save }} surfaceId={adding} onClose={() => setAdding(null)} />}
    </div>
  );
}

function VenueDialog({ lg, save, venue, games, onClose }: {
  lg: League; save: Save; venue: Venue | null; games: (slotIds: Set<string>) => number; onClose: () => void;
}) {
  const [name, setName] = useState(venue?.name ?? "");
  const [address, setAddress] = useState(venue?.address ?? "");
  const [surfaces, setSurfaces] = useState(() => {
    const have = venue ? lg.surfaces.filter((s) => s.venue_id === venue.id) : [];
    return have.length ? have.map((s) => ({ id: s.id, name: s.name, split: s.units > 1 }))
      : [{ id: uid("s"), name: lg.sport === "hockey" ? "Main rink" : "Field 1", split: false }];
  });
  const [confirmDelete, setConfirmDelete] = useState(false);
  const ok = name.trim() && surfaces.every((s) => s.name.trim()) && surfaces.length > 0;

  const submit = async () => {
    const id = venue?.id ?? uid("v");
    const v: Venue = { id, name: name.trim(), address: address.trim() || null };
    const venues = venue ? lg.venues.map((x) => (x.id === id ? { ...x, ...v } : x)) : [...lg.venues, v];
    const kept = new Set(surfaces.map((s) => s.id));
    const others = lg.surfaces.filter((s) => s.venue_id !== id);
    const mine = surfaces.map((s) => ({
      ...(lg.surfaces.find((x) => x.id === s.id) ?? { lit: true }),
      id: s.id, venue_id: id, name: s.name.trim(), units: s.split ? 2 : 1,
    }));
    const removed = new Set(lg.surfaces.filter((s) => s.venue_id === id && !kept.has(s.id)).map((s) => s.id));
    const slots = lg.slots.filter((s) => !removed.has(s.surface_id));
    if (await save({ ...lg, venues, surfaces: [...others, ...mine], slots }, venue ? `Changed ${v.name}` : `Added ${v.name}`)) onClose();
  };
  const remove = async () => {
    if (!venue) return;
    const sfs = new Set(lg.surfaces.filter((s) => s.venue_id === venue.id).map((s) => s.id));
    const next: League = {
      ...lg,
      venues: lg.venues.filter((v) => v.id !== venue.id),
      surfaces: lg.surfaces.filter((s) => !sfs.has(s.id)),
      slots: lg.slots.filter((s) => !sfs.has(s.surface_id)),
      teams: lg.teams.map((t) => (t.home_venue_id === venue.id ? { ...t, home_venue_id: null } : t)),
      blackouts: lg.blackouts.filter((b) => !((b.scope === "venue" && b.target_id === venue.id) || (b.scope === "surface" && sfs.has(b.target_id ?? "")))),
    };
    if (await save(next, `Deleted ${venue.name}`)) onClose();
  };
  const venueGames = venue ? games(new Set(lg.slots.filter((s) => lg.surfaces.some((sf) => sf.id === s.surface_id && sf.venue_id === venue.id)).map((s) => s.id))) : 0;

  return (
    <Modal title={venue ? `Edit ${venue.name}` : "Add a venue"} onClose={onClose}
      footer={<>
        {venue && !confirmDelete && <button className="btn btn-ghost" style={{ marginRight: "auto" }} onClick={() => setConfirmDelete(true)}>Delete venue</button>}
        <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" disabled={!ok} onClick={submit}>{venue ? "Save" : "Add venue"}</button>
      </>}>
      {confirmDelete && (
        <Note tone="bad">
          Deleting {venue!.name} removes all its time.{venueGames ? ` ${plural(venueGames, "scheduled game")} go to the Needs a spot list.` : ""} You can undo this.
          <div style={{ marginTop: 8 }}><button className="btn btn-warn btn-sm" onClick={remove}>Delete {venue!.name}</button></div>
        </Note>
      )}
      <label className="field">Venue name<input className="input" value={name} autoFocus onChange={(e) => setName(e.target.value)} placeholder="e.g. North Arena" /></label>
      <label className="field">Address (optional)<input className="input" value={address} onChange={(e) => setAddress(e.target.value)} /></label>
      <div className="stack">
        <h3>{lg.sport === "hockey" ? "Rinks" : "Fields or courts"}</h3>
        {surfaces.map((s, i) => (
          <div key={s.id} className="row">
            <input className="input" style={{ flex: 1 }} value={s.name} aria-label="Name"
              onChange={(e) => setSurfaces(surfaces.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)))} />
            <label className="row small" style={{ cursor: "pointer", gap: 6 }}>
              <input type="checkbox" checked={s.split} onChange={(e) => setSurfaces(surfaces.map((x, j) => (j === i ? { ...x, split: e.target.checked } : x)))} />
              Can be split in half
            </label>
            <button className="icon-btn" aria-label="Remove" disabled={surfaces.length === 1} onClick={() => setSurfaces(surfaces.filter((_, j) => j !== i))}><Icon name="close" style={{ fontSize: 18 }} /></button>
          </div>
        ))}
        <div><button className="btn btn-ghost btn-sm" onClick={() => setSurfaces([...surfaces, { id: uid("s"), name: `${lg.sport === "hockey" ? "Rink" : "Field"} ${surfaces.length + 1}`, split: false }])}>
          <Icon name="add" style={{ fontSize: 16 }} />Add another
        </button></div>
      </div>
    </Modal>
  );
}

function TimeDialog({ lg, save, surfaceId, onClose }: { lg: League; save: Save; surfaceId: string; onClose: () => void }) {
  const sf = lg.surfaces.find((s) => s.id === surfaceId)!;
  const venue = lg.venues.find((v) => v.id === sf.venue_id);
  const [days, setDays] = useState<number[]>([5]);
  const [start, setStart] = useState("09:00");
  const [end, setEnd] = useState("17:00");
  const [from, setFrom] = useState(lg.season_start);
  const [to, setTo] = useState(lg.season_end);
  const dates = useMemo(() => {
    const out: string[] = [];
    if (!from || !to || to < from) return out;
    for (let d = parseDate(from); isoDate(d) <= to; d.setDate(d.getDate() + 1)) {
      if (from === to || days.includes((d.getDay() + 6) % 7)) out.push(isoDate(d));
    }
    return out;
  }, [days, from, to]);
  const minutesLong = (Number(end.slice(0, 2)) * 60 + Number(end.slice(3))) - (Number(start.slice(0, 2)) * 60 + Number(start.slice(3)));
  const taken = new Set(lg.slots.filter((s) => s.surface_id === surfaceId).map((s) => s.date));
  const overlapping = dates.filter((d) => taken.has(d) && lg.slots.some((s) => s.surface_id === surfaceId && s.date === d && s.start < `${end}:00` && `${start}:00` < s.end));
  const ok = dates.length > 0 && minutesLong > 0 && overlapping.length === 0;
  const where = venue && venue.name !== sf.name ? `${venue.name} ${sf.name}` : sf.name;

  const submit = async () => {
    const slots: Slot[] = dates.map((d) => ({ id: uid("sl"), surface_id: surfaceId, date: d, start: `${start}:00`, end: `${end}:00`, cost: null }));
    const label = from === to ? fmtDay(from) : days.map((d) => EVERY[d]).join(" and ");
    if (await save({ ...lg, slots: [...lg.slots, ...slots] }, `Added ${label} ${fmtTime(start)} to ${fmtTime(end)} at ${where}`)) onClose();
  };
  return (
    <Modal title={`Add time at ${where}`} onClose={onClose}
      subtitle="Add the hours you have every week. Remove single dates afterwards if a week is different."
      footer={<>
        <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" disabled={!ok} onClick={submit}>Add {plural(dates.length, "date")}</button>
      </>}>
      <div className="field">Repeats on
        <div className="row wrap" style={{ gap: 6 }}>
          {WEEKDAYS.map((w, i) => (
            <button key={w} className={`day-chip${days.includes(i) ? " on" : ""}`} aria-pressed={days.includes(i)}
              onClick={() => setDays(days.includes(i) ? days.filter((x) => x !== i) : [...days, i].sort())}>{w}</button>
          ))}
        </div>
      </div>
      <div className="row wrap">
        <label className="field">From<input className="input" type="time" value={start} onChange={(e) => setStart(e.target.value)} /></label>
        <label className="field">To<input className="input" type="time" value={end} onChange={(e) => setEnd(e.target.value)} /></label>
      </div>
      <div className="row wrap">
        <label className="field">First date<input className="input" type="date" value={from} onChange={(e) => setFrom(e.target.value)} /></label>
        <label className="field">Last date<input className="input" type="date" value={to} onChange={(e) => setTo(e.target.value)} /></label>
      </div>
      {minutesLong <= 0 ? <Note tone="warn">The end time needs to be after the start time.</Note>
        : overlapping.length ? <Note tone="warn">{where} already has time then on {overlapping.slice(0, 3).map(fmtDay).join(", ")}{overlapping.length > 3 ? ` and ${overlapping.length - 3} more` : ""}.</Note>
        : <Note>{dates.length ? `${plural(dates.length, "date")}, ${Math.round((dates.length * minutesLong) / 6) / 10} hours in all.` : "Pick at least one day of the week."}</Note>}
    </Modal>
  );
}

// ── coaches: times they can't make (firm) and times they'd rather coach (soft) ─

export function describeTime(t: TimeOff): string {
  const when = t.day ? fmtDay(t.day) : EVERY[t.weekday ?? 0];
  return t.start && t.end ? `${when} from ${fmtTime(t.start)} to ${fmtTime(t.end)}` : when;
}

export function CoachesEditor(ctx: Pick<Ctx, "season" | "setSeason" | "toast">) {
  const lg = ctx.season.league;
  const save = useSave(ctx);
  const [editing, setEditing] = useState<Coach | null>(null);
  const [open, setOpen] = useState(false);
  if (!lg.coaches.length) return null;
  const teamNames = (c: Coach) => c.team_ids.map((t) => lg.teams.find((x) => x.id === t)?.name ?? "").filter(Boolean).join(", ");
  const withTimes = lg.coaches.filter((c) => c.unavailable?.length || c.prefers?.length).length;
  return (
    <div className="card">
      <div className="card-head">
        <h2 style={{ flex: 1 }}>Coaches' times</h2>
        <button className="btn btn-ghost btn-sm" onClick={() => setOpen(!open)}>{open ? "Hide coaches" : `Show all ${plural(lg.coaches.length, "coach", "coaches")}`}</button>
      </div>
      <p className="muted small">
        Add times a coach can't make, and the schedule will never put their teams there. Times they'd rather coach are honoured when there's room.
        {withTimes ? ` ${plural(withTimes, "coach", "coaches")} ${withTimes === 1 ? "has" : "have"} times set.` : ""}
      </p>
      {open && (
        <table className="data" style={{ marginTop: 8 }}>
          <thead><tr><th>Coach</th><th>Teams</th><th>Can't make</th><th>Would rather coach</th><th></th></tr></thead>
          <tbody>
            {lg.coaches.map((c) => (
              <tr key={c.id}>
                <td style={{ fontWeight: 500 }}>{c.name}</td>
                <td className="muted">{teamNames(c)}</td>
                <td>{(c.unavailable ?? []).map(describeTime).join("; ")}</td>
                <td>{(c.prefers ?? []).map(describeTime).join("; ")}</td>
                <td style={{ width: 40 }}><button className="icon-btn" aria-label={`Edit ${c.name}`} onClick={() => setEditing(c)}><Icon name="edit" style={{ fontSize: 18 }} /></button></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {editing && <CoachDialog {...{ lg, save }} coach={editing} onClose={() => setEditing(null)} />}
    </div>
  );
}

function CoachDialog({ lg, save, coach, onClose }: { lg: League; save: Save; coach: Coach; onClose: () => void }) {
  const [off, setOff] = useState<TimeOff[]>(coach.unavailable ?? []);
  const [prefers, setPrefers] = useState<TimeOff[]>(coach.prefers ?? []);
  const submit = async () => {
    const coaches = lg.coaches.map((c) => (c.id === coach.id ? { ...c, unavailable: off, prefers } : c));
    if (await save({ ...lg, coaches }, `Changed ${coach.name}'s times`)) onClose();
  };
  return (
    <Modal title={coach.name} onClose={onClose} wide
      footer={<>
        <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" onClick={submit}>Save</button>
      </>}>
      <TimeList title="Can't make" hint="Their teams never play at these times." items={off} setItems={setOff} lg={lg} />
      <TimeList title="Would rather coach" hint="When there's a choice, their teams play at these times." items={prefers} setItems={setPrefers} lg={lg} />
    </Modal>
  );
}

function TimeList({ title, hint, items, setItems, lg }: {
  title: string; hint: string; items: TimeOff[]; setItems: (t: TimeOff[]) => void; lg: League;
}) {
  const [when, setWhen] = useState("1"); // weekday index, or "date"
  const [day, setDay] = useState(lg.season_start);
  const [allDay, setAllDay] = useState(true);
  const [start, setStart] = useState("17:00");
  const [end, setEnd] = useState("19:00");
  const ok = (when !== "date" || day) && (allDay || start < end);
  const add = () => {
    const t: TimeOff = {
      weekday: when === "date" ? null : Number(when), day: when === "date" ? day : null,
      start: allDay ? null : `${start}:00`, end: allDay ? null : `${end}:00`,
    };
    setItems([...items, t]);
  };
  return (
    <div className="stack">
      <h3>{title}</h3>
      <p className="muted small">{hint}</p>
      <div className="row wrap" style={{ gap: 6 }}>
        {items.length === 0 && <span className="muted small">None.</span>}
        {items.map((t, i) => (
          <span key={i} className="chip">{describeTime(t)}
            <button className="chip-x" aria-label={`Remove ${describeTime(t)}`} onClick={() => setItems(items.filter((_, j) => j !== i))}><Icon name="close" style={{ fontSize: 14 }} /></button>
          </span>
        ))}
      </div>
      <div className="row wrap" style={{ alignItems: "flex-end" }}>
        <label className="field">When
          <select className="input" value={when} onChange={(e) => setWhen(e.target.value)} aria-label={`${title}: when`}>
            {EVERY.map((d, i) => <option key={d} value={String(i)}>Every {d.slice(0, -1)}</option>)}
            <option value="date">One date</option>
          </select>
        </label>
        {when === "date" && <label className="field">Date<input className="input" type="date" value={day} onChange={(e) => setDay(e.target.value)} /></label>}
        <label className="row small" style={{ cursor: "pointer", gap: 6, paddingBottom: 10 }}>
          <input type="checkbox" checked={allDay} onChange={(e) => setAllDay(e.target.checked)} />All day
        </label>
        {!allDay && <>
          <label className="field">From<input className="input" type="time" value={start} onChange={(e) => setStart(e.target.value)} /></label>
          <label className="field">To<input className="input" type="time" value={end} onChange={(e) => setEnd(e.target.value)} /></label>
        </>}
        <button className="btn btn-soft btn-sm" style={{ marginBottom: 6 }} disabled={!ok} onClick={add}>Add</button>
      </div>
    </div>
  );
}

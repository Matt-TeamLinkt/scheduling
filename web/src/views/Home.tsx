import { useEffect, useState } from "react";
import { api, ApiError } from "../api";
import { isoDate } from "../format";
import { Icon, Note } from "../ui";

const SPORTS = ["hockey", "soccer", "baseball", "softball", "basketball", "volleyball", "other"];

export function Home() {
  const [seasons, setSeasons] = useState<{ id: string; name: string; published: boolean }[]>([]);
  const [samples, setSamples] = useState<{ id: string; description: string }[]>([]);
  const [name, setName] = useState("");
  const [sport, setSport] = useState("soccer");
  const today = new Date();
  const [start, setStart] = useState(isoDate(today));
  const [end, setEnd] = useState(isoDate(new Date(today.getTime() + 12 * 7 * 864e5)));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.seasons().then(setSeasons);
    api.samples().then(setSamples);
  }, []);

  const open = (id: string) => (window.location.hash = `#/s/${id}/setup`);
  const create = async (sample?: string) => {
    setError(null);
    try {
      const s = sample
        ? await api.create({ name: samples.find((x) => x.id === sample)?.description ?? "Sample league", sample })
        : await api.create({ name: name.trim(), sport, season_start: start, season_end: end });
      window.location.hash = `#/s/${s.id}/${sample ? "schedule" : "setup"}`;
    } catch (e) {
      setError((e as ApiError).message);
    }
  };

  return (
    <div className="page">
      <div>
        <h1>Your seasons</h1>
        <p className="muted" style={{ marginTop: 4 }}>Load your teams and time slots, set a few rules, and get a fair schedule in minutes.</p>
      </div>

      {seasons.length > 0 && (
        <div className="stack">
          {seasons.map((s) => (
            <div key={s.id} className="list-row" style={{ cursor: "pointer" }} onClick={() => open(s.id)}>
              <Icon name="calendar_month" style={{ color: "var(--tl-fg-muted)" }} />
              <div style={{ flex: 1, fontWeight: 500, color: "var(--tl-fg)" }}>{s.name}</div>
              {s.published ? <span className="chip chip-green">Published</span> : <span className="chip">Draft</span>}
              <Icon name="chevron_right" style={{ color: "var(--tl-fg-muted)" }} />
            </div>
          ))}
        </div>
      )}

      <div className="card">
        <div className="card-head"><h2>Start a new season</h2></div>
        <div className="grid2">
          <label className="field">Season name
            <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Spring 2027 house league" />
          </label>
          <label className="field">Sport
            <select className="input" value={sport} onChange={(e) => setSport(e.target.value)}>
              {SPORTS.map((s) => <option key={s} value={s}>{s[0].toUpperCase() + s.slice(1)}</option>)}
            </select>
          </label>
          <label className="field">First day
            <input className="input" type="date" value={start} onChange={(e) => setStart(e.target.value)} />
          </label>
          <label className="field">Last day
            <input className="input" type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
          </label>
        </div>
        <div className="row" style={{ marginTop: 16 }}>
          <button className="btn btn-primary" disabled={!name.trim()} onClick={() => create()}>Create season</button>
          {error && <span style={{ color: "var(--tl-error)" }}>{error}</span>}
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <h2>Or try a sample league</h2>
        </div>
        <Note>Samples come with teams, coaches, families and time slots already loaded, so you can see a schedule straight away.</Note>
        <div className="stack" style={{ marginTop: 12 }}>
          {samples.map((s) => (
            <div key={s.id} className="list-row">
              <Icon name="sports" style={{ color: "var(--tl-fg-muted)" }} />
              <div style={{ flex: 1 }}>{s.description}</div>
              <button className="btn btn-soft" onClick={() => create(s.id)}>Try it</button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

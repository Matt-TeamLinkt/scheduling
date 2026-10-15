import { useState } from "react";
import { api, ApiError, waitForJob, type Job, type Season } from "../api";
import { Icon, Modal, Note, Progress } from "../ui";

export function GenerateDialog({ season, onClose, onDone }: {
  season: Season; onClose: () => void; onDone: (s: Season, summary: string) => void;
}) {
  const [order, setOrder] = useState(season.goals);
  const [thorough, setThorough] = useState(true);
  const hasSchedule = season.events.length > 0;
  const [fresh, setFresh] = useState(!hasSchedule);
  const [advanced, setAdvanced] = useState(false);
  const [division, setDivision] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState<number | null>(null);

  const move = (i: number, j: number) => {
    if (j < 0 || j >= order.length || i === j) return;
    const next = order.slice();
    const [g] = next.splice(i, 1);
    next.splice(j, 0, g);
    setOrder(next);
  };

  const run = async () => {
    setError(null);
    try {
      const scope = !fresh && advanced && (division || from || to)
        ? { division_ids: division ? [division] : null, start: from || null, end: to || null } : undefined;
      const { job_id } = await api.generate(season.id, {
        priorities: order.map((g) => g.id), seconds: thorough ? 60 : 20, fresh, scope,
      });
      const done = await waitForJob(job_id, setJob);
      if (done.state === "failed") return setError(done.message);
      onDone(await api.season(season.id), done.result.summary ?? "Done.");
    } catch (e) {
      setError((e as ApiError).message);
    }
  };

  const running = job?.state === "running";
  if (job && running) {
    const share = job.phase === "improving" ? 0.4 + 0.6 * Math.min(1, job.seconds / (thorough ? 60 : 20))
      : job.total ? 0.4 * (job.placed / job.total) : 0.05;
    return (
      <Modal title="Building your schedule" onClose={() => {}}>
        <Progress value={share} />
        <p>{job.message}</p>
        <p className="muted small">This takes about {thorough ? "a minute" : "20 seconds"}. You can leave this open.</p>
      </Modal>
    );
  }

  return (
    <Modal title={hasSchedule ? "Generate again" : "Generate the schedule"} onClose={onClose}
      subtitle="Every hard rule is always respected. Rank what matters most when there's a trade-off."
      footer={<>
        <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" onClick={run}><Icon name="auto_awesome" style={{ fontSize: 18 }} />Generate</button>
      </>}>
      {hasSchedule && (
        <div className="stack">
          <label className="row" style={{ cursor: "pointer" }}>
            <input type="radio" checked={!fresh} onChange={() => setFresh(false)} />
            <span><b>Improve the current schedule.</b> <span className="muted">Same matchups. Locked games stay where they are.</span></span>
          </label>
          <label className="row" style={{ cursor: "pointer" }}>
            <input type="radio" checked={fresh} onChange={() => setFresh(true)} />
            <span><b>Start over.</b> <span className="muted">New matchups from your teams. Use this after adding or removing teams.</span></span>
          </label>
        </div>
      )}
      <div>
        <h3 style={{ marginBottom: 6 }}>What matters most</h3>
        <p className="muted small" style={{ marginBottom: 8 }}>Drag to reorder. The top one wins when two goals pull different ways.</p>
        <div className="ranked">
          {order.map((g, i) => (
            <div key={g.id} className="list-row" draggable
              onDragStart={() => setDragging(i)} onDragOver={(e) => e.preventDefault()}
              onDrop={() => { if (dragging !== null) move(dragging, i); setDragging(null); }}>
              <span className="rank-n">{i + 1}</span>
              <span style={{ flex: 1 }}>{g.label}</span>
              <button className="icon-btn" aria-label="Move up" disabled={i === 0} onClick={() => move(i, i - 1)}><Icon name="arrow_upward" style={{ fontSize: 18 }} /></button>
              <button className="icon-btn" aria-label="Move down" disabled={i === order.length - 1} onClick={() => move(i, i + 1)}><Icon name="arrow_downward" style={{ fontSize: 18 }} /></button>
            </div>
          ))}
        </div>
      </div>
      <div className="row">
        <label className="row" style={{ cursor: "pointer" }}><input type="radio" checked={thorough} onChange={() => setThorough(true)} />Thorough (about a minute)</label>
        <label className="row" style={{ cursor: "pointer" }}><input type="radio" checked={!thorough} onChange={() => setThorough(false)} />Quick (about 20 seconds)</label>
      </div>
      {hasSchedule && !fresh && (
        <div>
          <label className="row small muted" style={{ cursor: "pointer", gap: 6 }}>
            <input type="checkbox" checked={advanced} onChange={(e) => setAdvanced(e.target.checked)} />
            Only redo part of the season
          </label>
          {advanced && (
            <div className="row wrap" style={{ marginTop: 8, alignItems: "flex-end" }}>
              <label className="field">Division
                <select className="input" value={division} onChange={(e) => setDivision(e.target.value)}>
                  <option value="">All divisions</option>
                  {season.league.divisions.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                </select>
              </label>
              <label className="field">From<input className="input" type="date" value={from} onChange={(e) => setFrom(e.target.value)} /></label>
              <label className="field">To<input className="input" type="date" value={to} onChange={(e) => setTo(e.target.value)} /></label>
            </div>
          )}
        </div>
      )}
      {error && <Note tone="bad">{error}</Note>}
    </Modal>
  );
}

import { useEffect, useState } from "react";
import type { Ctx } from "../App";
import { api, type Report } from "../api";
import { Note } from "../ui";

export function Fairness({ season }: Ctx) {
  const [rep, setRep] = useState<Report | null>(null);
  const [division, setDivision] = useState("");
  useEffect(() => { api.report(season.id).then(setRep); }, [season.id, season.version]);

  if (!season.events.length) return <div className="page"><Note>Generate a schedule to see how fair it is.</Note></div>;
  if (!rep) return <div className="page"><p className="muted">Checking fairness…</p></div>;

  const divisions = [...new Set(rep.teams.map((t) => t.division))];
  const teams = rep.teams.filter((t) => !division || t.division === division);
  const flagged = new Set(rep.flags.flatMap((f) => f.team_ids));
  const avg = (xs: number[]) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0);
  const byDiv = Object.fromEntries(divisions.map((d) => [d, avg(rep.teams.filter((t) => t.division === d).map((t) => t.early_or_late))]));

  return (
    <div className="page">
      <div>
        <h1>Fairness</h1>
        <p className="muted" style={{ marginTop: 4 }}>How the schedule treats each team. Anything unusual is listed first.</p>
      </div>
      <Note tone={rep.flags.length ? "warn" : "ok"}>{rep.summary}</Note>
      {rep.flags.length > 0 && (
        <div className="card stack">
          <h2>Worth a look</h2>
          {rep.flags.map((f, i) => <div key={i} className="row"><span className="icon" style={{ color: "var(--tl-warning)", fontSize: 18 }}>flag</span>{f.message}</div>)}
        </div>
      )}
      <div className="card" style={{ padding: 0 }}>
        <div className="row" style={{ padding: 16 }}>
          <h2 style={{ flex: 1 }}>Every team</h2>
          <select className="input" value={division} onChange={(e) => setDivision(e.target.value)} aria-label="Division">
            <option value="">All divisions</option>
            {divisions.map((d) => <option key={d}>{d}</option>)}
          </select>
        </div>
        <div style={{ overflowX: "auto" }}>
          <table className="data">
            <thead>
              <tr>
                <th>Team</th><th>Division</th><th className="num">Games</th><th className="num">Home</th><th className="num">Away</th>
                <th className="num">Early or late</th><th className="num">Back-to-back days</th><th className="num">Longest break (days)</th>
                <th className="num">Quickest rematch (days)</th><th className="num">Travel (km)</th>
              </tr>
            </thead>
            <tbody>
              {teams.map((t) => (
                <tr key={t.team_id} style={flagged.has(t.team_id) ? { background: "rgba(229,159,41,.06)" } : undefined}>
                  <td style={{ fontWeight: 500 }}>{t.name}</td>
                  <td>{t.division}</td>
                  <td className={`num${t.games < t.target ? " flag" : ""}`}>{t.games}{t.games < t.target && ` of ${t.target}`}</td>
                  <td className={`num${Math.abs(t.home - t.away) >= 2 ? " flag" : ""}`}>{t.home}</td>
                  <td className={`num${Math.abs(t.home - t.away) >= 2 ? " flag" : ""}`}>{t.away}</td>
                  <td className={`num${t.early_or_late >= byDiv[t.division] + 2 ? " flag" : ""}`}>{t.early_or_late}</td>
                  <td className={`num${t.back_to_back_days >= 3 ? " flag" : ""}`}>{t.back_to_back_days}</td>
                  <td className={`num${t.longest_gap_days >= 21 ? " flag" : ""}`}>{t.longest_gap_days}</td>
                  <td className={`num${t.quickest_rematch_days !== null && t.quickest_rematch_days < 7 ? " flag" : ""}`}>{t.quickest_rematch_days ?? "–"}</td>
                  <td className="num">{t.travel_km ? Math.round(t.travel_km) : "–"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      {rep.family_clashes.length > 0 && (
        <div className="card stack">
          <h2>Families with a clash</h2>
          {rep.family_clashes.map((c, i) => <p key={i}>{c}</p>)}
        </div>
      )}
    </div>
  );
}

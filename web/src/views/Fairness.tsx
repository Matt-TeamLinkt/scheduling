import { useEffect, useState } from "react";
import type { Ctx } from "../App";
import { api, type Report } from "../api";
import { plural } from "../format";
import { Icon, Note } from "../ui";
import { DownloadButton } from "./ScheduleViews";

export function Fairness({ season, toast }: Ctx) {
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
      <div className="row">
        <div style={{ flex: 1 }}>
          <h1>Fairness</h1>
          <p className="muted" style={{ marginTop: 4 }}>How the schedule treats each team. Anything unusual is listed first.</p>
        </div>
        <DownloadButton season={season} toast={toast} />
      </div>
      <div className="card stack">
        <h2>What stands out</h2>
        {(rep.highlights ?? [rep.summary]).map((h, i) => (
          <div key={i} className="row">
            <Icon name={rep.flags.length ? "flag" : "check_circle"} style={{ color: rep.flags.length ? "var(--tl-warning)" : "var(--tl-success)", fontSize: 18 }} />{h}
          </div>
        ))}
        {rep.flags.length > 0 && (
          <details>
            <summary style={{ cursor: "pointer" }} className="muted small">See all {plural(rep.flags.length, "note")}</summary>
            <div className="stack" style={{ marginTop: 8 }}>
              {rep.flags.map((f, i) => <div key={i} className="small">{f.message}</div>)}
            </div>
          </details>
        )}
      </div>
      {rep.divisions && rep.divisions.length > 0 && (
        <div className="div-cards">
          {rep.divisions.map((d) => (
            <button key={d.name} className={`card div-card${division === d.name ? " on" : ""}`} onClick={() => setDivision(division === d.name ? "" : d.name)}
              title="Show only this division's teams below">
              <div className="row">
                <h3 style={{ flex: 1 }}>{d.name}</h3>
                {d.flags ? <span className="chip chip-amber">{plural(d.flags, "note")}</span> : <span className="chip chip-green">Even</span>}
              </div>
              <p className="small">{d.verdict}</p>
              <div className="muted small">
                {plural(d.teams, "team")} · {plural(d.games, "game")} · longest break {d.longest_gap_days} days
                {d.back_to_back_days ? ` · ${plural(d.back_to_back_days, "back-to-back")}` : ""}
                {d.quickest_rematch_days !== null ? ` · quickest rematch ${d.quickest_rematch_days} days` : ""}
              </div>
            </button>
          ))}
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

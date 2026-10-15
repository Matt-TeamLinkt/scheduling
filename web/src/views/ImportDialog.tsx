import { useRef, useState } from "react";
import { api, ApiError, type ImportPreview, type Season } from "../api";
import { Icon, Modal, Note } from "../ui";

const KINDS = {
  teams: { title: "Import teams", hint: "A spreadsheet with a column for team name and division. Coach, coach email and home venue columns are picked up too." },
  slots: { title: "Import time slots", hint: "The ice or field times your facilities gave you: venue, date, and start and end time (or a time range like 7:00 PM - 8:15 PM)." },
  coaches: { title: "Import coaches", hint: "Coach name and team. A coach listed on several teams is never scheduled in two places at once." },
} as const;
export type ImportKind = keyof typeof KINDS;

export function ImportDialog({ season, kind, onClose, onDone }: {
  season: Season; kind: ImportKind; onClose: () => void; onDone: (s: Season, summary: string) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const choose = async (f: File) => {
    setFile(f);
    setError(null);
    setBusy("Reading your file…");
    try { setPreview(await api.importFile(season.id, kind, f, false)); }
    catch (e) { setError((e as ApiError).message); }
    finally { setBusy(null); }
  };
  const apply = async () => {
    if (!file) return;
    setBusy("Importing…");
    try {
      const r = await api.importFile(season.id, kind, file, true);
      if (r.season) onDone(r.season, r.summary.replace("We'll add", "Added").replace("will be left out", "were left out")
        .replace("need a quick look", "may need a quick look").replace("needs a quick look", "may need a quick look"));
    } catch (e) { setError((e as ApiError).message); }
    finally { setBusy(null); }
  };

  const levels = [
    { id: "skipped", label: "Left out", tone: "bad" as const },
    { id: "check", label: "Worth a quick look", tone: "warn" as const },
    { id: "note", label: "Good to know", tone: "info" as const },
  ];

  return (
    <Modal wide title={KINDS[kind].title} subtitle={KINDS[kind].hint} onClose={onClose}
      footer={<>
        <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" disabled={!preview?.can_import || !!busy} onClick={apply}>Import</button>
      </>}>
      <input ref={input} type="file" accept=".csv,.xlsx,.xlsm,.txt" hidden
        onChange={(e) => e.target.files?.[0] && choose(e.target.files[0])} />
      <div className="drop" onClick={() => input.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) choose(f); }}>
        <Icon name="upload_file" style={{ fontSize: 28, color: "var(--tl-blue)" }} />
        <div style={{ marginTop: 6, fontWeight: 500 }}>{file ? file.name : "Choose a CSV or Excel file"}</div>
        <div className="muted small">or drop it here. Nothing changes until you press Import.</div>
      </div>
      {busy && <p className="muted">{busy}</p>}
      {error && <Note tone="bad">{error}</Note>}
      {preview && (
        <>
          <Note tone={preview.can_import ? "ok" : "bad"}>{preview.summary}</Note>
          {preview.columns.length > 0 && (
            <div>
              <h3 style={{ marginBottom: 6 }}>Columns we found</h3>
              <div className="row wrap" style={{ gap: 6 }}>
                {preview.columns.map((c) => (
                  <span key={c.header} className={`chip ${c.field ? "chip-blue" : ""}`} title={c.field ? `Read as ${c.field}` : "Not used"}>
                    {c.header}{c.field ? ` → ${c.field}` : " (not used)"}
                  </span>
                ))}
              </div>
            </div>
          )}
          {levels.map((lv) => {
            const ps = preview.problems.filter((p) => p.level === lv.id);
            if (!ps.length) return null;
            return (
              <div key={lv.id} className="stack">
                <h3>{lv.label} ({ps.length})</h3>
                {ps.map((p, i) => <Note key={i} tone={lv.tone}>{p.message}</Note>)}
              </div>
            );
          })}
        </>
      )}
    </Modal>
  );
}

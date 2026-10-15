import { useEffect, useState } from "react";
import type { Ctx } from "../App";
import { api, ApiError, type Change } from "../api";
import { plural } from "../format";
import { Icon, Modal, Note } from "../ui";

const KIND_ICON: Record<string, string> = { added: "add_circle", cancelled: "cancel", moved: "schedule", swapped: "swap_horiz" };

export function Publish({ season, setSeason, toast }: Ctx) {
  const [preview, setPreview] = useState<{ changes: Change[]; teams_affected: number } | null>(null);
  const [history, setHistory] = useState<{ version: number; published_at: string; changes: Change[] }[]>([]);
  const [confirm, setConfirm] = useState(false);
  useEffect(() => {
    api.publishPreview(season.id).then(setPreview);
    api.publications(season.id).then(setHistory);
  }, [season.id, season.version, season.published_version]);

  const publish = async () => {
    setConfirm(false);
    try { setSeason(await api.publish(season.id)); } catch (e) { toast((e as ApiError).message); }
  };
  const first = season.published_version === null;
  const n = preview?.changes.length ?? 0;

  return (
    <div className="page">
      <div>
        <h1>Publish</h1>
        <p className="muted" style={{ marginTop: 4 }}>Nothing reaches families until you publish. Every publish is recorded with exactly what changed.</p>
      </div>
      {!season.events.length ? (
        <Note>Generate a schedule first.</Note>
      ) : (
        <div className="card">
          <div className="card-head">
            <h2 style={{ flex: 1 }}>{first ? "Not published yet" : n ? `${plural(n, "change")} since you last published` : "Families have the latest schedule"}</h2>
            <button className="btn btn-dark" disabled={!n} onClick={() => setConfirm(true)}>
              <Icon name="send" style={{ fontSize: 18 }} />{first ? "Publish the schedule" : "Publish changes"}
            </button>
          </div>
          {preview && n > 0 && (
            <>
              <p className="muted small" style={{ marginBottom: 8 }}>{plural(preview.teams_affected, "team")} will see changes.{first ? "" : " Only those teams need to hear about it."}</p>
              <div className="stack" style={{ maxHeight: 360, overflow: "auto" }}>
                {preview.changes.slice(0, first ? 0 : 200).map((c, i) => (
                  <div key={i} className="row"><Icon name={KIND_ICON[c.kind] ?? "edit"} style={{ fontSize: 18, color: "var(--tl-fg-muted)" }} />{c.message}</div>
                ))}
                {first && <p>Every team gets its full schedule: {plural(season.events.length, "game")}.</p>}
              </div>
            </>
          )}
        </div>
      )}
      {season.unplaced.length > 0 && n > 0 && (
        <Note tone="warn">{plural(season.unplaced.length, "game")} still didn't fit. You can publish now and add them later; families will only hear about the change.</Note>
      )}
      {history.length > 0 && (
        <div className="card stack">
          <h2>Published before</h2>
          {history.map((h) => (
            <details key={h.published_at}>
              <summary style={{ cursor: "pointer" }}>{new Date(h.published_at).toLocaleString()} · {plural(h.changes.length, "change")}</summary>
              <div className="stack" style={{ marginTop: 8, paddingLeft: 12 }}>
                {h.changes.slice(0, 100).map((c, i) => <p key={i} className="small">{c.message}</p>)}
                {h.changes.length > 100 && <p className="muted small">…and {h.changes.length - 100} more</p>}
              </div>
            </details>
          ))}
        </div>
      )}
      {confirm && (
        <Modal title={first ? "Publish the schedule?" : `Publish ${plural(n, "change")}?`} onClose={() => setConfirm(false)}
          footer={<>
            <button className="btn btn-ghost" onClick={() => setConfirm(false)}>Not yet</button>
            <button className="btn btn-dark" onClick={publish}>Publish</button>
          </>}>
          <p>{first ? "Families will be able to see the full schedule." : `${plural(preview?.teams_affected ?? 0, "team")} will see what changed.`} You can keep editing afterwards; changes stay in draft until you publish again.</p>
        </Modal>
      )}
    </div>
  );
}

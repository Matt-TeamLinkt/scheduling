import { useCallback, useEffect, useState } from "react";
import { api, ApiError, type Season } from "./api";
import { plural } from "./format";
import { Icon } from "./ui";
import { Home } from "./views/Home";
import { Setup } from "./views/Setup";
import { Schedule } from "./views/Schedule";
import { Fairness } from "./views/Fairness";
import { Publish } from "./views/Publish";

export type Tab = "setup" | "schedule" | "fairness" | "publish";
const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: "setup", label: "Setup", icon: "tune" },
  { id: "schedule", label: "Schedule", icon: "calendar_month" },
  { id: "fairness", label: "Fairness", icon: "balance" },
  { id: "publish", label: "Publish", icon: "send" },
];

function readHash(): { seasonId: string | null; tab: Tab } {
  const [, s, id, tab] = window.location.hash.split("/");
  if (s === "s" && id) return { seasonId: id, tab: (TABS.some((t) => t.id === tab) ? tab : "setup") as Tab };
  return { seasonId: null, tab: "setup" };
}

/** Shared by every view: the season, a way to replace it, and a toast. */
export interface Ctx {
  season: Season;
  setSeason: (s: Season) => void;
  toast: (msg: string) => void;
  go: (tab: Tab) => void;
}

export function App() {
  const [route, setRoute] = useState(readHash);
  const [season, setSeasonState] = useState<Season | null>(null);
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  useEffect(() => {
    const onHash = () => setRoute(readHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const toast = useCallback((msg: string) => {
    setToastMsg(msg);
    window.setTimeout(() => setToastMsg((m) => (m === msg ? null : m)), 4500);
  }, []);

  const setSeason = useCallback((s: Season) => {
    setSeasonState(s);
    if (s.message) toast(s.message);
  }, [toast]);

  useEffect(() => {
    if (!route.seasonId) return setSeasonState(null);
    if (season?.id === route.seasonId) return;
    api.season(route.seasonId).then(setSeasonState).catch(() => (window.location.hash = "#/"));
  }, [route.seasonId, season?.id]);

  const go = useCallback((tab: Tab) => {
    if (season) window.location.hash = `#/s/${season.id}/${tab}`;
  }, [season]);

  const undo = useCallback(async () => {
    if (!season?.can_undo) return;
    try { setSeason(await api.undo(season.id)); } catch (e) { toast((e as ApiError).message); }
  }, [season, setSeason, toast]);
  const redo = useCallback(async () => {
    if (!season?.can_redo) return;
    try { setSeason(await api.redo(season.id)); } catch (e) { toast((e as ApiError).message); }
  }, [season, setSeason, toast]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const typing = (e.target as HTMLElement)?.closest("input, select, textarea");
      if (typing || !(e.metaKey || e.ctrlKey) || e.key.toLowerCase() !== "z") return;
      e.preventDefault();
      if (e.shiftKey) redo(); else undo();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [undo, redo]);

  const ctx: Ctx | null = season ? { season, setSeason, toast, go } : null;

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand" onClick={() => (window.location.hash = "#/")}>
          <div className="mark"><Icon name="check" style={{ fontVariationSettings: "'FILL' 1, 'wght' 600" }} /></div>
          Scheduling
        </div>
        {season && (
          <>
            <div className="divider-v" />
            <div style={{ fontWeight: 500, color: "var(--tl-fg)" }}>{season.name}</div>
            <nav className="tabs">
              {TABS.map((t) => (
                <button key={t.id} className={`tab${route.tab === t.id ? " active" : ""}`} onClick={() => go(t.id)}>
                  <Icon name={t.icon} style={{ fontSize: 16 }} />{t.label}
                </button>
              ))}
            </nav>
            <div className="spacer" />
            <div className="status" title={season.last_action}>
              {season.published_version === null ? (
                <><span className="chip">Draft</span> Not published yet</>
              ) : season.unpublished_changes ? (
                <><span className="chip chip-amber">Draft</span>{plural(season.unpublished_changes, "change")} not published</>
              ) : (
                <><span className="chip chip-green">Published</span>Families see the latest</>
              )}
            </div>
            <button className="icon-btn" title="Undo (Ctrl+Z)" aria-label="Undo" disabled={!season.can_undo} onClick={undo}>
              <Icon name="undo" />
            </button>
            <button className="icon-btn" title="Redo (Ctrl+Shift+Z)" aria-label="Redo" disabled={!season.can_redo} onClick={redo}>
              <Icon name="redo" />
            </button>
          </>
        )}
      </header>
      {import.meta.env.VITE_DEMO === "1" && (
        <div className="demo-bar">
          Preview with sample leagues. The schedules, fairness reports and explanations were made by the real
          scheduling engine. Drag checks here are a simplified version, and importing your own files needs the full app.
          Nothing you do here is saved.
        </div>
      )}
      <main className="main">
        {!route.seasonId && <Home />}
        {ctx && route.tab === "setup" && <Setup {...ctx} />}
        {ctx && route.tab === "schedule" && <Schedule {...ctx} />}
        {ctx && route.tab === "fairness" && <Fairness {...ctx} />}
        {ctx && route.tab === "publish" && <Publish {...ctx} />}
      </main>
      {toastMsg && (
        <div className="toast" role="status">
          {toastMsg}
          <button className="icon-btn" style={{ color: "#fff", width: 24, height: 24 }} onClick={() => setToastMsg(null)} aria-label="Dismiss">
            <Icon name="close" style={{ fontSize: 16 }} />
          </button>
        </div>
      )}
    </div>
  );
}

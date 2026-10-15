// Plain-language formatting shared by every view.

import type { GameEvent, League } from "./api";

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function parseDate(iso: string): Date {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function isoDate(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export function fmtDay(iso: string): string {
  const d = parseDate(iso);
  return `${DAYS[d.getDay()]} ${MONTHS[d.getMonth()]} ${d.getDate()}`;
}

/** "07:00:00" or "2027-01-09T07:00:00" -> "7:00 AM" */
export function fmtTime(t: string): string {
  const hhmm = t.includes("T") ? t.split("T")[1] : t;
  const [h, m] = hhmm.split(":").map(Number);
  const ap = h < 12 ? "AM" : "PM";
  return `${h % 12 || 12}:${String(m).padStart(2, "0")} ${ap}`;
}

export function minutes(t: string): number {
  const hhmm = t.includes("T") ? t.split("T")[1] : t;
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + m;
}

export function plural(n: number, word: string, many?: string): string {
  return `${n} ${n === 1 ? word : many ?? word + "s"}`;
}

export class Lookup {
  constructor(public league: League) {}
  team = (id: string | null) => this.league.teams.find((t) => t.id === id)?.name ?? "?";
  division = (id: string) => this.league.divisions.find((d) => d.id === id)?.name ?? "";
  slot = (id: string) => this.league.slots.find((s) => s.id === id);
  surface = (id: string) => this.league.surfaces.find((s) => s.id === id);
  venue = (id: string) => this.league.venues.find((v) => v.id === id);
  place = (slotId: string) => {
    const sl = this.slot(slotId);
    const sf = sl && this.surface(sl.surface_id);
    const v = sf && this.venue(sf.venue_id);
    if (!sf) return "?";
    return v && v.name !== sf.name ? `${v.name} ${sf.name}` : sf.name;
  };
  matchup = (e: Pick<GameEvent, "home_team_id" | "away_team_id">) =>
    e.away_team_id ? `${this.team(e.home_team_id)} vs ${this.team(e.away_team_id)}` : `${this.team(e.home_team_id)} practice`;
}

// Division colors from the brand palette, assigned by position.
const PALETTE = ["rgb(36,84,255)", "rgb(48,164,108)", "rgb(229,159,41)", "rgb(147,51,234)", "rgb(6,182,212)", "rgb(219,39,119)"];
export function divisionColor(league: League, divisionId: string): string {
  const i = league.divisions.findIndex((d) => d.id === divisionId);
  return PALETTE[(i < 0 ? 0 : i) % PALETTE.length];
}

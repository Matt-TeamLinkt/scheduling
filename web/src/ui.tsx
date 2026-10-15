import { useEffect, type ReactNode } from "react";

export function Icon({ name, style }: { name: string; style?: React.CSSProperties }) {
  return <span className="icon" aria-hidden="true" style={style}>{name}</span>;
}

export function Modal({ title, subtitle, children, footer, onClose, wide }: {
  title: string; subtitle?: string; children: ReactNode; footer?: ReactNode; onClose: () => void; wide?: boolean;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div className="backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`modal${wide ? " wide" : ""}`} role="dialog" aria-label={title}>
        <div className="modal-head">
          <h2>{title}</h2>
          {subtitle && <p className="muted small" style={{ marginTop: 4 }}>{subtitle}</p>}
        </div>
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-foot">{footer}</div>}
      </div>
    </div>
  );
}

export function Note({ tone = "info", icon, children }: { tone?: "info" | "warn" | "ok" | "bad"; icon?: string; children: ReactNode }) {
  const color = { info: "var(--tl-fg-muted)", warn: "var(--tl-warning)", ok: "var(--tl-success)", bad: "var(--tl-error)" }[tone];
  const fallback = { info: "info", warn: "warning", ok: "check_circle", bad: "error" }[tone];
  return (
    <div className={`note ${tone === "info" ? "" : tone}`}>
      <Icon name={icon ?? fallback} style={{ color, fontSize: 18 }} />
      <div style={{ flex: 1 }}>{children}</div>
    </div>
  );
}

export function Progress({ value }: { value: number }) {
  return <div className="bar"><div style={{ width: `${Math.max(3, Math.min(100, value * 100))}%` }} /></div>;
}

import type { ReactNode } from "react";

import { cn } from "../lib/cn";

/** A section separated by a top hairline rule. Header carries an eyebrow label + optional aside. */
export function Panel({
  eyebrow,
  aside,
  children,
  className,
}: {
  eyebrow?: string;
  aside?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={cn(
        "border-t border-hairline pt-5",
        className,
      )}
    >
      {(eyebrow || aside) && (
        <header className="mb-4 flex items-baseline justify-between gap-4">
          {eyebrow ? <Eyebrow>{eyebrow}</Eyebrow> : <span />}
          {aside}
        </header>
      )}
      {children}
    </section>
  );
}

/** Uppercase tracked label — the structural eyebrow. */
export function Eyebrow({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <span
      className={cn(
        "text-[0.6875rem] font-medium uppercase tracking-[0.08em] text-muted",
        className,
      )}
    >
      {children}
    </span>
  );
}

type PillTone = "iris" | "warn" | "danger" | "neutral";

const PILL_TONES: Record<PillTone, string> = {
  iris: "border-iris/40 bg-iris-dim text-iris-fg",
  warn: "border-warn/40 bg-warn-dim text-warn-fg",
  danger: "border-danger/40 bg-danger-dim text-danger-fg",
  neutral: "border-line bg-elevated text-secondary",
};

/** A small status pill. Always pairs color with text (never color-alone). */
export function StatusPill({
  tone = "neutral",
  children,
  className,
}: {
  tone?: PillTone;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5",
        "font-mono text-[0.6875rem] tracking-tight",
        PILL_TONES[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

/** A labelled metric readout: mono value over a small sans label. */
export function Stat({
  label,
  value,
  sub,
  tone,
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  tone?: "iris" | "warn" | "fg";
}) {
  const valueColor =
    tone === "iris" ? "text-iris-fg" : tone === "warn" ? "text-warn-fg" : "text-fg";
  return (
    <div className="flex flex-col gap-1">
      <Eyebrow>{label}</Eyebrow>
      <span className={cn("font-mono text-2xl leading-none tnum", valueColor)}>{value}</span>
      {sub && <span className="font-mono text-[0.75rem] text-muted tnum">{sub}</span>}
    </div>
  );
}

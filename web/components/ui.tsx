import type { ReactNode } from "react";

import { cn } from "../lib/cn";

export const FOCUS_RING =
  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-iris";

type ButtonVariant = "primary" | "secondary" | "ghost";

/** One button vocabulary for links and buttons: ink primary, outlined secondary, quiet ghost. */
export function buttonClass(variant: ButtonVariant = "primary", className?: string): string {
  return cn(
    "inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors",
    "disabled:cursor-not-allowed disabled:opacity-50",
    FOCUS_RING,
    variant === "primary" && "bg-fg text-paper hover:bg-fg/85",
    variant === "secondary" && "border border-line bg-surface text-fg hover:border-edge hover:bg-elevated",
    variant === "ghost" && "px-2 text-secondary hover:text-fg",
    className,
  );
}

/** A section separated by a top hairline rule, with an optional title and aside. */
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
    <section className={cn("border-t border-hairline pt-5", className)}>
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

/** A small section label in sentence case (deliberately not shouty uppercase). */
export function Eyebrow({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <span className={cn("text-[0.8125rem] font-medium text-secondary first-letter:uppercase", className)}>
      {children}
    </span>
  );
}

type PillTone = "iris" | "warn" | "danger" | "neutral";

const PILL_TONES: Record<PillTone, string> = {
  iris: "border-iris/30 bg-iris-dim text-iris-fg",
  warn: "border-warn/30 bg-warn-dim text-warn-fg",
  danger: "border-danger/30 bg-danger-dim text-danger-fg",
  neutral: "border-line bg-elevated text-secondary",
};

/** A small status pill. Always pairs color with text (never color alone). */
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
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium",
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

import { cn } from "../../lib/cn";
import { fmtMetric, fmtSigned } from "../../lib/format";

interface Props {
  reported: number;
  honest: number;
  delta: number;
  variant?: "hero" | "card";
}

/** The reported→honest collapse — a static readout (no animation). */
export function CollapseViz({ reported, honest, delta, variant = "hero" }: Props) {
  const hero = variant === "hero";
  const max = Math.max(reported, honest) * 1.12 || 1;
  const pct = (v: number) => Math.max(0, (v / max) * 100);
  const share = reported !== 0 ? Math.round((delta / reported) * 100) : 0;

  const barH = hero ? "h-3.5" : "h-2";
  const num = hero ? "text-3xl" : "text-base";
  const lbl = hero ? "text-[0.8125rem]" : "text-[0.625rem]";

  const Bar = ({ label, tone, value }: { label: string; tone: "warn" | "iris"; value: number }) => (
    <div className={cn("grid items-center gap-3", hero ? "grid-cols-[4.5rem_1fr_auto]" : "grid-cols-[3.5rem_1fr_auto]")}>
      <span className={cn("font-mono", lbl, tone === "warn" ? "text-warn-fg" : "text-iris-fg")}>{label}</span>
      <div className={cn("overflow-hidden rounded-sm bg-hairline", barH)}>
        <div
          className={cn("h-full rounded-sm", tone === "warn" ? "bg-warn/70" : "bg-iris/70")}
          style={{ width: `${pct(value)}%` }}
        />
      </div>
      <span className={cn("text-right font-mono tnum", num, tone === "warn" ? "text-warn-fg" : "text-iris-fg")}>
        {fmtMetric(value)}
      </span>
    </div>
  );

  return (
    <div className={cn("flex flex-col", hero ? "gap-3" : "gap-2")}>
      <Bar label="reported" tone="warn" value={reported} />
      <Bar label="honest" tone="iris" value={honest} />
      <p className={cn("font-mono text-muted", hero ? "text-[0.8125rem]" : "text-[0.625rem]")}>
        leakage <span className="text-warn-fg">Δ {fmtSigned(delta)}</span> · {share}% of the reported
        metric
      </p>
    </div>
  );
}

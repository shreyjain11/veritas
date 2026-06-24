import type { AuditReport, TracedValue } from "../../lib/audit-report";
import { cn } from "../../lib/cn";
import { fmtCI, fmtMetric, fmtSigned, leakageShare } from "../../lib/format";
import { Eyebrow, Stat, StatusPill } from "../ui";

interface Scale {
  min: number;
  max: number;
}

function pct(v: number, s: Scale): number {
  return ((v - s.min) / (s.max - s.min)) * 100;
}

function bound(t: TracedValue, key: "ci_low" | "ci_high"): number {
  const ci = t[key];
  return ci ?? t.value ?? 0;
}

/** A reported/honest bar with its CI whisker, on the shared metric scale. */
function MetricBar({
  traced,
  scale,
  tone,
}: {
  traced: TracedValue;
  scale: Scale;
  tone: "warn" | "iris";
}) {
  const value = traced.value ?? 0;
  const zero = pct(0, scale);
  const end = pct(value, scale);
  const left = Math.min(zero, end);
  const width = Math.abs(end - zero);
  const ciL = pct(bound(traced, "ci_low"), scale);
  const ciH = pct(bound(traced, "ci_high"), scale);
  const fill = tone === "warn" ? "bg-warn/70" : "bg-iris/70";
  const cap = tone === "warn" ? "bg-warn-fg" : "bg-iris-fg";

  return (
    <div className="relative h-7">
      {/* CI band */}
      <div
        className={cn("absolute top-1/2 h-3 -translate-y-1/2 rounded-sm", tone === "warn" ? "bg-warn-dim" : "bg-iris-dim")}
        style={{ left: `${ciL}%`, width: `${Math.max(0, ciH - ciL)}%` }}
        aria-hidden
      />
      {/* bar */}
      <div
        className={cn("absolute top-1/2 h-3 -translate-y-1/2 rounded-sm", fill)}
        style={{ left: `${left}%`, width: `${width}%` }}
      />
      {/* endpoint cap */}
      <div
        className={cn("absolute top-1/2 h-3 w-0.5 -translate-y-1/2", cap)}
        style={{ left: `calc(${end}% - 1px)` }}
        aria-hidden
      />
    </div>
  );
}

export function CollapseHero({ report }: { report: AuditReport }) {
  const reported = report.reported;
  const honest = report.honest;
  const delta = report.delta;
  if (!reported || !honest || !delta) return null;

  const rv = reported.value ?? 0;
  const hv = honest.value ?? 0;
  const dv = delta.value ?? 0;
  const share = leakageShare(dv, rv);

  const lo = Math.min(0, bound(reported, "ci_low"), bound(honest, "ci_low"));
  const hi = Math.max(bound(reported, "ci_high"), bound(honest, "ci_high"), rv);
  const padPad = (hi - lo) * 0.06;
  const scale: Scale = { min: lo - padPad, max: hi + padPad };
  const zero = pct(0, scale);

  return (
    <div className="border-t border-hairline pt-5">
      <div className="mb-5 flex items-baseline justify-between gap-4">
        <Eyebrow>reported → honest</Eyebrow>
        <span className="font-mono text-[0.6875rem] text-muted tnum">{reported.name}</span>
      </div>

      <div className="mb-6 grid grid-cols-3 gap-4">
        <Stat
          label="reported"
          tone="warn"
          value={reported.status === "ok" ? fmtMetric(rv) : "—"}
          sub={fmtCI(reported.ci_low, reported.ci_high)}
        />
        <Stat
          label="honest"
          tone="iris"
          value={honest.status === "ok" ? fmtMetric(hv) : "—"}
          sub={fmtCI(honest.ci_low, honest.ci_high)}
        />
        <Stat
          label="Δ leakage"
          tone="warn"
          value={delta.status === "ok" ? fmtSigned(dv) : "—"}
          sub={fmtCI(delta.ci_low, delta.ci_high)}
        />
      </div>

      <div className="relative">
        {/* zero baseline */}
        <div
          className="pointer-events-none absolute bottom-0 top-0 w-px bg-line"
          style={{ left: `${zero}%` }}
          aria-hidden
        />
        <div className="grid grid-cols-[4.5rem_1fr] items-center gap-x-3 gap-y-1">
          <span className="font-mono text-[0.6875rem] text-warn-fg">reported</span>
          <MetricBar traced={reported} scale={scale} tone="warn" />
          <span className="font-mono text-[0.6875rem] text-iris-fg">honest</span>
          <MetricBar traced={honest} scale={scale} tone="iris" />
        </div>
      </div>

      <p className="mt-5 text-[0.8125rem] leading-relaxed text-secondary">
        {reported.status === "ok" && honest.status === "ok" ? (
          <>
            <span className="font-mono text-warn-fg tnum">{share}%</span> of the reported metric is
            leakage — it disappears once train/test homology is removed.
            {honest.ci_low != null && honest.ci_high != null && honest.ci_low <= 0 && 0 <= honest.ci_high && (
              <> The honest metric&apos;s CI includes zero: a statistical null.</>
            )}
          </>
        ) : (
          <StatusPill tone="warn">{report.status}</StatusPill>
        )}
      </p>
    </div>
  );
}

import type { CSSProperties } from "react";

import type { AuditReport } from "../../lib/audit-report";
import { fmtPct } from "../../lib/format";
import { Panel } from "../ui";

export function LeakageMeter({ report }: { report: AuditReport }) {
  const leakage = report.leakage;
  if (!leakage) return null;
  const frac =
    leakage.fraction_contaminated ??
    (leakage.n_eval ? leakage.n_contaminated / leakage.n_eval : 0);
  const detectors = Object.entries(leakage.per_detector ?? {});
  // Anchor the per-detector claim with the threshold the run used (from provenance.params).
  const params = report.provenance.params as Record<string, unknown> | undefined;
  const identity = params?.["identity_threshold"];
  const thresholdLabel = typeof identity === "number" ? `identity ≥ ${identity.toFixed(2)}` : null;

  return (
    <Panel
      eyebrow="leakage"
      aside={
        <span className="font-mono text-[0.75rem] text-secondary tnum">
          {leakage.n_contaminated}/{leakage.n_eval} eval items
        </span>
      }
    >
      <div className="flex items-baseline gap-3">
        <span className="font-mono text-2xl leading-none text-warn-fg tnum">{fmtPct(frac)}</span>
        <span className="text-[0.75rem] text-muted">contaminated by train/test homology</span>
      </div>
      <div className="mt-3 h-2 overflow-hidden rounded-sm bg-hairline">
        <div className="bar-fill h-full rounded-sm bg-warn/70" style={{ "--bar-w": `${frac * 100}%` } as CSSProperties} />
      </div>
      {detectors.length > 0 && (
        <div className="mt-4 flex flex-col gap-1.5">
          {detectors.map(([name, count]) => (
            <div key={name} className="font-mono text-[0.75rem] text-secondary tnum">
              <span className="text-fg">{name}</span> flagged{" "}
              <span className="text-warn-fg">
                {count}/{leakage.n_eval}
              </span>
              {thresholdLabel && <span className="text-muted"> · {thresholdLabel}</span>}
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

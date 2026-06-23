import type { AuditReport } from "../../lib/audit-report";
import { fmtPct } from "../../lib/format";
import { Eyebrow, Panel } from "../ui";

export function LeakageMeter({ report }: { report: AuditReport }) {
  const leakage = report.leakage;
  if (!leakage) return null;
  const frac =
    leakage.fraction_contaminated ??
    (leakage.n_eval ? leakage.n_contaminated / leakage.n_eval : 0);
  const detectors = Object.entries(leakage.per_detector ?? {});

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
        <div className="h-full rounded-sm bg-warn/70" style={{ width: `${frac * 100}%` }} />
      </div>
      {detectors.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-x-5 gap-y-1.5">
          {detectors.map(([name, count]) => (
            <span key={name} className="font-mono text-[0.75rem] text-secondary tnum">
              <span className="text-muted">{name}</span> {count}
            </span>
          ))}
        </div>
      )}
    </Panel>
  );
}

import { Info } from "lucide-react";

import type { AuditReport, DetectorCell } from "../../lib/audit-report";
import { cn } from "../../lib/cn";
import { fmtPct } from "../../lib/format";
import { Eyebrow } from "../ui";

// Leaky detectors read amber; a near-zero cell recedes to a hairline. Encoded redundantly by
// fill length + the rate number + the role label — never color-alone.
function rate(cell: DetectorCell): number {
  return cell.n_total > 0 ? cell.n_flagged / cell.n_total : 0;
}

function Cell({ cell }: { cell: DetectorCell }) {
  const r = rate(cell);
  const empty = r < 0.005;
  return (
    <div className="px-3 py-2.5">
      <div className="flex items-baseline justify-between gap-2">
        <span className={cn("font-mono text-sm tnum", empty ? "text-muted" : "text-warn-fg")}>
          {fmtPct(r)}
        </span>
        <span className="font-mono text-[0.625rem] text-faint tnum">
          {cell.n_flagged}/{cell.n_total}
        </span>
      </div>
      <div className="mt-1.5 h-1.5 overflow-hidden rounded-[2px] bg-hairline">
        {!empty && <div className="h-full rounded-[2px] bg-warn/70" style={{ width: `${r * 100}%` }} />}
      </div>
    </div>
  );
}

export function SplitsMatrix({ report }: { report: AuditReport }) {
  const splits = report.splits ?? [];
  if (splits.length === 0) return null;
  const detectors = (splits[0]?.cells ?? []).map((c) => c.detector);
  const thresholds = new Map((splits[0]?.cells ?? []).map((c) => [c.detector, c.threshold_label]));
  const cols = `minmax(10rem,1.3fr) repeat(${detectors.length}, minmax(0, 1fr))`;

  return (
    <section className="border-t border-hairline pt-5">
      <header className="mb-4 flex items-baseline justify-between gap-4">
        <Eyebrow>leakage by split × detector</Eyebrow>
        <span className="font-mono text-[0.6875rem] text-muted tnum">
          {splits.length} split{splits.length > 1 ? "s" : ""}
        </span>
      </header>

      <div className="overflow-x-auto">
        <div className="min-w-[34rem]">
          {/* column headers */}
          <div className="grid items-end gap-px border-b border-line pb-2" style={{ gridTemplateColumns: cols }}>
            <span />
            {detectors.map((d) => (
              <div key={d} className="px-3">
                <div className="flex items-center gap-1 font-mono text-[0.75rem] text-secondary">
                  {d}
                  {d === "structural" && <Info className="size-3 text-faint" aria-label="fold-level" />}
                </div>
                <div className="mt-0.5 font-mono text-[0.625rem] leading-tight text-faint">
                  {thresholds.get(d)}
                </div>
              </div>
            ))}
          </div>

          {/* rows */}
          {splits.map((split) => {
            const byDet = new Map(split.cells.map((c) => [c.detector, c]));
            return (
              <div
                key={split.split_name}
                className="grid items-stretch border-b border-hairline last:border-b-0"
                style={{ gridTemplateColumns: cols }}
              >
                <div className="px-3 py-2.5">
                  <div className="text-[0.8125rem] leading-tight text-fg">{split.split_name}</div>
                  <div className="mt-0.5 font-mono text-[0.625rem] uppercase tracking-[0.06em] text-faint">
                    {split.role}
                  </div>
                </div>
                {detectors.map((d) => {
                  const cell = byDet.get(d);
                  return cell ? <Cell key={d} cell={cell} /> : <div key={d} className="px-3 py-2.5" />;
                })}
              </div>
            );
          })}
        </div>
      </div>

      <p className="mt-3 text-[0.6875rem] leading-relaxed text-faint">
        <Info className="mr-1 inline size-3 align-[-1px]" aria-hidden />
        structural is fold-level (foldseek monomer TMalign) — a related but more permissive signal
        than iDist&apos;s interface-level redundancy; reported as its own quantity, not directly
        comparable. A near-zero row — like the published control — recedes to hairline; amber cells
        mark a leaky split.
      </p>
    </section>
  );
}

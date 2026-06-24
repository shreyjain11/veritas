import Link from "next/link";
import type { ReactNode } from "react";

import type { AuditReport } from "../../lib/audit-report";
import { cn } from "../../lib/cn";
import { FIXTURES } from "../../lib/fixtures";
import { fmtMetric, fmtPct } from "../../lib/format";
import { Eyebrow } from "../ui";
import { CollapseViz } from "./CollapseViz";

const byId = (id: string) => FIXTURES.find((f) => f.id === id)!;

const KIND_LABEL: Record<string, string> = {
  metric_audit: "metric audit",
  detection: "detection",
  stratification: "stratification",
};

function ResultCard({ id, featured, children }: { id: string; featured?: boolean; children: ReactNode }) {
  const fx = byId(id);
  return (
    <Link
      href={`/report?report=${id}`}
      className={cn(
        "group flex flex-col border-t border-hairline pt-5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-iris",
        featured && "sm:col-span-2",
      )}
    >
      <div className="flex items-baseline justify-between gap-3">
        <h3 className="text-[0.9375rem] text-fg transition-colors group-hover:text-iris-fg">{fx.label}</h3>
        <span className="font-mono text-[0.625rem] uppercase tracking-[0.06em] text-faint">
          {KIND_LABEL[fx.report.report_kind ?? "metric_audit"]}
        </span>
      </div>
      <div className="mt-4">{children}</div>
      <p className="mt-4 text-pretty text-[0.8125rem] leading-relaxed text-secondary">{fx.finding}</p>
      <span className="mt-3 font-mono text-[0.75rem] text-iris-fg transition-transform group-hover:translate-x-0.5">
        Open audit →
      </span>
    </Link>
  );
}

function collapse(report: AuditReport) {
  return {
    reported: report.reported?.value ?? 0,
    honest: report.honest?.value ?? 0,
    delta: report.delta?.value ?? 0,
  };
}

function Meter({ report }: { report: AuditReport }) {
  const cell = report.splits?.[0]?.cells?.[0];
  const rate = cell && cell.n_total ? cell.n_flagged / cell.n_total : 0;
  return (
    <div>
      <div className="flex items-baseline gap-2">
        <span className="font-mono text-2xl text-warn-fg tnum">{fmtPct(rate)}</span>
        <span className="text-[0.6875rem] text-muted">reverse-complement</span>
      </div>
      <div className="mt-2 h-2 overflow-hidden rounded-sm bg-hairline">
        <div className="h-full rounded-sm bg-warn/70" style={{ width: `${rate * 100}%` }} />
      </div>
    </div>
  );
}

function Gradient({ report }: { report: AuditReport }) {
  const strata = [...(report.stratification ?? [])].sort((a, b) => a.bucket_index - b.bucket_index);
  const max = Math.max(...strata.map((s) => s.metric.value ?? 0), 0.001);
  return (
    <div className="flex h-24 items-end gap-3">
      {strata.map((s) => (
        <div key={s.bucket_index} className="flex flex-1 flex-col items-center gap-1.5">
          <span className="font-mono text-[0.75rem] text-iris-fg tnum">{fmtMetric(s.metric.value)}</span>
          <div className="w-full rounded-sm bg-iris/55" style={{ height: `${((s.metric.value ?? 0) / max) * 70}px` }} />
          <span className="font-mono text-[0.625rem] text-muted">{s.bucket_label}</span>
        </div>
      ))}
    </div>
  );
}

function MiniMatrix({ report }: { report: AuditReport }) {
  const splits = report.splits ?? [];
  return (
    <div className="flex flex-col gap-1">
      {splits.map((s) => (
        <div key={s.split_name} className="flex items-center gap-2">
          <span className="w-24 shrink-0 truncate font-mono text-[0.625rem] text-muted">
            {s.split_name.split(" (")[0]}
          </span>
          <div className="flex flex-1 gap-1">
            {s.cells.map((c) => {
              const r = c.n_total ? c.n_flagged / c.n_total : 0;
              return (
                <div
                  key={c.detector}
                  className="h-4 flex-1 rounded-[2px]"
                  title={`${c.detector} ${fmtPct(r)}`}
                  style={{
                    backgroundColor: r < 0.005 ? "#1c222a" : `rgba(224,165,59,${(0.3 + r * 0.55).toFixed(2)})`,
                  }}
                />
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

export function Proof() {
  return (
    <section className="mx-auto max-w-[1100px] px-5 py-14 sm:px-8">
      <Eyebrow>five real audits · no fabricated numbers</Eyebrow>
      <div className="mt-8 grid gap-x-10 gap-y-7 sm:grid-cols-2">
        <ResultCard id="r3_random" featured>
          <CollapseViz {...collapse(byId("r3_random").report)} variant="card" />
        </ResultCard>
        <ResultCard id="r3_chr8_chr9">
          <CollapseViz {...collapse(byId("r3_chr8_chr9").report)} variant="card" />
        </ResultCard>
        <ResultCard id="r2_reverse_complement">
          <Meter report={byId("r2_reverse_complement").report} />
        </ResultCard>
        <ResultCard id="proteingym_msa_depth">
          <Gradient report={byId("proteingym_msa_depth").report} />
        </ResultCard>
        <ResultCard id="ppi_interface">
          <MiniMatrix report={byId("ppi_interface").report} />
        </ResultCard>
      </div>
    </section>
  );
}

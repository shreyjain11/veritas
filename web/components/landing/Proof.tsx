import Link from "next/link";
import type { CSSProperties, ReactNode } from "react";

import type { AuditReport } from "../../lib/audit-report";
import { cn } from "../../lib/cn";
import { FIXTURES } from "../../lib/fixtures";
import { fmtMetric, fmtPct } from "../../lib/format";
import { Reveal } from "../Reveal";
import { Eyebrow } from "../ui";
import { CollapseViz } from "./CollapseViz";

const byId = (id: string) => FIXTURES.find((f) => f.id === id)!;

const KIND_LABEL: Record<string, string> = {
  metric_audit: "metric audit",
  detection: "detection",
  stratification: "stratification",
};

function ResultCard({ id, delay = 0, children }: { id: string; delay?: number; children: ReactNode }) {
  const fx = byId(id);
  return (
    <Reveal delay={delay}>
      <Link
        href={`/report?report=${id}`}
        className="group flex flex-col border-t border-hairline pt-5 transition-transform duration-300 ease-out hover:-translate-y-1 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-iris"
      >
        <div className="flex items-baseline justify-between gap-3">
          <h3 className="text-[0.9375rem] text-fg transition-colors group-hover:text-iris-fg">{fx.label}</h3>
          <span className="font-mono text-[0.625rem] uppercase tracking-[0.06em] text-faint">
            {KIND_LABEL[fx.report.report_kind ?? "metric_audit"]}
          </span>
        </div>
        <div className="mt-4">{children}</div>
        <p className="mt-4 text-pretty text-[0.8125rem] leading-relaxed text-secondary">{fx.finding}</p>
        <span className="mt-3 font-mono text-[0.75rem] text-iris-fg transition-transform group-hover:translate-x-1">
          Open audit →
        </span>
      </Link>
    </Reveal>
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
        <div className="bar-fill h-full rounded-sm bg-warn/70" style={{ "--bar-w": `${rate * 100}%` } as CSSProperties} />
      </div>
    </div>
  );
}

function Gradient({ report }: { report: AuditReport }) {
  const strata = [...(report.stratification ?? [])].sort((a, b) => a.bucket_index - b.bucket_index);
  const max = Math.max(...strata.map((s) => s.metric.value ?? 0), 0.001);
  return (
    <div className="flex h-24 items-end gap-3">
      {strata.map((s, i) => (
        <div key={s.bucket_index} className="flex flex-1 flex-col items-center gap-1.5">
          <span className="font-mono text-[0.75rem] text-iris-fg tnum">{fmtMetric(s.metric.value)}</span>
          <div
            className="w-full origin-bottom rounded-sm bg-iris/55"
            style={{
              height: `${((s.metric.value ?? 0) / max) * 70}px`,
              animation: `pop 480ms ${80 + i * 70}ms cubic-bezier(0.16,1,0.3,1) both`,
            }}
          />
          <span className="font-mono text-[0.625rem] text-muted">{s.bucket_label}</span>
        </div>
      ))}
    </div>
  );
}

// A row is "clean" when even its worst detector is near-zero — same threshold the full
// viewer matrix uses. Clean rows recede (uniform dim cells + iris edge); leaky rows read hot
// amber. The Pr/PI published control is the clean row; the immune holdouts read leaky.
const CLEAN_MAX_RATE = 0.05;

function MiniMatrix({ report }: { report: AuditReport }) {
  const splits = report.splits ?? [];
  return (
    <div className="flex flex-col gap-1">
      {splits.map((s) => {
        const rowMax = s.cells.reduce((m, c) => Math.max(m, c.n_total ? c.n_flagged / c.n_total : 0), 0);
        const clean = rowMax < CLEAN_MAX_RATE;
        return (
          <div
            key={s.split_name}
            className="flex items-center gap-2"
          >
            <span
              className={cn(
                "w-24 shrink-0 truncate font-mono text-[0.625rem]",
                clean ? "text-iris-fg" : "text-muted",
              )}
            >
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
                      backgroundColor: clean
                        ? "#161a21"
                        : r < 0.005
                          ? "#1c222a"
                          : `rgba(224,165,59,${(0.35 + r * 0.5).toFixed(2)})`,
                    }}
                  />
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function Proof() {
  return (
    <section className="mx-auto max-w-[1100px] px-5 py-16 sm:px-8 sm:py-20">
      <Eyebrow>four more audits · across model types</Eyebrow>
      <p className="mt-3 max-w-2xl text-pretty text-[0.9375rem] leading-relaxed text-secondary">
        Each is a real run on pinned data, locked by a test — spanning genomic, variant-effect, and
        protein-interaction models, and all three detector kinds. Nothing is fabricated.
      </p>
      <div className="mt-10 grid gap-x-12 gap-y-10 sm:grid-cols-2">
        <ResultCard id="r3_chr8_chr9" delay={0}>
          <CollapseViz {...collapse(byId("r3_chr8_chr9").report)} variant="card" />
        </ResultCard>
        <ResultCard id="r2_reverse_complement" delay={80}>
          <Meter report={byId("r2_reverse_complement").report} />
        </ResultCard>
        <ResultCard id="proteingym_msa_depth" delay={0}>
          <Gradient report={byId("proteingym_msa_depth").report} />
        </ResultCard>
        <ResultCard id="ppi_interface" delay={80}>
          <MiniMatrix report={byId("ppi_interface").report} />
        </ResultCard>
      </div>
    </section>
  );
}

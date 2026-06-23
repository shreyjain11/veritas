"use client";

import { FileUp, X } from "lucide-react";
import { useState } from "react";

import type { AuditReport } from "../../lib/audit-report";
import { cn } from "../../lib/cn";
import { FIXTURES } from "../../lib/fixtures";
import { StatusPill } from "../ui";
import { CollapseHero } from "./CollapseHero";
import { HashSeal } from "./HashSeal";
import { LeakageMeter } from "./LeakageMeter";
import { Limitations } from "./Limitations";
import { ProvenanceReadout } from "./ProvenanceReadout";
import { SplitsMatrix } from "./SplitsMatrix";
import { StratificationCurve } from "./StratificationCurve";

interface Active {
  report: AuditReport;
  label: string;
  id: string;
}

const KIND_LABEL: Record<string, string> = {
  metric_audit: "metric audit",
  detection: "detection",
  stratification: "stratification",
};

function looksLikeReport(value: unknown): value is AuditReport {
  return (
    typeof value === "object" &&
    value !== null &&
    "audit_hash" in value &&
    "report_kind" in value &&
    "benchmark_name" in value
  );
}

export function Viewer() {
  const first = FIXTURES[0]!;
  const [active, setActive] = useState<Active>({ report: first.report, label: first.label, id: first.id });
  const [pasteOpen, setPasteOpen] = useState(false);
  const [pasteText, setPasteText] = useState("");
  const [error, setError] = useState<string | null>(null);

  function ingest(raw: string, label: string) {
    try {
      const parsed: unknown = JSON.parse(raw);
      if (!looksLikeReport(parsed)) {
        setError("Not an AuditReport — missing audit_hash / report_kind / benchmark_name.");
        return;
      }
      setActive({ report: parsed, label, id: `custom:${label}` });
      setError(null);
      setPasteOpen(false);
      setPasteText("");
    } catch {
      setError("Could not parse JSON.");
    }
  }

  const { report } = active;
  const kind = report.report_kind ?? "metric_audit";

  return (
    <div className="mx-auto grid min-h-screen max-w-[1240px] grid-cols-1 lg:grid-cols-[290px_1fr]">
      <aside className="border-b border-line px-5 py-6 lg:sticky lg:top-0 lg:h-screen lg:overflow-y-auto lg:border-b-0 lg:border-r">
        <div className="mb-5">
          <h1 className="font-mono text-sm font-semibold tracking-tight text-fg">veritas</h1>
          <p className="mt-1 text-[0.75rem] leading-snug text-muted">
            leakage &amp; robustness audit viewer
          </p>
        </div>

        <HashSeal report={report} />

        <nav className="mt-6">
          <p className="mb-2 text-[0.6875rem] font-medium uppercase tracking-[0.08em] text-faint">
            specimens
          </p>
          <ul className="flex flex-col gap-0.5">
            {FIXTURES.map((f) => {
              const selected = active.id === f.id;
              return (
                <li key={f.id}>
                  <button
                    type="button"
                    onClick={() => {
                      setActive({ report: f.report, label: f.label, id: f.id });
                      setError(null);
                    }}
                    className={cn(
                      "w-full rounded-md border-l-2 px-3 py-2 text-left transition-colors",
                      selected
                        ? "border-l-iris bg-iris-dim/50"
                        : "border-l-transparent hover:bg-elevated/60",
                    )}
                  >
                    <span className={cn("block text-[0.8125rem]", selected ? "text-iris-fg" : "text-fg")}>
                      {f.label}
                    </span>
                    <span className="mt-0.5 block text-[0.6875rem] leading-snug text-muted">{f.blurb}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>

        <div className="mt-6 border-t border-hairline pt-4">
          <label className="flex cursor-pointer items-center gap-2 text-[0.75rem] text-secondary transition-colors hover:text-fg">
            <FileUp className="size-3.5" aria-hidden />
            <span>Load a report…</span>
            <input
              type="file"
              accept="application/json,.json"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                file.text().then((text) => ingest(text, file.name));
              }}
            />
          </label>
          <button
            type="button"
            onClick={() => setPasteOpen((v) => !v)}
            className="mt-2 text-[0.75rem] text-secondary transition-colors hover:text-fg"
          >
            {pasteOpen ? "Cancel paste" : "Paste JSON…"}
          </button>
          {pasteOpen && (
            <div className="mt-2">
              <textarea
                value={pasteText}
                onChange={(e) => setPasteText(e.target.value)}
                rows={4}
                placeholder="{ …AuditReport JSON… }"
                className="w-full rounded-md border border-line bg-base px-2 py-1.5 font-mono text-[0.6875rem] text-fg outline-none focus:border-iris/60"
              />
              <button
                type="button"
                onClick={() => ingest(pasteText, "pasted report")}
                className="mt-1.5 rounded-md border border-iris/40 bg-iris-dim px-2.5 py-1 text-[0.75rem] text-iris-fg transition-colors hover:border-iris/70"
              >
                Render
              </button>
            </div>
          )}
          {error && (
            <p className="mt-2 flex items-start gap-1.5 text-[0.6875rem] leading-snug text-danger-fg">
              <X className="mt-0.5 size-3 shrink-0" aria-hidden />
              {error}
            </p>
          )}
        </div>
      </aside>

      <main className="min-w-0 px-5 py-6 lg:px-8 lg:py-8">
        <header className="mb-6 flex flex-wrap items-center gap-3">
          <h2 className="font-mono text-lg text-fg">{report.benchmark_name}</h2>
          <StatusPill tone="neutral">{KIND_LABEL[kind] ?? kind}</StatusPill>
          {report.status && report.status !== "ok" && (
            <StatusPill tone="warn">{report.status}</StatusPill>
          )}
        </header>

        <div className="flex flex-col gap-5">
          {kind === "metric_audit" && (
            <>
              <CollapseHero report={report} />
              <LeakageMeter report={report} />
              <StratificationCurve report={report} />
            </>
          )}
          {kind === "detection" && <SplitsMatrix report={report} />}
          {kind === "stratification" && <StratificationCurve report={report} />}
          <ProvenanceReadout report={report} />
          <Limitations report={report} />
        </div>
      </main>
    </div>
  );
}

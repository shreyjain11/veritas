"use client";

import { FileUp, TriangleAlert, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import type { AuditReport } from "../../lib/audit-report";
import { cn } from "../../lib/cn";
import { FIXTURES } from "../../lib/fixtures";
import { useVerify } from "../../lib/useVerify";
import { ErrorBoundary } from "../ErrorBoundary";
import { Footer } from "../Footer";
import { StatusPill } from "../ui";
import { CollapseHero } from "./CollapseHero";
import { HashSeal, HashSealChip } from "./HashSeal";
import { LeakageMeter } from "./LeakageMeter";
import { Limitations } from "./Limitations";
import { ProvenanceReadout } from "./ProvenanceReadout";
import { SplitsMatrix } from "./SplitsMatrix";
import { StratificationCurve } from "./StratificationCurve";
import { TamperBanner } from "./TamperBanner";

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

const FOCUS = "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-iris";

export function Viewer() {
  const first = FIXTURES[0]!;
  const [active, setActive] = useState<Active>({ report: first.report, label: first.label, id: first.id });
  const [pasteOpen, setPasteOpen] = useState(false);
  const [pasteText, setPasteText] = useState("");
  const [error, setError] = useState<string | null>(null);

  const verify = useVerify(active.report);

  // Deep-link: /report?report=<specimen-id> selects that fixture on load (used by the
  // landing's result cards). Runs once on mount; unknown ids fall back to the default.
  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get("report");
    if (!id) return;
    const fx = FIXTURES.find((f) => f.id === id);
    if (fx) setActive({ report: fx.report, label: fx.label, id: fx.id });
  }, []);

  async function ingest(raw: string, label: string) {
    let parsed: unknown;
    try {
      parsed = JSON.parse(raw);
    } catch {
      setError("Could not parse JSON.");
      return;
    }
    const { validateReport } = await import("../../lib/validate");
    const result = validateReport(parsed);
    if (!result.ok) {
      setError(`Not a valid AuditReport — ${result.errors.join("; ")}`);
      return;
    }
    setActive({
      report: result.report,
      label,
      id: `custom:${result.report.audit_hash.slice(0, 10)}`,
    });
    setError(null);
    setPasteOpen(false);
    setPasteText("");
  }

  function selectFixture(id: string) {
    const fx = FIXTURES.find((f) => f.id === id);
    if (fx) {
      setActive({ report: fx.report, label: fx.label, id: fx.id });
      setError(null);
    }
  }

  const isCustom = !FIXTURES.some((f) => f.id === active.id);
  const ingestion = (
    <Ingestion
      pasteOpen={pasteOpen}
      setPasteOpen={setPasteOpen}
      pasteText={pasteText}
      setPasteText={setPasteText}
      error={error}
      ingest={ingest}
    />
  );

  return (
    <div className="mx-auto max-w-[1240px]">
      {/* Mobile bar */}
      <div className="sticky top-0 z-10 border-b border-line bg-base/90 px-4 py-3 backdrop-blur lg:hidden">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="rounded-sm font-mono text-sm font-semibold text-fg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-iris"
          >
            veritas
          </Link>
          <HashSealChip state={verify} />
          <label className="ml-auto flex items-center gap-1.5 text-[0.75rem] text-secondary">
            <span className="sr-only">Choose a specimen</span>
            <select
              value={isCustom ? "custom" : active.id}
              onChange={(e) => selectFixture(e.target.value)}
              className={cn("rounded-md border border-line bg-elevated px-2 py-1 font-mono text-[0.75rem] text-fg", FOCUS)}
            >
              {FIXTURES.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.label}
                </option>
              ))}
              {isCustom && <option value="custom">{active.label}</option>}
            </select>
          </label>
        </div>
        <div className="mt-3">{ingestion}</div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[290px_1fr]">
        {/* Desktop rail */}
        <aside className="hidden px-5 py-6 lg:sticky lg:top-0 lg:block lg:h-dvh lg:overflow-y-auto lg:border-r lg:border-line">
          <div className="mb-5">
            <Link
              href="/"
              className="group inline-flex items-center gap-1.5 rounded-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-iris"
            >
              <span className="font-mono text-sm font-semibold tracking-tight text-fg">veritas</span>
              <span className="text-[0.6875rem] text-faint transition-colors group-hover:text-muted">
                ↗ overview
              </span>
            </Link>
            <p className="mt-1 text-[0.75rem] leading-snug text-muted">leakage &amp; robustness audit viewer</p>
          </div>

          <HashSeal auditHash={active.report.audit_hash} state={verify} />

          <nav className="mt-6">
            <p className="mb-2 text-[0.6875rem] font-medium uppercase tracking-[0.08em] text-faint">specimens</p>
            <ul className="flex flex-col gap-0.5">
              {FIXTURES.map((f) => {
                const selected = active.id === f.id;
                return (
                  <li key={f.id}>
                    <button
                      type="button"
                      onClick={() => selectFixture(f.id)}
                      aria-current={selected ? "true" : undefined}
                      className={cn(
                        "w-full rounded-md px-3 py-2 text-left transition-colors",
                        FOCUS,
                        selected ? "bg-iris-dim/50" : "hover:bg-elevated/60",
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

          <div className="mt-6 border-t border-hairline pt-4">{ingestion}</div>
        </aside>

        {/* Main */}
        <main className="min-w-0 px-4 py-6 lg:px-8 lg:py-8">
          <header className="mb-6 flex flex-wrap items-center gap-3">
            <h2 className="font-mono text-lg text-fg">{active.report.benchmark_name}</h2>
            <StatusPill tone="neutral">
              {KIND_LABEL[active.report.report_kind ?? "metric_audit"] ?? active.report.report_kind}
            </StatusPill>
            {active.report.status && active.report.status !== "ok" && (
              <StatusPill tone="warn">{active.report.status}</StatusPill>
            )}
          </header>

          {verify.status === "mismatch" && (
            <div className="mb-5">
              <TamperBanner auditHash={active.report.audit_hash} result={verify.result} />
            </div>
          )}

          <ErrorBoundary
            key={active.id}
            fallback={(err) => (
              <div className="rounded-md border border-danger/40 bg-danger-dim px-5 py-4">
                <div className="flex items-center gap-2 text-danger-fg">
                  <TriangleAlert className="size-4" aria-hidden />
                  <h3 className="text-[0.875rem] font-medium">This report couldn&apos;t be rendered</h3>
                </div>
                <p className="mt-2 font-mono text-[0.75rem] leading-relaxed text-secondary">{err.message}</p>
                <p className="mt-2 text-[0.8125rem] text-muted">
                  Pick a specimen from the list, or load a report that matches the AuditReport schema.
                </p>
              </div>
            )}
          >
            <ReportPanels report={active.report} />
          </ErrorBoundary>

          <Footer />
        </main>
      </div>
    </div>
  );
}

function ReportPanels({ report }: { report: AuditReport }) {
  const kind = report.report_kind ?? "metric_audit";
  return (
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
  );
}

function Ingestion({
  pasteOpen,
  setPasteOpen,
  pasteText,
  setPasteText,
  error,
  ingest,
}: {
  pasteOpen: boolean;
  setPasteOpen: (v: boolean) => void;
  pasteText: string;
  setPasteText: (v: string) => void;
  error: string | null;
  ingest: (raw: string, label: string) => void;
}) {
  return (
    <div>
      <div className="flex flex-wrap items-center gap-4">
        <label className={cn("flex cursor-pointer items-center gap-2 rounded-sm text-[0.75rem] text-secondary transition-colors hover:text-fg", FOCUS)}>
          <FileUp className="size-3.5" aria-hidden />
          <span>Load a report…</span>
          <input
            type="file"
            accept="application/json,.json"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) file.text().then((text) => ingest(text, file.name));
            }}
          />
        </label>
        <button
          type="button"
          onClick={() => setPasteOpen(!pasteOpen)}
          className={cn("rounded-sm text-[0.75rem] text-secondary transition-colors hover:text-fg", FOCUS)}
        >
          {pasteOpen ? "Cancel paste" : "Paste JSON…"}
        </button>
      </div>
      {pasteOpen && (
        <div className="mt-2">
          <textarea
            value={pasteText}
            onChange={(e) => setPasteText(e.target.value)}
            rows={4}
            placeholder="{ …AuditReport JSON… }"
            aria-label="Paste AuditReport JSON"
            className={cn("w-full rounded-md border border-line bg-base px-2 py-1.5 font-mono text-[0.6875rem] text-fg outline-none focus:border-iris/60", FOCUS)}
          />
          <button
            type="button"
            onClick={() => ingest(pasteText, "pasted report")}
            className={cn("mt-1.5 rounded-md border border-iris/40 bg-iris-dim px-2.5 py-1 text-[0.75rem] text-iris-fg transition-colors hover:border-iris/70", FOCUS)}
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
  );
}

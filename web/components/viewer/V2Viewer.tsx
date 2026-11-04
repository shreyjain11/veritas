"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { parseV2Report, type V2Report } from "../../lib/v2-report";
import { buttonClass } from "../ui";
import { ReportView } from "./ReportView";

const MAX_BYTES = 64 * 1024 * 1024;

export function V2Viewer() {
  const [report, setReport] = useState<V2Report | null>(null);
  const [source, setSource] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const accept = useCallback((data: unknown, name: string) => {
    try {
      setReport(parseV2Report(data));
      setSource(name);
      setError(null);
      window.scrollTo({ top: 0 });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not read the report.");
    }
  }, []);

  const loadFile = useCallback(
    async (file: File) => {
      if (file.size > MAX_BYTES) {
        setError(`${file.name} is ${(file.size / 1e6).toFixed(0)} MB; the viewer opens reports up to 64 MB.`);
        return;
      }
      setLoading(true);
      try {
        accept(JSON.parse(await file.text()), file.name);
      } catch {
        setError(`${file.name} is not valid JSON. Open the report.json written by \`veritas audit\` or downloaded from the run page.`);
      } finally {
        setLoading(false);
      }
    },
    [accept],
  );

  const loadSample = useCallback(async () => {
    setLoading(true);
    try {
      const sample = await import("../../fixtures/v2/sample_report.json");
      accept(sample.default, "sample report");
    } finally {
      setLoading(false);
    }
  }, [accept]);

  useEffect(() => {
    if (new URLSearchParams(window.location.search).has("sample")) void loadSample();
  }, [loadSample]);

  return (
    <main
      className="mx-auto max-w-[1120px] px-5 py-10 sm:px-8"
      onDragOver={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={(event) => {
        if (event.currentTarget === event.target) setDragging(false);
      }}
      onDrop={(event) => {
        event.preventDefault();
        setDragging(false);
        const file = event.dataTransfer.files[0];
        if (file) void loadFile(file);
      }}
    >
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-hairline pb-5">
        <p className="min-w-0 truncate text-sm text-muted">
          {source ? <>Viewing <span className="font-medium text-fg">{source}</span></> : "Report viewer"}
        </p>
        <div className="flex flex-wrap items-center gap-2">
          {report && (
            <button type="button" onClick={() => void loadSample()} className={buttonClass("ghost")}>
              Sample
            </button>
          )}
          <button type="button" onClick={() => inputRef.current?.click()} className={buttonClass(report ? "secondary" : "primary")}>
            {report ? "Open another" : "Open report.json"}
          </button>
          <input
            ref={inputRef}
            className="sr-only"
            type="file"
            accept="application/json,.json"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void loadFile(file);
              event.target.value = "";
            }}
          />
        </div>
      </header>

      {error && (
        <p role="alert" className="mt-5 rounded-md border border-danger/40 bg-danger-dim p-4 text-sm text-danger-fg">
          {error}
          {error.includes("legacy") && (
            <Link href="/report/legacy" className="ml-2 underline underline-offset-4">Open the legacy viewer →</Link>
          )}
        </p>
      )}
      {loading && <p className="mt-5 text-sm text-muted" aria-live="polite">Loading…</p>}

      {report ? (
        <div className="py-8">
          <ReportView report={report} />
        </div>
      ) : (
        <EmptyState dragging={dragging} choose={() => inputRef.current?.click()} sample={() => void loadSample()} />
      )}
    </main>
  );
}

function EmptyState({ dragging, choose, sample }: { dragging: boolean; choose: () => void; sample: () => void }) {
  return (
    <section className="py-14">
      <h1 className="font-display text-[2.5rem] leading-tight font-medium tracking-[-0.015em] text-fg">Open an audit report</h1>
      <p className="mt-3 max-w-2xl text-secondary">
        Inspect scores, verdicts, and every prompt, response, and variant. Reports are read locally in
        your browser and never uploaded; the audit hash is re-verified on open.
      </p>
      <div
        className={`mt-8 grid place-items-center rounded-xl border-2 border-dashed px-6 py-14 text-center transition-colors ${dragging ? "border-iris bg-iris-dim/40" : "border-line bg-surface"}`}
      >
        <p className="text-fg">Drop a <span className="font-mono">report.json</span> here</p>
        <p className="mt-1 text-sm text-muted">from <span className="font-mono">veritas audit</span> or a browser run</p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <button type="button" onClick={choose} className={buttonClass("primary")}>
            Choose a file
          </button>
          <button type="button" onClick={sample} className={buttonClass("secondary")}>
            Explore the sample report
          </button>
        </div>
      </div>
      <div className="mt-6 flex flex-wrap gap-x-6 gap-y-2 text-sm">
        <Link className="font-medium text-iris-fg underline-offset-4 hover:underline" href="/run">Run a new audit →</Link>
        <Link className="text-secondary underline-offset-4 hover:text-fg hover:underline" href="/report/legacy">Legacy biological reports →</Link>
      </div>
    </section>
  );
}

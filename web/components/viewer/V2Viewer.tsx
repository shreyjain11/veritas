"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { parseV2Report, type V2Report } from "../../lib/v2-report";
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
      className="mx-auto max-w-[1240px] px-5 py-10 sm:px-8"
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
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-hairline pb-6">
        <div>
          <p className="font-mono text-[0.6875rem] uppercase tracking-[0.08em] text-muted">report viewer · schema v2</p>
          {source && <p className="mt-1 break-all font-mono text-xs text-secondary">{source}</p>}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {report && (
            <button type="button" onClick={() => void loadSample()} className="rounded-md px-3 py-2 text-sm text-secondary hover:text-fg">
              Sample
            </button>
          )}
          <button type="button" onClick={() => inputRef.current?.click()} className="rounded-md border border-iris/40 bg-iris-dim px-4 py-2 font-mono text-sm text-iris-fg transition-colors hover:border-iris/70">
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
      <h1 className="text-3xl font-semibold tracking-tight text-fg">Open a benchmark-integrity audit.</h1>
      <p className="mt-3 max-w-2xl text-secondary">
        Inspect scores, verdicts, and every prompt, response, and variant. Reports are read locally in
        your browser and never uploaded; the audit hash is re-verified on open.
      </p>
      <div
        className={`mt-8 grid place-items-center rounded-xl border-2 border-dashed px-6 py-14 text-center transition-colors ${dragging ? "border-iris bg-iris-dim/30" : "border-line"}`}
      >
        <p className="text-fg">Drop a <span className="font-mono">report.json</span> here</p>
        <p className="mt-1 text-sm text-muted">from <span className="font-mono">veritas audit</span> or a browser run</p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <button type="button" onClick={choose} className="rounded-md border border-iris/40 bg-iris-dim px-4 py-2 font-mono text-sm text-iris-fg hover:border-iris/70">
            Choose a file
          </button>
          <button type="button" onClick={sample} className="rounded-md border border-line px-4 py-2 text-sm text-secondary hover:border-edge hover:text-fg">
            Explore the sample report
          </button>
        </div>
      </div>
      <div className="mt-6 flex flex-wrap gap-x-6 gap-y-2 text-sm">
        <Link className="text-iris-fg underline-offset-4 hover:underline" href="/run">Run a new audit →</Link>
        <Link className="text-secondary underline-offset-4 hover:text-fg hover:underline" href="/report/legacy">Legacy biological reports →</Link>
      </div>
    </section>
  );
}

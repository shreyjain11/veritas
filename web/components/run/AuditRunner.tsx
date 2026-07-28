"use client";

import Link from "next/link";
import { useRef, useState } from "react";

import {
  BROWSER_BENCHMARKS,
  BROWSER_PROVIDERS,
  type BrowserAuditReport,
  type BrowserBenchmarkId,
  type BrowserProviderId,
  MAX_BROWSER_ITEMS,
  requestCount,
} from "../../lib/browser-audit";

const CONTROL =
  "w-full rounded-md border border-line bg-base px-3 py-2.5 text-sm text-fg outline-none transition-colors placeholder:text-faint focus:border-iris/70";

function pct(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

export function AuditRunner() {
  const [provider, setProvider] = useState<BrowserProviderId>("together");
  const [benchmark, setBenchmark] = useState<BrowserBenchmarkId>("mmlu");
  const [model, setModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [itemCount, setItemCount] = useState(10);
  const [offset, setOffset] = useState(0);
  const [acknowledged, setAcknowledged] = useState(false);
  const [status, setStatus] = useState<"idle" | "running" | "complete" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<BrowserAuditReport | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const requests = requestCount(itemCount);
  const selectedProvider = BROWSER_PROVIDERS.find((entry) => entry.id === provider);
  const selectedBenchmark = BROWSER_BENCHMARKS.find((entry) => entry.id === benchmark);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus("running");
    setError(null);
    setReport(null);
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const response = await fetch("/api/audits", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        cache: "no-store",
        signal: controller.signal,
        body: JSON.stringify({
          provider,
          benchmark,
          model,
          apiKey,
          itemCount,
          offset,
          acknowledgeExternalTransfer: acknowledged,
        }),
      });
      const body = (await response.json()) as BrowserAuditReport | { error?: string };
      if (!response.ok || !("schema_version" in body)) {
        throw new Error("error" in body && body.error ? body.error : "The audit did not complete.");
      }
      setReport(body);
      setStatus("complete");
    } catch (cause) {
      if (cause instanceof DOMException && cause.name === "AbortError") {
        setError("Audit cancelled. Your provider key was cleared.");
      } else {
        setError(cause instanceof Error ? cause.message : "The audit did not complete.");
      }
      setStatus("error");
    } finally {
      setApiKey("");
      abortRef.current = null;
    }
  }

  function cancel() {
    abortRef.current?.abort();
  }

  function download() {
    if (!report) return;
    const url = URL.createObjectURL(
      new Blob([`${JSON.stringify(report, null, 2)}\n`], { type: "application/json" }),
    );
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `veritas-${report.benchmark.id}-${report.audit_hash.slice(0, 10)}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main className="mx-auto max-w-[1180px] px-5 py-10 sm:px-8 sm:py-14">
      <header className="grid gap-8 border-b border-hairline pb-10 lg:grid-cols-[1fr_360px] lg:items-end">
        <div>
          <Link href="/" className="font-mono text-sm text-iris-fg">
            veritas
          </Link>
          <p className="mt-5 font-mono text-[0.6875rem] uppercase tracking-[0.08em] text-muted">
            browser audit console · BYOK
          </p>
          <h1 className="mt-3 max-w-3xl text-balance text-3xl font-semibold tracking-tight text-fg sm:text-4xl">
            Run a benchmark-integrity audit from the browser.
          </h1>
          <p className="mt-4 max-w-2xl text-pretty text-[0.9375rem] leading-relaxed text-secondary">
            Choose a benchmark and provider. Veritas sends controlled prompt variants to your
            model, computes paired robustness evidence, and returns a downloadable schema-v2 report.
          </p>
        </div>
        <div className="rounded-lg border border-iris/25 bg-iris-dim/30 p-4">
          <p className="font-mono text-xs text-iris-fg">Your key stays ephemeral</p>
          <p className="mt-2 text-xs leading-relaxed text-secondary">
            It is sent once over HTTPS, used in server memory for this audit, cleared from the form,
            and never stored in the report, cache, logs, cookies, or browser storage by Veritas.
          </p>
        </div>
      </header>

      <div className="grid gap-8 py-10 lg:grid-cols-[minmax(0,1fr)_340px]">
        <form onSubmit={submit} className="rounded-xl border border-line bg-surface/20 p-5 sm:p-7">
          <div className="flex items-center justify-between gap-4 border-b border-hairline pb-5">
            <div>
              <p className="font-mono text-xs text-iris-fg">01 / configure</p>
              <h2 className="mt-1 text-lg text-fg">Model connection</h2>
            </div>
            <span className="rounded-full border border-line px-2.5 py-1 font-mono text-[0.625rem] text-muted">
              OpenAI-compatible
            </span>
          </div>

          <div className="mt-6 grid gap-5 sm:grid-cols-2">
            <label className="block">
              <span className="mb-2 block text-xs text-secondary">Provider</span>
              <select value={provider} onChange={(event) => setProvider(event.target.value as BrowserProviderId)} className={CONTROL} disabled={status === "running"}>
                {BROWSER_PROVIDERS.map((entry) => (
                  <option key={entry.id} value={entry.id}>{entry.name}</option>
                ))}
              </select>
              <span className="mt-1.5 block text-[0.6875rem] text-muted">{selectedProvider?.description}</span>
            </label>
            <label className="block">
              <span className="mb-2 block text-xs text-secondary">Provider model ID</span>
              <input value={model} onChange={(event) => setModel(event.target.value)} className={CONTROL} placeholder="Copy from your provider dashboard" autoComplete="off" required disabled={status === "running"} />
              <span className="mt-1.5 block text-[0.6875rem] text-muted">Exact IDs differ by provider.</span>
            </label>
          </div>

          <label className="mt-5 block">
            <span className="mb-2 flex items-center justify-between gap-3 text-xs text-secondary">
              API key
              <span className="font-mono text-[0.625rem] text-iris-fg">never persisted</span>
            </span>
            <input value={apiKey} onChange={(event) => setApiKey(event.target.value)} className={CONTROL} type="password" placeholder="Paste for this run only" autoComplete="new-password" spellCheck={false} required disabled={status === "running"} />
          </label>

          <div className="mt-9 flex items-center justify-between gap-4 border-b border-hairline pb-5">
            <div>
              <p className="font-mono text-xs text-iris-fg">02 / scope</p>
              <h2 className="mt-1 text-lg text-fg">Benchmark window</h2>
            </div>
            <span className="font-mono text-xs text-muted">public multiple-choice</span>
          </div>

          <div className="mt-6 grid gap-5 sm:grid-cols-2">
            <label className="block sm:col-span-2">
              <span className="mb-2 block text-xs text-secondary">Benchmark</span>
              <select value={benchmark} onChange={(event) => setBenchmark(event.target.value as BrowserBenchmarkId)} className={CONTROL} disabled={status === "running"}>
                {BROWSER_BENCHMARKS.map((entry) => (
                  <option key={entry.id} value={entry.id}>{entry.name} — {entry.description}</option>
                ))}
              </select>
              <span className="mt-1.5 block text-[0.6875rem] text-muted">{selectedBenchmark?.split} split · fetched from the declared upstream source</span>
            </label>
            <label className="block">
              <span className="mb-2 flex justify-between text-xs text-secondary"><span>Parent items</span><span className="font-mono text-fg">{itemCount}</span></span>
              <input type="range" min="1" max={MAX_BROWSER_ITEMS} value={itemCount} onChange={(event) => setItemCount(Number(event.target.value))} className="w-full accent-[var(--color-iris)]" disabled={status === "running"} />
            </label>
            <label className="block">
              <span className="mb-2 block text-xs text-secondary">Dataset offset</span>
              <input type="number" min="0" max="10000" value={offset} onChange={(event) => setOffset(Number(event.target.value))} className={CONTROL} disabled={status === "running"} />
            </label>
          </div>

          <label className="mt-7 flex cursor-pointer items-start gap-3 rounded-lg border border-warn/25 bg-warn-dim/20 p-4">
            <input type="checkbox" checked={acknowledged} onChange={(event) => setAcknowledged(event.target.checked)} className="mt-0.5 size-4 accent-[var(--color-iris)]" required disabled={status === "running"} />
            <span className="text-xs leading-relaxed text-secondary">
              I understand that {requests} benchmark prompts will be sent to {selectedProvider?.name},
              may incur charges on my account, and are governed by that provider&apos;s data policy.
            </span>
          </label>

          <div className="mt-6 flex flex-wrap items-center gap-3">
            <button type="submit" disabled={status === "running"} className="rounded-md border border-iris/50 bg-iris-dim px-4 py-2.5 font-mono text-sm text-iris-fg transition-colors hover:border-iris disabled:cursor-not-allowed disabled:opacity-50">
              {status === "running" ? "Running audit…" : `Run ${requests} requests →`}
            </button>
            {status === "running" ? (
              <button type="button" onClick={cancel} className="rounded-md px-3 py-2 text-sm text-secondary hover:text-fg">Cancel</button>
            ) : null}
          </div>
          <div aria-live="polite">
            {status === "running" ? <p className="mt-4 text-xs text-muted">Fetching the benchmark, evaluating canonical prompts and two validated variants per item. Keep this tab open.</p> : null}
            {error ? <p className="mt-4 rounded-md border border-danger/40 bg-danger-dim p-3 text-sm text-danger-fg">{error}</p> : null}
          </div>
        </form>

        <aside className="space-y-4 lg:sticky lg:top-20 lg:self-start">
          <SummaryCard label="Requests" value={String(requests)} body={`${itemCount} canonical + ${itemCount * 2} transformed`} />
          <SummaryCard label="Output cap" value={`${requests * 16} tokens`} body="Provider input tokens and pricing vary by model." />
          <SummaryCard label="Evidence" value="3 paired tests" body="Overall perturbation, answer order, and template dependence." />
          <div className="rounded-lg border border-line p-4 text-xs leading-relaxed text-muted">
            This first hosted release intentionally excludes gated/private benchmarks, arbitrary
            endpoints, code execution, and claims of proven training membership.
          </div>
        </aside>
      </div>

      {report ? <AuditResult report={report} download={download} /> : null}
    </main>
  );
}

function SummaryCard({ label, value, body }: { label: string; value: string; body: string }) {
  return (
    <div className="rounded-lg border border-line bg-surface/20 p-4">
      <p className="font-mono text-[0.625rem] uppercase tracking-[0.08em] text-muted">{label}</p>
      <p className="mt-2 font-mono text-xl text-fg">{value}</p>
      <p className="mt-2 text-xs leading-relaxed text-secondary">{body}</p>
    </div>
  );
}

function AuditResult({ report, download }: { report: BrowserAuditReport; download: () => void }) {
  const canonical = report.responses.filter((response) => !response.item_id.includes("::"));
  const failures = report.responses.filter((response) => response.error).length;
  return (
    <section className="border-t border-hairline py-12">
      <div className="flex flex-wrap items-end justify-between gap-5">
        <div>
          <p className="font-mono text-xs text-iris-fg">03 / complete</p>
          <h2 className="mt-2 text-2xl font-semibold text-fg">Audit evidence package</h2>
          <p className="mt-2 break-all font-mono text-[0.6875rem] text-muted">{report.audit_hash}</p>
        </div>
        <button type="button" onClick={download} className="rounded-md border border-iris/50 bg-iris-dim px-4 py-2.5 font-mono text-sm text-iris-fg hover:border-iris">
          Download report.json
        </button>
      </div>

      <div className="mt-7 grid gap-3 sm:grid-cols-4">
        <ResultMetric label="Canonical" value={pct(report.score.canonical_reproduced_score)} />
        <ResultMetric label="Robust" value={pct(report.score.robust_score)} />
        <ResultMetric label="Robustness gap" value={pct(report.score.robustness_gap)} warn={report.score.robustness_gap > 0} />
        <ResultMetric label="Failed requests" value={String(failures)} warn={failures > 0} />
      </div>

      <div className="mt-8 overflow-hidden rounded-lg border border-line">
        <div className="grid grid-cols-[100px_1fr_90px] gap-3 bg-elevated px-4 py-3 font-mono text-[0.6875rem] uppercase tracking-wide text-muted">
          <span>Item</span><span>Model response</span><span>Result</span>
        </div>
        {canonical.slice(0, 8).map((response) => {
          const expected = report.benchmark.items.find((entry) => entry.id === response.item_id)?.expected_output;
          const correct = response.parsed_answer === expected;
          return (
            <div key={response.item_id} className="grid grid-cols-[100px_1fr_90px] gap-3 border-t border-hairline px-4 py-3 text-xs">
              <span className="truncate font-mono text-secondary">{response.item_id}</span>
              <span className="truncate text-secondary">{response.raw_text || response.error || "No response"}</span>
              <span className={`font-mono ${correct ? "text-iris-fg" : "text-warn-fg"}`}>{correct ? "correct" : "inspect"}</span>
            </div>
          );
        })}
      </div>
      <p className="mt-4 text-xs leading-relaxed text-muted">
        Download the complete package for every prompt, transformation, response, finding,
        unavailable detector, and provenance record, then open it in the <Link href="/report" className="text-iris-fg underline-offset-4 hover:underline">full report viewer</Link>.
      </p>
    </section>
  );
}

function ResultMetric({ label, value, warn = false }: { label: string; value: string; warn?: boolean }) {
  return (
    <div className="rounded-lg border border-line bg-surface/20 p-4">
      <p className="text-xs text-muted">{label}</p>
      <p className={`mt-2 font-mono text-2xl ${warn ? "text-warn-fg" : "text-fg"}`}>{value}</p>
    </div>
  );
}

"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { isReasoningModel } from "../../lib/audit-logic";
import {
  BROWSER_BENCHMARKS,
  BROWSER_PROVIDERS,
  type BrowserAuditReport,
  type BrowserBenchmarkId,
  type BrowserProviderId,
  defaultOutputTokens,
  MAX_BROWSER_ITEMS,
  OUTPUT_BUDGETS,
  requestCount,
} from "../../lib/browser-audit";
import { parseV2Report, type V2Report } from "../../lib/v2-report";
import { ReportView } from "../viewer/ReportView";

const CONTROL =
  "w-full rounded-md border border-line bg-base px-3 py-2.5 text-sm text-fg outline-none transition-colors placeholder:text-faint focus:border-iris/70 disabled:opacity-60";
const SETTINGS_KEY = "veritas.run.settings.v1";
const CONCURRENCY = 6;

type Settings = {
  provider: BrowserProviderId;
  benchmark: BrowserBenchmarkId;
  model: string;
  itemCount: number;
  offset: number;
  budget: "auto" | number;
};

const DEFAULTS: Settings = { provider: "together", benchmark: "mmlu", model: "", itemCount: 20, offset: 0, budget: "auto" };

/** Non-secret preferences only: the API key is never written to browser storage. */
function loadSettings(): Settings {
  try {
    const raw = JSON.parse(window.localStorage.getItem(SETTINGS_KEY) ?? "null") as Partial<Settings> | null;
    if (!raw) return DEFAULTS;
    return {
      provider: BROWSER_PROVIDERS.some((entry) => entry.id === raw.provider) ? raw.provider! : DEFAULTS.provider,
      benchmark: BROWSER_BENCHMARKS.some((entry) => entry.id === raw.benchmark) ? raw.benchmark! : DEFAULTS.benchmark,
      model: typeof raw.model === "string" ? raw.model.slice(0, 200) : "",
      itemCount: Number.isInteger(raw.itemCount) ? Math.min(Math.max(raw.itemCount!, 1), MAX_BROWSER_ITEMS) : DEFAULTS.itemCount,
      offset: Number.isInteger(raw.offset) ? Math.min(Math.max(raw.offset!, 0), 10000) : 0,
      budget: raw.budget === "auto" || OUTPUT_BUDGETS.includes(raw.budget as never) ? raw.budget! : "auto",
    };
  } catch {
    return DEFAULTS;
  }
}

function clock(seconds: number): string {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

export function AuditRunner() {
  const [settings, setSettings] = useState<Settings>(DEFAULTS);
  const [hydrated, setHydrated] = useState(false);
  const [apiKey, setApiKey] = useState("");
  const [acknowledged, setAcknowledged] = useState(false);
  const [status, setStatus] = useState<"idle" | "running" | "complete" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<BrowserAuditReport | null>(null);
  const [view, setView] = useState<V2Report | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const abortRef = useRef<AbortController | null>(null);
  const resultRef = useRef<HTMLElement>(null);

  useEffect(() => {
    setSettings(loadSettings());
    setHydrated(true);
  }, []);
  useEffect(() => {
    if (!hydrated) return;
    try {
      window.localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
    } catch {
      /* storage unavailable (private mode): preferences simply are not remembered */
    }
  }, [settings, hydrated]);
  useEffect(() => {
    if (status !== "running") return;
    setElapsed(0);
    const started = Date.now();
    const timer = window.setInterval(() => setElapsed(Math.round((Date.now() - started) / 1000)), 1000);
    return () => window.clearInterval(timer);
  }, [status]);

  const update = <K extends keyof Settings>(key: K, value: Settings[K]) => setSettings((current) => ({ ...current, [key]: value }));
  const running = status === "running";
  const requests = requestCount(settings.itemCount);
  const provider = BROWSER_PROVIDERS.find((entry) => entry.id === settings.provider)!;
  const benchmark = BROWSER_BENCHMARKS.find((entry) => entry.id === settings.benchmark)!;
  const budget = settings.budget === "auto" ? defaultOutputTokens(settings.model) : settings.budget;
  const reasoning = isReasoningModel(settings.model);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus("running");
    setError(null);
    setReport(null);
    setView(null);
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const response = await fetch("/api/audits", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        cache: "no-store",
        signal: controller.signal,
        body: JSON.stringify({
          provider: settings.provider,
          benchmark: settings.benchmark,
          model: settings.model,
          apiKey,
          itemCount: settings.itemCount,
          offset: settings.offset,
          maxOutputTokens: budget,
          acknowledgeExternalTransfer: acknowledged,
        }),
      });
      const body = (await response.json().catch(() => ({ error: `The server returned HTTP ${response.status}.` }))) as BrowserAuditReport | { error?: string };
      if (!response.ok || !("schema_version" in body)) {
        throw new Error("error" in body && body.error ? body.error : "The audit did not complete.");
      }
      setReport(body);
      setView(parseV2Report(body));
      setStatus("complete");
      window.setTimeout(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
    } catch (cause) {
      setError(
        cause instanceof DOMException && cause.name === "AbortError"
          ? "Audit cancelled. Your provider key was cleared."
          : cause instanceof Error
            ? cause.message
            : "The audit did not complete.",
      );
      setStatus("error");
    } finally {
      setApiKey("");
      setAcknowledged(false);
      abortRef.current = null;
    }
  }

  function download() {
    if (!report) return;
    const url = URL.createObjectURL(new Blob([`${JSON.stringify(report, null, 2)}\n`], { type: "application/json" }));
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
          <p className="font-mono text-[0.6875rem] uppercase tracking-[0.08em] text-muted">browser audit console · bring your own key</p>
          <h1 className="mt-3 max-w-3xl text-balance text-3xl font-semibold tracking-tight text-fg sm:text-4xl">
            Run a benchmark-integrity audit from the browser.
          </h1>
          <p className="mt-4 max-w-2xl text-pretty text-[0.9375rem] leading-relaxed text-secondary">
            Pick a benchmark and a model. Veritas asks each question three ways — as published, with the
            answer options moved, and in a different prompt template — then tests whether the score holds.
          </p>
          <p className="mt-3 text-sm text-muted">
            No key handy?{" "}
            <Link href="/report?sample" className="text-iris-fg underline-offset-4 hover:underline">
              Explore a sample report
            </Link>{" "}
            first.
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
          <SectionTitle step="01" title="Model" aside="OpenAI-compatible" />
          <div className="mt-6 grid gap-5 sm:grid-cols-2">
            <label className="block">
              <span className="mb-2 block text-xs text-secondary">Provider</span>
              <select value={settings.provider} onChange={(event) => update("provider", event.target.value as BrowserProviderId)} className={CONTROL} disabled={running}>
                {BROWSER_PROVIDERS.map((entry) => (
                  <option key={entry.id} value={entry.id}>{entry.name}</option>
                ))}
              </select>
              <span className="mt-1.5 block text-[0.6875rem] text-muted">{provider.description}</span>
            </label>
            <label className="block">
              <span className="mb-2 block text-xs text-secondary">Model ID</span>
              <input value={settings.model} onChange={(event) => update("model", event.target.value)} className={CONTROL} placeholder={`e.g. ${provider.example}`} autoComplete="off" spellCheck={false} required disabled={running} />
              <span className="mt-1.5 block text-[0.6875rem] text-muted">
                Exact ID from your provider dashboard.{" "}
                {settings.model !== provider.example && (
                  <button type="button" onClick={() => update("model", provider.example)} className="text-iris-fg underline-offset-2 hover:underline" disabled={running}>
                    Use {provider.example.length > 28 ? "example" : provider.example}
                  </button>
                )}
              </span>
            </label>
          </div>

          <label className="mt-5 block">
            <span className="mb-2 flex items-center justify-between gap-3 text-xs text-secondary">
              API key
              <span className="font-mono text-[0.625rem] text-iris-fg">used once · never stored</span>
            </span>
            <input value={apiKey} onChange={(event) => setApiKey(event.target.value)} className={CONTROL} type="password" placeholder={`Paste your ${provider.name} key for this run`} autoComplete="off" spellCheck={false} required disabled={running} />
          </label>

          <SectionTitle step="02" title="Benchmark window" aside="public multiple-choice" className="mt-9" />
          <div className="mt-6 grid gap-5 sm:grid-cols-2">
            <label className="block sm:col-span-2">
              <span className="mb-2 block text-xs text-secondary">Benchmark</span>
              <select value={settings.benchmark} onChange={(event) => update("benchmark", event.target.value as BrowserBenchmarkId)} className={CONTROL} disabled={running}>
                {BROWSER_BENCHMARKS.map((entry) => (
                  <option key={entry.id} value={entry.id}>{entry.name} — {entry.description}</option>
                ))}
              </select>
              <span className="mt-1.5 block text-[0.6875rem] text-muted">{benchmark.split} split · fetched from the upstream Hugging Face dataset</span>
            </label>
            <label className="block">
              <span className="mb-2 flex justify-between text-xs text-secondary">
                <span>Items</span>
                <span className="tnum font-mono text-fg">{settings.itemCount}</span>
              </span>
              <input type="range" min="1" max={MAX_BROWSER_ITEMS} value={settings.itemCount} onChange={(event) => update("itemCount", Number(event.target.value))} className="w-full accent-[var(--color-iris)]" disabled={running} />
              <span className="mt-1 block text-[0.6875rem] text-muted">{settings.itemCount < 10 ? "Verdicts need at least 10 items." : "More items give tighter intervals."}</span>
            </label>
            <label className="block">
              <span className="mb-2 block text-xs text-secondary">Start at item</span>
              <input type="number" min="0" max="10000" value={settings.offset} onChange={(event) => update("offset", Math.min(Math.max(Math.trunc(Number(event.target.value) || 0), 0), 10000))} className={CONTROL} disabled={running} />
            </label>
            <label className="block sm:col-span-2">
              <span className="mb-2 block text-xs text-secondary">Output budget per request</span>
              <select value={String(settings.budget)} onChange={(event) => update("budget", event.target.value === "auto" ? "auto" : Number(event.target.value))} className={CONTROL} disabled={running}>
                <option value="auto">Auto — {defaultOutputTokens(settings.model)} tokens{reasoning ? " (reasoning model detected)" : ""}</option>
                {OUTPUT_BUDGETS.map((value) => (
                  <option key={value} value={value}>{value} tokens</option>
                ))}
              </select>
              <span className="mt-1.5 block text-[0.6875rem] text-muted">
                Reasoning models think before answering and need a larger budget; they are also slower, so use fewer items.
              </span>
            </label>
          </div>

          <label className="mt-7 flex cursor-pointer items-start gap-3 rounded-lg border border-warn/25 bg-warn-dim/20 p-4">
            <input type="checkbox" checked={acknowledged} onChange={(event) => setAcknowledged(event.target.checked)} className="mt-0.5 size-4 accent-[var(--color-iris)]" required disabled={running} />
            <span className="text-xs leading-relaxed text-secondary">
              I understand that {requests} benchmark prompts will be sent to {provider.name}, may incur
              charges on my account (up to {(requests * budget).toLocaleString()} output tokens), and are
              governed by that provider&apos;s data policy.
            </span>
          </label>

          <div className="mt-6 flex flex-wrap items-center gap-3">
            <button type="submit" disabled={running} className="rounded-md border border-iris/50 bg-iris-dim px-4 py-2.5 font-mono text-sm text-iris-fg transition-colors hover:border-iris disabled:cursor-not-allowed disabled:opacity-50">
              {running ? `Running… ${clock(elapsed)}` : `Run ${requests} requests →`}
            </button>
            {running && (
              <button type="button" onClick={() => abortRef.current?.abort()} className="rounded-md px-3 py-2 text-sm text-secondary hover:text-fg">
                Cancel
              </button>
            )}
          </div>
          <div aria-live="polite">
            {running && (
              <div className="mt-4">
                <div className="h-1 overflow-hidden rounded-full bg-elevated">
                  <div className="h-full w-1/3 animate-[progress_1.6s_ease-in-out_infinite] rounded-full bg-iris/70" />
                </div>
                <p className="mt-2 text-xs text-muted">
                  Fetching {settings.itemCount} items, then sending {requests} requests {CONCURRENCY} at a time. Typical runs take
                  {reasoning || budget > 256 ? " a few minutes" : " under a minute"}; keep this tab open.
                </p>
              </div>
            )}
            {error && <p role="alert" className="mt-4 rounded-md border border-danger/40 bg-danger-dim p-3 text-sm text-danger-fg">{error}</p>}
          </div>
        </form>

        <aside className="space-y-4 lg:sticky lg:top-20 lg:self-start">
          <SummaryCard label="Requests" value={String(requests)} body={`${settings.itemCount} original + ${settings.itemCount * 2} variants (options moved, new template)`} />
          <SummaryCard label="Output cap" value={`${(requests * budget).toLocaleString()} tokens`} body={`${budget} per request. Input tokens and pricing vary by model.`} />
          <SummaryCard label="Evidence" value="3 paired tests" body="Surface-form dependence, answer-position dependence, and template dependence, with 95% intervals and corrected p-values." />
          <div className="rounded-lg border border-line p-4 text-xs leading-relaxed text-muted">
            Need private data, local models, caching, or thousands of items? Use the{" "}
            <Link href="/docs" className="text-iris-fg underline-offset-4 hover:underline">CLI</Link>.
            Hosted runs never claim proven training membership.
          </div>
        </aside>
      </div>

      {view && report && (
        <section ref={resultRef} className="scroll-mt-20 border-t border-hairline py-12">
          <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
            <p className="font-mono text-xs text-iris-fg">03 / results</p>
            <div className="flex flex-wrap gap-2">
              <button type="button" onClick={download} className="rounded-md border border-iris/50 bg-iris-dim px-4 py-2 font-mono text-sm text-iris-fg hover:border-iris">
                Download report.json
              </button>
              <button type="button" onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })} className="rounded-md border border-line px-4 py-2 text-sm text-secondary hover:border-edge hover:text-fg">
                Run another
              </button>
            </div>
          </div>
          <ReportView report={view} />
        </section>
      )}
    </main>
  );
}

function SectionTitle({ step, title, aside, className = "" }: { step: string; title: string; aside: string; className?: string }) {
  return (
    <div className={`flex items-center justify-between gap-4 border-b border-hairline pb-5 ${className}`}>
      <div>
        <p className="font-mono text-xs text-iris-fg">{step} / configure</p>
        <h2 className="mt-1 text-lg text-fg">{title}</h2>
      </div>
      <span className="rounded-full border border-line px-2.5 py-1 font-mono text-[0.625rem] text-muted">{aside}</span>
    </div>
  );
}

function SummaryCard({ label, value, body }: { label: string; value: string; body: string }) {
  return (
    <div className="rounded-lg border border-line bg-surface/20 p-4">
      <p className="font-mono text-[0.625rem] uppercase tracking-[0.08em] text-muted">{label}</p>
      <p className="tnum mt-2 font-mono text-xl text-fg">{value}</p>
      <p className="mt-2 text-xs leading-relaxed text-secondary">{body}</p>
    </div>
  );
}

import Link from "next/link";
import type { CSSProperties } from "react";

import { Eyebrow } from "../ui";

const FOCUS = "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-iris";

const SIGNALS = [
  ["canonical score", "baseline"],
  ["validated variants", "paired"],
  ["fresh-set transfer", "when available"],
  ["exposure evidence", "calibrated or not run"],
];

export function Hero() {
  return (
    <section>
      <div className="mx-auto grid max-w-[1100px] items-center gap-x-14 gap-y-12 px-5 pb-20 pt-16 sm:px-8 sm:pt-24 lg:grid-cols-[1.02fr_0.98fr]">
        <div className="enter">
          <Eyebrow>benchmark integrity auditor</Eyebrow>
          <h1 className="mt-4 text-balance text-[2rem] font-semibold leading-[1.1] tracking-tight text-fg sm:text-[2.6rem] sm:leading-[1.06]">
            Check whether frontier models are benchmark maxxing.
          </h1>
          <p className="mt-5 max-w-xl text-pretty text-[0.9375rem] leading-relaxed text-secondary sm:text-[1.0625rem]">
            Veritas stress-tests reported scores across prompt wording, answer order, templates,
            repeated samples, and fresh data—then separates robust capability from protocol
            dependence, exposure-consistent signals, evaluator weakness, and uncertainty.
          </p>
          <p className="mt-3 max-w-xl text-pretty text-[0.8125rem] leading-relaxed text-muted">
            Behavioral evidence is not proof of contamination. Veritas reports what the evidence
            supports and marks unavailable tests as not run.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-x-5 gap-y-3">
            <Link
              href="/run"
              className={`rounded-md border border-iris/40 bg-iris-dim px-4 py-2 font-mono text-[0.8125rem] text-iris-fg transition-all duration-200 hover:-translate-y-0.5 hover:border-iris/70 hover:shadow-[0_6px_20px_-6px_rgba(110,120,240,0.35)] ${FOCUS}`}
            >
              Run an audit in the browser →
            </Link>
            <Link
              href="/report"
              className={`rounded-sm text-[0.8125rem] text-secondary underline-offset-4 transition-colors hover:text-fg hover:underline ${FOCUS}`}
            >
              Open a completed report
            </Link>
            <a
              href="#how"
              className={`rounded-sm text-[0.8125rem] text-secondary underline-offset-4 transition-colors hover:text-fg hover:underline ${FOCUS}`}
            >
              See the audit workflow ↓
            </a>
          </div>
        </div>

        <Link
          href="/run"
          aria-label="Run a benchmark integrity audit"
          style={{ "--delay": "120ms" } as CSSProperties}
          className={`enter group block rounded-lg border border-hairline bg-surface/30 p-6 transition-all duration-300 ease-out hover:-translate-y-1 hover:border-line hover:shadow-[0_16px_40px_-16px_rgba(0,0,0,0.55)] sm:p-7 ${FOCUS}`}
        >
          <div className="mb-6 flex items-baseline justify-between gap-3">
            <span className="font-mono text-[0.8125rem] text-fg">frontier model audit</span>
            <span className="font-mono text-[0.625rem] uppercase tracking-[0.08em] text-faint">
              schema v2
            </span>
          </div>
          <div className="space-y-3">
            {SIGNALS.map(([label, status], index) => (
              <div
                key={label}
                className="grid grid-cols-[1fr_auto] items-center gap-4 border-t border-hairline pt-3"
              >
                <span className="text-[0.8125rem] text-secondary">{label}</span>
                <span
                  className={`font-mono text-[0.6875rem] ${index === 3 ? "text-warn-fg" : "text-iris-fg"}`}
                >
                  {status}
                </span>
              </div>
            ))}
          </div>
          <span className="mt-6 inline-block font-mono text-[0.75rem] text-iris-fg transition-transform duration-200 group-hover:translate-x-1">
            choose a model, benchmark, and request budget →
          </span>
        </Link>
      </div>
    </section>
  );
}

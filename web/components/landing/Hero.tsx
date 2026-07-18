import Link from "next/link";
import type { CSSProperties } from "react";

import { FIXTURES } from "../../lib/fixtures";
import { Eyebrow } from "../ui";
import { CollapseViz } from "./CollapseViz";

const FOCUS = "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-iris";

export function Hero() {
  const r3 = FIXTURES.find((f) => f.id === "r3_random")!.report;
  const reported = r3.reported?.value ?? 0.165;
  const honest = r3.honest?.value ?? 0.018;
  const delta = r3.delta?.value ?? 0.147;

  return (
    <section>
      <div className="mx-auto grid max-w-[1100px] items-center gap-x-14 gap-y-12 px-5 pb-20 pt-16 sm:px-8 sm:pt-24 lg:grid-cols-[1.02fr_0.98fr]">
        {/* Left — the thesis */}
        <div className="enter">
          <Eyebrow>leakage &amp; robustness auditor</Eyebrow>
          <h1 className="mt-4 text-balance text-[2rem] font-semibold leading-[1.1] tracking-tight text-fg sm:text-[2.6rem] sm:leading-[1.06]">
            ML models report inflated performance because their benchmarks leak.
          </h1>
          <p className="mt-5 max-w-xl text-pretty text-[0.9375rem] leading-relaxed text-secondary sm:text-[1.0625rem]">
            Veritas measures how much survives once train/test homology is removed — model-agnostic,
            provenance-stamped, reproducible. It never runs your model.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-x-5 gap-y-3">
            <Link
              href="/report"
              className={`rounded-md border border-iris/40 bg-iris-dim px-4 py-2 font-mono text-[0.8125rem] text-iris-fg transition-all duration-200 hover:-translate-y-0.5 hover:border-iris/70 hover:shadow-[0_6px_20px_-6px_rgba(110,120,240,0.35)] ${FOCUS}`}
            >
              Open the report viewer →
            </Link>
            <a
              href="#how"
              className={`rounded-sm text-[0.8125rem] text-secondary underline-offset-4 transition-colors hover:text-fg hover:underline ${FOCUS}`}
            >
              See how it works ↓
            </a>
          </div>
        </div>

        {/* Right — one real audit, rendered as the hero instrument */}
        <Link
          href="/report?report=r3_random"
          aria-label="Open the OverfitNN random-split audit in the report viewer"
          style={{ "--delay": "120ms" } as CSSProperties}
          className={`enter group block rounded-lg border border-hairline bg-surface/30 p-6 transition-all duration-300 ease-out hover:-translate-y-1 hover:border-line hover:shadow-[0_16px_40px_-16px_rgba(0,0,0,0.55)] sm:p-7 ${FOCUS}`}
        >
          <div className="mb-6 flex items-baseline justify-between gap-3">
            <span className="font-mono text-[0.8125rem] text-fg">OverfitNN · random split</span>
            <span className="font-mono text-[0.625rem] uppercase tracking-[0.08em] text-faint">
              metric audit
            </span>
          </div>
          <CollapseViz reported={reported} honest={honest} delta={delta} variant="hero" />
          <span className="mt-6 inline-block font-mono text-[0.75rem] text-iris-fg transition-transform duration-200 group-hover:translate-x-1">
            open this audit →
          </span>
        </Link>
      </div>
    </section>
  );
}

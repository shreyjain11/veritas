import Link from "next/link";

import { FIXTURES } from "../../lib/fixtures";
import { Eyebrow } from "../ui";
import { CollapseViz } from "./CollapseViz";

export function Hero() {
  const r3 = FIXTURES.find((f) => f.id === "r3_random")!.report;
  const reported = r3.reported?.value ?? 0.165;
  const honest = r3.honest?.value ?? 0.018;
  const delta = r3.delta?.value ?? 0.147;

  return (
    <section className="mx-auto max-w-[1100px] px-5 pb-16 pt-14 sm:px-8 sm:pb-24 sm:pt-20">
      <Eyebrow>leakage &amp; robustness auditor</Eyebrow>
      <h1 className="mt-4 max-w-3xl text-[2rem] font-semibold leading-[1.12] tracking-tight text-fg sm:text-5xl">
        ML models report inflated performance because their benchmarks leak.
      </h1>
      <p className="mt-5 max-w-2xl text-[0.9375rem] leading-relaxed text-secondary sm:text-lg">
        Veritas measures how much survives once train/test homology is removed — model-agnostic,
        provenance-stamped, reproducible. It never runs your model.
      </p>

      <div className="mt-10 max-w-2xl rounded-lg border border-hairline bg-surface/50 px-6 py-6">
        <CollapseViz reported={reported} honest={honest} delta={delta} variant="hero" />
        <Link
          href="/report?report=r3_random"
          className="mt-4 inline-block rounded-sm font-mono text-[0.75rem] text-muted underline-offset-4 transition-colors hover:text-fg hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-iris"
        >
          OverfitNN · random split — a real audit →
        </Link>
      </div>

      <div className="mt-8 flex flex-wrap items-center gap-x-5 gap-y-3">
        <Link
          href="/report"
          className="rounded-md border border-iris/40 bg-iris-dim px-4 py-2 font-mono text-[0.8125rem] text-iris-fg transition-colors hover:border-iris/70 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-iris"
        >
          Open the report viewer →
        </Link>
        <a
          href="#how"
          className="rounded-sm text-[0.8125rem] text-secondary underline-offset-4 transition-colors hover:text-fg hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-iris"
        >
          See how it works ↓
        </a>
      </div>
    </section>
  );
}

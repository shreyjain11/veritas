import Link from "next/link";

import { Reveal } from "../Reveal";

const LINK =
  "rounded-sm text-iris-fg underline-offset-4 transition-colors hover:text-iris hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-iris";

export function HonestNote() {
  return (
    <section className="mx-auto max-w-[1100px] px-5 py-10 sm:px-8">
      <Reveal className="max-w-3xl">
        <p className="text-[0.875rem] leading-relaxed text-secondary">
          Veritas does not convert behavioral anomalies into a contamination verdict. Results
          distinguish exact or semantic exposure evidence, protocol dependence, evaluator weakness,
          distribution shift, legitimate capability, unavailable evidence, and inconclusive outcomes.
          The original biological leakage auditor remains supported through the legacy report path.
        </p>
        <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2 font-mono text-[0.8125rem]">
          <Link href="/docs#interpretation" className={LINK}>
            Scientific claims
          </Link>
          <a href="https://github.com/shreyjain11/veritas" target="_blank" rel="noreferrer" className={LINK}>
            GitHub
          </a>
          <Link href="/report/legacy" className={LINK}>
            Legacy bio viewer
          </Link>
        </div>
      </Reveal>
    </section>
  );
}

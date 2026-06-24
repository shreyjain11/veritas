import Link from "next/link";

import { Reveal } from "../Reveal";

const LINK =
  "rounded-sm text-iris-fg underline-offset-4 transition-colors hover:text-iris hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-iris";

export function HonestNote() {
  return (
    <Reveal>
    <section className="mx-auto max-w-[1100px] px-5 py-10 sm:px-8">
      <div className="max-w-3xl border-l-2 border-line pl-5">
        <p className="text-[0.875rem] leading-relaxed text-secondary">
          An independent research project. Every number on this site is from a real run on pinned
          data, locked by a test — nothing is fabricated. Structural detection is fold-level
          (foldseek), a more permissive signal than interface-level redundancy; results corroborate
          prior work qualitatively, not numerically.
        </p>
        <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2 font-mono text-[0.8125rem]">
          <Link href="/docs#results" className={LINK}>
            Validation
          </Link>
          <a href="https://github.com/shreyjain11/veritas" target="_blank" rel="noreferrer" className={LINK}>
            GitHub
          </a>
          <Link href="/docs" className={LINK}>
            Docs
          </Link>
        </div>
      </div>
    </section>
    </Reveal>
  );
}

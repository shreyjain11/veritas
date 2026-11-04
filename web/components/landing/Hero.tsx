import Link from "next/link";

import { buttonClass } from "../ui";
import { FlipExample } from "./FlipExample";

export function Hero() {
  return (
    <section className="mx-auto grid max-w-[1120px] items-center gap-x-14 gap-y-12 px-5 pt-14 pb-20 sm:px-8 sm:pt-20 lg:grid-cols-[1fr_0.95fr]">
      <div className="enter">
        <h1 className="font-display text-[2.5rem] leading-[1.05] font-medium tracking-[-0.015em] text-balance text-fg sm:text-[3.25rem]">
          Check whether frontier models are benchmark maxxing.
        </h1>
        <p className="mt-6 max-w-xl text-[1.0625rem] leading-relaxed text-pretty text-secondary">
          Veritas asks every benchmark question again, with the options moved, the labels renamed,
          and the template changed, then tests whether the score holds. Each verdict comes with a
          confidence interval, and tests it could not run are listed, not hidden.
        </p>
        <div className="mt-8 flex flex-wrap items-center gap-3">
          <Link href="/run" className={buttonClass("primary", "px-5 py-2.5")}>
            Run an audit
          </Link>
          <Link href="/report?sample" className={buttonClass("secondary", "px-5 py-2.5")}>
            View a sample report
          </Link>
        </div>
        <p className="mt-5 text-sm text-muted">
          Bring your own API key, or run the open-source CLI on private data and local models.
        </p>
      </div>
      <div className="enter" style={{ "--delay": "100ms" } as React.CSSProperties}>
        <FlipExample />
      </div>
    </section>
  );
}

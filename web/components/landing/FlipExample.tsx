import { Check, X } from "lucide-react";
import Link from "next/link";

import { cn } from "../../lib/cn";
import { FOCUS_RING, StatusPill } from "../ui";

// Item add-02 and its option-order variant, verbatim from web/fixtures/v2/sample_report.json.
const ORIGINAL = { choices: [["a", "25"], ["b", "37"], ["c", "27"], ["d", "28"]], key: "c", picked: "c" } as const;
const MOVED = { choices: [["a", "37"], ["b", "28"], ["c", "25"], ["d", "27"]], key: "d", picked: "c" } as const;

function Options({ title, variant }: { title: string; variant: typeof ORIGINAL | typeof MOVED }) {
  const correct = variant.picked === variant.key;
  return (
    <div className="min-w-0">
      <p className="text-[0.8125rem] font-medium text-secondary">{title}</p>
      <ul className="mt-2 space-y-1">
        {variant.choices.map(([label, text]) => {
          const isKey = label === variant.key;
          const isPick = label === variant.picked;
          return (
            <li
              key={label}
              className={cn(
                "flex items-center gap-2.5 rounded-md border px-2.5 py-1.5 text-sm",
                isPick && correct && "border-iris/40 bg-iris-dim",
                isPick && !correct && "border-warn/40 bg-warn-dim",
                !isPick && "border-transparent",
              )}
            >
              <span className="font-mono text-xs text-muted">{label}</span>
              <span className={cn("tnum font-mono", isKey ? "font-semibold text-fg" : "text-secondary")}>{text}</span>
              {isKey && <span className="text-xs text-muted">answer</span>}
              {isPick && (
                <span className={cn("ml-auto inline-flex items-center gap-1 text-xs font-medium", correct ? "text-iris-fg" : "text-warn-fg")}>
                  {correct ? <Check aria-hidden className="size-3.5" /> : <X aria-hidden className="size-3.5" />}
                  model
                </span>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function FlipExample() {
  return (
    <figure className="overflow-hidden rounded-xl border border-line bg-surface shadow-[0_1px_2px_rgba(0,0,0,0.04),0_12px_32px_-16px_rgba(0,0,0,0.18)]">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-hairline px-5 py-3">
        <span className="text-[0.8125rem] text-muted">One item from the sample audit</span>
        <StatusPill tone="warn">answer-position dependence</StatusPill>
      </div>
      <div className="px-5 py-5">
        <p className="font-display text-2xl text-fg">What is 13 + 14?</p>
        <div className="mt-4 grid gap-5 sm:grid-cols-2">
          <Options title="As published" variant={ORIGINAL} />
          <Options title="Options moved" variant={MOVED} />
        </div>
        <p className="mt-4 text-sm leading-relaxed text-secondary">
          The answer moved to <span className="font-mono text-fg">d</span>. The model still said{" "}
          <span className="font-mono text-fg">c</span>: it followed the letter, not the arithmetic.
        </p>
      </div>
      <dl className="grid grid-cols-3 border-t border-hairline text-sm">
        <div className="px-5 py-3">
          <dt className="text-xs text-muted">As published</dt>
          <dd className="tnum mt-0.5 font-mono text-lg text-fg">97.5%</dd>
        </div>
        <div className="border-l border-hairline px-5 py-3">
          <dt className="text-xs text-muted">Under variants</dt>
          <dd className="tnum mt-0.5 font-mono text-lg text-fg">79.2%</dd>
        </div>
        <div className="border-l border-hairline px-5 py-3">
          <dt className="text-xs text-muted">Drop (95% CI)</dt>
          <dd className="tnum mt-0.5 font-mono text-lg text-warn-fg">18.3 pts</dd>
          <dd className="tnum font-mono text-[0.6875rem] text-muted">6.7 to 30.0</dd>
        </div>
      </dl>
      <figcaption className="flex flex-wrap items-center justify-between gap-2 border-t border-hairline bg-subtle px-5 py-2.5 text-xs text-muted">
        <span>Synthetic benchmark and scripted model, 40 items</span>
        <Link href="/report?sample" className={cn("font-medium text-iris-fg hover:underline", FOCUS_RING)}>
          Open the full report →
        </Link>
      </figcaption>
    </figure>
  );
}

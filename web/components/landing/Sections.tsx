import Link from "next/link";
import type { ReactNode } from "react";

import { Reveal } from "../Reveal";
import { buttonClass, FOCUS_RING, StatusPill } from "../ui";

const WRAP = "mx-auto max-w-[1120px] px-5 sm:px-8";
const LINK = `font-medium text-iris-fg underline-offset-4 hover:underline ${FOCUS_RING}`;

function SectionTitle({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="max-w-2xl">
      <h2 className="font-display text-[1.875rem] leading-tight font-medium tracking-[-0.01em] text-fg">{title}</h2>
      {children && <p className="mt-3 text-[1.0625rem] leading-relaxed text-pretty text-secondary">{children}</p>}
    </div>
  );
}

const STEPS = [
  {
    title: "Ask the question as published",
    body: "Every prompt, raw response, parsed answer, token count, and setting is recorded, so each score can be traced back to an item.",
  },
  {
    title: "Ask it again, differently",
    body: "The options are shuffled so the answer changes letter, the labels are renamed (a → 1), and the template is rewritten. The correct answer never changes.",
  },
  {
    title: "Compare, with uncertainty",
    body: "Each item is compared with its own variants. A drop counts only if its 95% interval clears zero after multiple-testing correction.",
  },
];

export function HowItWorks() {
  return (
    <section className={`${WRAP} py-20`}>
      <SectionTitle title="How an audit works">
        A memorized benchmark looks like a capable model until you change something that should not
        matter. Veritas changes those things on purpose.
      </SectionTitle>
      <ol className="mt-12 grid gap-10 sm:grid-cols-3 sm:gap-8">
        {STEPS.map((step, index) => (
          <Reveal key={step.title} as="li" delay={index * 80} className="border-t border-line pt-5">
            <span className="font-display text-3xl text-faint">{index + 1}</span>
            <h3 className="mt-3 text-base font-semibold text-fg">{step.title}</h3>
            <p className="mt-2 text-[0.9375rem] leading-relaxed text-secondary">{step.body}</p>
          </Reveal>
        ))}
      </ol>
    </section>
  );
}

// The sample report's actual findings (web/fixtures/v2/sample_report.json).
const VERDICTS: Array<{ test: string; verdict: string; tone: "warn" | "neutral"; effect: string; ci: string }> = [
  { test: "Answer position", verdict: "dependence", tone: "warn", effect: "27.5", ci: "12.5 to 45.0" },
  { test: "All surface changes", verdict: "dependence", tone: "warn", effect: "18.3", ci: "6.7 to 30.0" },
  { test: "Prompt template", verdict: "inconclusive", tone: "neutral", effect: "0.0", ci: "−7.5 to 7.5" },
  { test: "Token likelihood", verdict: "not run", tone: "neutral", effect: "—", ci: "no log-probs" },
  { test: "Fresh-set transfer", verdict: "not run", tone: "neutral", effect: "—", ci: "no fresh set" },
];

export function ReportPreview() {
  return (
    <section className="border-y border-hairline bg-subtle">
      <div className={`${WRAP} grid gap-12 py-20 lg:grid-cols-[0.9fr_1.1fr] lg:items-center`}>
        <div>
          <SectionTitle title="Evidence, not accusations">
            A score drop is behavioral evidence of protocol dependence. It is not proof of
            contamination, and the report says so.
          </SectionTitle>
          <ul className="mt-8 space-y-4 text-[0.9375rem] leading-relaxed text-secondary">
            <li><span className="font-medium text-fg">A verdict per test</span>, with effect size, interval, and corrected p-value.</li>
            <li><span className="font-medium text-fg">Every item that flipped</span>, with the exact prompt and answer for each variant.</li>
            <li><span className="font-medium text-fg">Tests it could not run</span>, and the reason, instead of silence.</li>
            <li><span className="font-medium text-fg">A signed report.</span> Any edit after the run breaks the hash, and the viewer checks it.</li>
          </ul>
        </div>
        <Reveal className="overflow-x-auto rounded-xl border border-line bg-surface">
          <table className="w-full min-w-[480px] text-left text-sm">
            <caption className="border-b border-hairline px-5 py-3 text-left text-[0.8125rem] text-muted">
              Findings from the sample report: accuracy drop under variants, in points
            </caption>
            <thead className="text-xs text-muted">
              <tr>
                <th className="px-5 py-2.5 font-medium">Test</th>
                <th className="px-3 py-2.5 font-medium">Verdict</th>
                <th className="px-3 py-2.5 text-right font-medium">Drop</th>
                <th className="px-5 py-2.5 text-right font-medium">95% CI</th>
              </tr>
            </thead>
            <tbody>
              {VERDICTS.map((row) => (
                <tr key={row.test} className="border-t border-hairline">
                  <td className="px-5 py-3 text-fg">{row.test}</td>
                  <td className="px-3 py-3"><StatusPill tone={row.tone}>{row.verdict}</StatusPill></td>
                  <td className="tnum px-3 py-3 text-right font-mono text-fg">{row.effect}</td>
                  <td className="tnum px-5 py-3 text-right font-mono text-muted">{row.ci}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Reveal>
      </div>
    </section>
  );
}

const SURFACES = [
  {
    title: "In the browser",
    body: "Pick one of 8 public benchmarks and a model from 11 providers, including OpenAI, Anthropic, Gemini, and open-weight hosts. Your key is used once and never stored.",
    code: null,
    link: { href: "/run", label: "Open the runner" },
  },
  {
    title: "From the command line",
    body: "Private benchmarks, local Transformers or vLLM models, resumable caching, and the full detector set.",
    code: 'pip install "veritas-leakage[cli]"\nveritas audit --config audit.json \\\n  --out run/',
    link: { href: "/docs#run", label: "Read the docs" },
  },
  {
    title: "In CI",
    body: "Fail a build when the robustness gap exceeds your threshold, or when a report has been edited.",
    code: "veritas verify --report report.json\nveritas gate --report report.json \\\n  --max-delta 0.05",
    link: { href: "/docs#verify", label: "Gate and verify" },
  },
];

export function WhereToRun() {
  return (
    <section className={`${WRAP} pt-4 pb-20`}>
      <SectionTitle title="Run it where your model lives" />
      <div className="mt-10 grid gap-6 md:grid-cols-3">
        {SURFACES.map((surface, index) => (
          <Reveal key={surface.title} delay={index * 80} className="flex flex-col rounded-xl border border-line bg-surface p-6">
            <h3 className="text-base font-semibold text-fg">{surface.title}</h3>
            <p className="mt-2 text-[0.9375rem] leading-relaxed text-secondary">{surface.body}</p>
            {surface.code && (
              <pre className="mt-4 overflow-x-auto rounded-md bg-elevated px-3 py-2.5 font-mono text-[0.6875rem] leading-relaxed text-fg">{surface.code}</pre>
            )}
            <Link href={surface.link.href} className={`mt-auto pt-5 text-sm ${LINK}`}>
              {surface.link.label} →
            </Link>
          </Reveal>
        ))}
      </div>
      <p className="mt-8 max-w-3xl text-sm leading-relaxed text-muted">
        Built-in catalog: MMLU, MMLU-Pro, GPQA, ARC-Challenge, OpenBookQA, HellaSwag, CommonsenseQA,
        PIQA, WinoGrande, TruthfulQA, BoolQ, HumanEval, and SWE-bench Verified, each pinned to an
        upstream revision. Any JSONL benchmark works too.
      </p>
    </section>
  );
}

export function Closing() {
  return (
    <section className={`${WRAP} pb-8`}>
      <div className="flex flex-col gap-6 rounded-2xl border border-line bg-surface px-6 py-10 sm:px-10 md:flex-row md:items-center md:justify-between">
        <div className="max-w-xl">
          <h2 className="font-display text-2xl font-medium text-fg">See it on a real model in a few minutes.</h2>
          <p className="mt-2 text-[0.9375rem] leading-relaxed text-secondary">
            Twenty items and an API key are enough for a first look. The original biological leakage
            auditor is still available in the{" "}
            <Link href="/report/legacy" className={LINK}>legacy viewer</Link>.
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap gap-3">
          <Link href="/run" className={buttonClass("primary", "px-5 py-2.5")}>Run an audit</Link>
          <Link href="/docs" className={buttonClass("secondary", "px-5 py-2.5")}>Read the docs</Link>
        </div>
      </div>
    </section>
  );
}

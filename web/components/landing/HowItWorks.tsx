import { Eyebrow } from "../ui";

function Step({ n, title, body }: { n: string; title: string; body: string }) {
  return (
    <li className="flex flex-col gap-1.5">
      <span className="font-mono text-[0.75rem] text-iris-fg tnum">{n}</span>
      <h3 className="text-[0.9375rem] text-fg">{title}</h3>
      <p className="text-[0.8125rem] leading-relaxed text-secondary">{body}</p>
    </li>
  );
}

function Commit({ label, body }: { label: string; body: string }) {
  return (
    <div>
      <span className="font-mono text-[0.75rem] text-fg">{label}</span>
      <p className="mt-1 text-pretty text-[0.8125rem] leading-relaxed text-secondary">{body}</p>
    </div>
  );
}

export function HowItWorks() {
  return (
    <section id="how" className="mx-auto max-w-[1100px] scroll-mt-16 px-5 py-14 sm:px-8">
      <Eyebrow>one reproducible workflow</Eyebrow>
      <p className="mt-3 max-w-2xl text-pretty text-[0.9375rem] leading-relaxed text-secondary">
        Point Veritas at a benchmark and an API, local open-weight model, subprocess, or replayed
        response set. The same application service powers inspection, execution, and reporting.
      </p>

      <ol className="mt-8 grid gap-6 sm:grid-cols-3">
        <Step
          n="01"
          title="Evaluate the canonical set"
          body="Capture every prompt, raw response, parsed answer, token count, latency, model setting, and cache key."
        />
        <Step
          n="02"
          title="Stress-test the score"
          body="Apply seeded, validated prompt, template, choice-order, identifier, notation, and task-specific transformations."
        />
        <Step
          n="03"
          title="Map the evidence"
          body="Compare paired scores with uncertainty, detector findings, alternatives, unavailable evidence, and an audit hash."
        />
      </ol>

      <div className="mt-10 grid gap-x-10 gap-y-5 border-t border-hairline pt-6 sm:grid-cols-2">
        <Commit label="provider-neutral" body="HTTP APIs, vLLM, local Transformers, subprocesses, mocks, and replay" />
        <Commit label="private-aware" body="external transfer requires an explicit acknowledgement and redacted provenance" />
        <Commit label="resumable" body="content-addressed responses and staged checkpoints prevent duplicate inference" />
        <Commit label="evidence-first" body="effect sizes, uncertainty, assumptions, alternatives, and not-run outcomes stay visible" />
      </div>
    </section>
  );
}

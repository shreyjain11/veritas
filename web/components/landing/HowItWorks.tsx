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
      <Eyebrow>how it works</Eyebrow>
      <p className="mt-3 max-w-2xl text-pretty text-[0.9375rem] leading-relaxed text-secondary">
        Predictions in → audit out. Veritas works on predictions you already have, so it applies to
        a protein language model, a DNA CNN, a docking score, or a black-box API.
      </p>

      <ol className="mt-8 grid gap-6 sm:grid-cols-3">
        <Step
          n="01"
          title="Detect leakage"
          body="sequence (mmseqs) · family (Pfam / HMMER) · structural (foldseek, fold-level)"
        />
        <Step
          n="02"
          title="Re-score honestly"
          body="the metric recomputed on the de-leaked set, with bootstrap confidence intervals"
        />
        <Step
          n="03"
          title="Stratify & sign"
          body="performance by difficulty, plus an audit_hash over every number in the report"
        />
      </ol>

      <div className="mt-10 grid gap-x-10 gap-y-5 border-t border-hairline pt-6 sm:grid-cols-2">
        <Commit label="provenance" body="every number carries where it came from" />
        <Commit label="deterministic" body="byte-identical reports on the pinned platform" />
        <Commit label="honest CIs" body="uncertainty + disclosed limitations travel inside the report" />
        <Commit label="tamper-evident" body="re-verify the audit_hash yourself, in the browser" />
      </div>
    </section>
  );
}

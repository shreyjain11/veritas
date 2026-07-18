import { Reveal } from "../Reveal";
import { Eyebrow } from "../ui";

function Step({ n, title, body, delay = 0 }: { n: string; title: string; body: string; delay?: number }) {
  return (
    <Reveal as="li" delay={delay} className="flex flex-col gap-1.5">
      <span className="font-mono text-[0.75rem] text-iris-fg tnum">{n}</span>
      <h3 className="text-[0.9375rem] text-fg">{title}</h3>
      <p className="text-[0.8125rem] leading-relaxed text-secondary">{body}</p>
    </Reveal>
  );
}

function Commit({ label, body, delay = 0 }: { label: string; body: string; delay?: number }) {
  return (
    <Reveal delay={delay}>
      <span className="font-mono text-[0.75rem] text-fg">{label}</span>
      <p className="mt-1 text-pretty text-[0.8125rem] leading-relaxed text-secondary">{body}</p>
    </Reveal>
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
          delay={0}
        />
        <Step
          n="02"
          title="Re-score honestly"
          body="the metric recomputed on the de-leaked set, with bootstrap confidence intervals"
          delay={90}
        />
        <Step
          n="03"
          title="Stratify & sign"
          body="performance by difficulty, plus an audit_hash over every number in the report"
          delay={180}
        />
      </ol>

      <div className="mt-10 grid gap-x-10 gap-y-5 border-t border-hairline pt-6 sm:grid-cols-2">
        <Commit label="provenance" body="every number carries where it came from" delay={0} />
        <Commit label="deterministic" body="byte-identical reports on the pinned platform" delay={60} />
        <Commit
          label="honest CIs"
          body="uncertainty + disclosed limitations travel inside the report"
          delay={120}
        />
        <Commit label="tamper-evident" body="re-verify the audit_hash yourself, in the browser" delay={180} />
      </div>
    </section>
  );
}

import { Reveal } from "../Reveal";
import { Eyebrow } from "../ui";

const EVIDENCE = [
  {
    title: "Prompt and template dependence",
    body: "Measure whether a score survives meaning-preserving wording, formatting, and instruction-template changes.",
    tag: "paired variants",
  },
  {
    title: "Choice and position sensitivity",
    body: "Permute options and remap labels while preserving the correct answer and parent-item lineage.",
    tag: "mapping checked",
  },
  {
    title: "Exposure-consistent behavior",
    body: "Record exact, near-reference, likelihood, completion, and error-reproduction evidence only when requirements are met.",
    tag: "never proof alone",
  },
  {
    title: "Capability that transfers",
    body: "Use fresh, temporal, transformed, and distribution-shift controls to distinguish robustness from benchmark familiarity.",
    tag: "controls required",
  },
];

const BENCHMARKS = [
  "MMLU",
  "MMLU-Pro",
  "GPQA",
  "ARC-Challenge",
  "HellaSwag",
  "TruthfulQA",
  "HumanEval",
  "SWE-bench Verified",
];

export function Proof() {
  return (
    <section className="mx-auto max-w-[1100px] px-5 py-16 sm:px-8 sm:py-20">
      <Eyebrow>what Veritas maps</Eyebrow>
      <p className="mt-3 max-w-2xl text-pretty text-[0.9375rem] leading-relaxed text-secondary">
        A benchmark score is the starting point. The audit asks which explanations survive
        controlled comparisons and keeps conflicting or missing evidence visible.
      </p>
      <div className="mt-10 grid gap-x-12 gap-y-10 sm:grid-cols-2">
        {EVIDENCE.map((item, index) => (
          <Reveal key={item.title} as="article" delay={(index % 2) * 80} className="border-t border-hairline pt-5">
            <div className="flex items-baseline justify-between gap-3">
              <h3 className="text-[0.9375rem] text-fg">{item.title}</h3>
              <span className="shrink-0 font-mono text-[0.625rem] uppercase tracking-[0.06em] text-iris-fg">
                {item.tag}
              </span>
            </div>
            <p className="mt-4 text-pretty text-[0.8125rem] leading-relaxed text-secondary">
              {item.body}
            </p>
          </Reveal>
        ))}
      </div>
      <Reveal className="mt-12 border-t border-hairline pt-5">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <h3 className="text-[0.9375rem] text-fg">Built-in benchmark catalog</h3>
          <span className="font-mono text-[0.625rem] uppercase tracking-[0.06em] text-muted">
            plus JSONL custom sets
          </span>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {BENCHMARKS.map((name) => (
            <span
              key={name}
              className="rounded border border-line bg-surface/30 px-2.5 py-1 font-mono text-[0.6875rem] text-secondary"
            >
              {name}
            </span>
          ))}
        </div>
        <p className="mt-3 text-[0.8125rem] leading-relaxed text-muted">
          Presets preserve upstream source, split, revision, license, access constraints, and
          deterministic sampling in provenance.
        </p>
      </Reveal>
    </section>
  );
}

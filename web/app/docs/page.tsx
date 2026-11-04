import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

import { Footer } from "../../components/Footer";
import { Toc, type TocItem } from "../../components/docs/Toc";
import { Nav } from "../../components/landing/Nav";
import { FOCUS_RING } from "../../components/ui";

export const metadata: Metadata = {
  title: "Docs — Veritas",
  description:
    "Install Veritas, run a benchmark-integrity audit, and read its verdicts, intervals, and signed report.",
};

const TOC: TocItem[] = [
  { id: "overview", label: "Overview" },
  { id: "install", label: "Install" },
  { id: "run", label: "Run an audit" },
  { id: "browser", label: "Browser runner" },
  { id: "transformations", label: "What gets changed" },
  { id: "decisions", label: "How verdicts are decided" },
  { id: "verify", label: "Verify and gate" },
  { id: "privacy", label: "Private benchmarks" },
  { id: "interpretation", label: "Interpretation" },
  { id: "legacy", label: "Legacy biology" },
];

function H2({ id, children }: { id: string; children: ReactNode }) {
  return (
    <h2 id={id} className="mt-14 scroll-mt-20 font-display text-2xl font-medium tracking-[-0.01em] text-fg">
      {children}
    </h2>
  );
}

function P({ children }: { children: ReactNode }) {
  return <p className="mt-4 text-[0.9375rem] leading-[1.7] text-secondary">{children}</p>;
}

function C({ children }: { children: ReactNode }) {
  return <code className="rounded bg-elevated px-1.5 py-0.5 font-mono text-[0.85em] text-fg [overflow-wrap:anywhere]">{children}</code>;
}

function Code({ children }: { children: string }) {
  return (
    <pre className="mt-4 overflow-x-auto rounded-lg border border-hairline bg-surface px-4 py-3.5 font-mono text-[0.8125rem] leading-relaxed text-fg">
      {children}
    </pre>
  );
}

const LINK = `font-medium text-iris-fg underline-offset-4 hover:underline ${FOCUS_RING}`;

const TRANSFORMS: Array<[string, string, string]> = [
  ["choice_permutation", "Option texts move under the same labels, so the correct answer changes letter.", "valid"],
  ["choice_label_remap", "Labels become a fresh scheme (a, b, c → 1, 2, 3 or unused letters).", "valid"],
  ["formatting", "The prompt template and whitespace change; question and options do not.", "valid"],
  ["identifier", "Placeholder names are renamed consistently (x → beta, y → gamma).", "uncertain"],
];

export default function DocsPage() {
  return (
    <>
      <Nav />
      <div className="mx-auto max-w-[1120px] px-5 py-12 sm:px-8">
        <div className="grid grid-cols-[minmax(0,1fr)] gap-12 lg:grid-cols-[200px_minmax(0,1fr)]">
          <aside className="hidden lg:block">
            <div className="sticky top-24">
              <Toc items={TOC} />
            </div>
          </aside>

          <article className="min-w-0 max-w-[700px]">
            <h1 className="font-display text-[2.5rem] leading-tight font-medium tracking-[-0.015em] text-fg">
              Documentation
            </h1>
            <p className="mt-4 text-[1.0625rem] leading-relaxed text-secondary">
              How to run an audit, what Veritas changes about each question, and how to read the
              verdicts it reports.
            </p>

            <H2 id="overview">Overview</H2>
            <P>
              Veritas checks whether a model&apos;s benchmark performance survives changes that should
              not matter: moving the answer options, renaming their labels, rewriting the prompt
              template. It records every prompt and response, scores each item against its own
              variants, and writes a signed evidence package in JSON, Markdown, and HTML.
            </P>
            <P>
              Models are reached through four adapters: <C>openai_compatible</C> for any
              OpenAI-style HTTP endpoint, <C>vllm</C> for local servers, <C>huggingface_local</C> for
              direct Transformers inference with token log-probabilities, and <C>replay</C> for
              recorded responses. Responses can be cached so interrupted runs resume without paying
              twice.
            </P>

            <H2 id="install">Install</H2>
            <Code>{`python -m pip install "veritas-leakage[cli]"

# local Transformers inference and the named benchmark catalog
python -m pip install "veritas-leakage[cli,local-model,benchmarks]"

# from a checkout
uv sync --extra cli`}</Code>
            <P>
              Other extras: <C>mcp</C> exposes the tools to MCP clients, and <C>yaml</C> accepts YAML
              audit specs. List the built-in benchmarks with <C>veritas benchmarks</C>.
            </P>

            <H2 id="run">Run an audit</H2>
            <P>
              An audit spec names a benchmark, a model, the transformations to apply, and the detectors
              to run. <C>inspect</C> validates it and estimates requests and tokens before anything is
              sent.
            </P>
            <Code>{`{
  "benchmark": { "adapter": "catalog", "name": "mmlu", "limit": 100 },
  "model": {
    "id": "gpt-4o-mini",
    "adapter": "openai_compatible",
    "endpoint": "https://api.openai.com/v1",
    "generation": { "temperature": 0, "max_tokens": 16 }
  },
  "transformations": [
    { "type": "choice_permutation" },
    { "type": "choice_label_remap" },
    { "type": "formatting" }
  ],
  "detectors": [
    { "type": "perturbation" },
    { "type": "option_order" },
    { "type": "template_dependence" }
  ]
}`}</Code>
            <Code>{`export MODEL_API_KEY=...
veritas inspect --config audit.json
veritas audit --config audit.json --out audit-run/`}</Code>
            <P>
              Catalog benchmarks download from Hugging Face and need the <C>benchmarks</C> extra. For
              your own data, use <C>{`{"adapter": "jsonl", "path": "items.jsonl"}`}</C> with one item
              per line.
            </P>
            <P>
              The run prints the scores and each verdict, and writes <C>report.json</C>,{" "}
              <C>report.md</C>, and <C>report.html</C>. Open <C>report.json</C> in the{" "}
              <Link href="/report" className={LINK}>report viewer</Link> to see every item, response,
              and variant.
            </P>

            <H2 id="browser">Browser runner</H2>
            <P>
              The <Link href="/run" className={LINK}>browser runner</Link> audits up to 50 items from
              eight public multiple-choice benchmarks against OpenAI, Anthropic, Google Gemini, xAI,
              Mistral, DeepSeek, Together, Fireworks, Groq, OpenRouter, or Hugging Face. Each item is
              asked three ways: as published, with the options moved, and in a different template.
              Your key is sent once over HTTPS, used in server memory for that run, and never stored or
              written into the report. Reasoning models need a larger output budget, which the runner
              sets automatically.
            </P>

            <H2 id="transformations">What gets changed</H2>
            <P>
              Every variant keeps the meaning of the question and records its lineage: parent item,
              seed, parameters, and the answer key it is scored against. Variants that would not
              change anything are skipped.
            </P>
            <div className="mt-5 overflow-x-auto rounded-lg border border-line">
              <table className="w-full min-w-[520px] text-left text-sm">
                <thead className="bg-subtle text-xs text-muted">
                  <tr>
                    <th className="px-4 py-2.5 font-medium">Transformation</th>
                    <th className="px-4 py-2.5 font-medium">What changes</th>
                    <th className="px-4 py-2.5 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {TRANSFORMS.map(([name, what, status]) => (
                    <tr key={name} className="border-t border-hairline align-top">
                      <td className="px-4 py-3 font-mono text-[0.8125rem] text-fg">{name}</td>
                      <td className="px-4 py-3 text-secondary">{what}</td>
                      <td className="px-4 py-3 text-secondary">{status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <P>
              Only valid variants count toward the robust score. Uncertain ones are reported
              separately, because a rule cannot prove that <C>x</C> is a variable rather than a
              multiplication sign.
            </P>

            <H2 id="decisions">How verdicts are decided</H2>
            <P>
              Each paired detector compares an item&apos;s original correctness with its accuracy
              across valid variants, then reports the gap, a bootstrap 95% interval, a sign-flip
              permutation p-value, and that p-value corrected for multiple tests (Benjamini–Hochberg).
            </P>
            <ul className="mt-4 space-y-2 text-[0.9375rem] leading-relaxed text-secondary">
              <li><span className="font-medium text-fg">Dependence detected</span> when the gap is positive, its interval is above zero, and the corrected p-value is at most 0.05.</li>
              <li><span className="font-medium text-fg">Robust</span> when the interval&apos;s upper end is below 5 points: any drop is smaller than that.</li>
              <li><span className="font-medium text-fg">Inconclusive</span> otherwise, and always with fewer than 10 paired items.</li>
            </ul>
            <P>
              Failed or missing responses are excluded, never counted as wrong. Tests whose inputs are
              missing, such as token likelihood without log-probabilities, are reported as not run.
              Thresholds can be set per detector, for example{" "}
              <C>{`{"type": "option_order", "config": {"min_parent_items": 20}}`}</C>.
            </P>

            <H2 id="verify">Verify and gate</H2>
            <P>
              The audit hash covers the whole report. <C>verify</C> recomputes it and exits non-zero
              if anything changed after the run; the viewer runs the same check in your browser.{" "}
              <C>gate</C> fails a CI job when the robustness gap exceeds a threshold, or when no
              paired comparison exists.
            </P>
            <Code>{`veritas verify --report audit-run/report.json
veritas gate --report audit-run/report.json --max-delta 0.05`}</Code>

            <H2 id="privacy">Private benchmarks</H2>
            <P>
              Mark a benchmark <C>&quot;visibility&quot;: &quot;private&quot;</C> and Veritas refuses
              to send it to an external endpoint unless you pass{" "}
              <C>--acknowledge-external-transfer</C>. API keys are read from the environment and never
              written to reports or cache keys. Use a local adapter when a benchmark&apos;s terms
              forbid disclosure.
            </P>

            <H2 id="interpretation">Interpretation</H2>
            <P>
              &ldquo;Benchmark maxxing&rdquo; is useful shorthand, not a finding. A large drop under a
              valid transformation shows that a score depends on presentation; it does not show that
              the benchmark was in the training data. Claims of contamination need calibrated
              detectors, matched controls, and evidence that rules out the alternatives each finding
              lists.
            </P>

            <H2 id="legacy">Legacy biology</H2>
            <P>
              The sequence-based leakage auditor is still supported. Its reports open in the{" "}
              <Link href="/report/legacy" className={LINK}>legacy viewer</Link>, and its commands are
              documented in the{" "}
              <a href="https://github.com/shreyjain11/veritas/tree/main/docs" className={LINK}>reference docs</a>.
            </P>
          </article>
        </div>
        <Footer />
      </div>
    </>
  );
}

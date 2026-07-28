import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

import { Footer } from "../../components/Footer";
import { Toc, type TocItem } from "../../components/docs/Toc";
import { Nav } from "../../components/landing/Nav";

export const metadata: Metadata = {
  title: "Benchmark integrity docs — Veritas",
  description:
    "Run and interpret Veritas schema-v2 audits of frontier and open-weight model benchmark performance.",
};

const TOC: TocItem[] = [
  { id: "overview", label: "Overview" },
  { id: "workflow", label: "Workflow" },
  { id: "evidence", label: "Evidence" },
  { id: "statistics", label: "Statistics" },
  { id: "install", label: "Install" },
  { id: "run", label: "Run an audit" },
  { id: "privacy", label: "Privacy" },
  { id: "interpretation", label: "Interpretation" },
  { id: "legacy", label: "Legacy biology" },
];

function H2({ id, children }: { id: string; children: ReactNode }) {
  return (
    <h2 id={id} className="mt-12 scroll-mt-20 text-xl font-semibold tracking-tight text-fg first:mt-0">
      {children}
    </h2>
  );
}

function P({ children }: { children: ReactNode }) {
  return <p className="mt-3 text-[0.9375rem] leading-relaxed text-secondary">{children}</p>;
}

function C({ children }: { children: ReactNode }) {
  return <code className="rounded bg-elevated px-1 py-0.5 font-mono text-[0.85em] text-iris-fg">{children}</code>;
}

function Code({ children }: { children: string }) {
  return (
    <pre className="mt-4 overflow-x-auto rounded-md border border-hairline bg-subtle px-4 py-3 font-mono text-[0.8125rem] leading-relaxed text-secondary">
      {children}
    </pre>
  );
}

const DOC_LINK =
  "text-iris-fg underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-iris";

export default function DocsPage() {
  return (
    <>
      <Nav />
      <div className="mx-auto max-w-[1100px] px-5 py-10 sm:px-8">
        <div className="grid gap-10 lg:grid-cols-[1fr_220px]">
          <article className="order-2 max-w-[680px] lg:order-1">
            <p className="text-[0.6875rem] font-medium uppercase tracking-[0.08em] text-muted">documentation · schema v2</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-fg">Auditing benchmark integrity</h1>

            <H2 id="overview">Overview</H2>
            <P>
              Veritas checks whether a model&apos;s reported benchmark performance transfers beyond the
              exact evaluation protocol. It records prompts and responses, runs reproducible
              transformations and controls, computes paired uncertainty, and packages the evidence
              with provenance and a deterministic audit hash.
            </P>

            <H2 id="workflow">Workflow</H2>
            <Code>{`audit specification
  → validate benchmark + privacy choices
  → inspect request, token, and cost limits
  → evaluate canonical items
  → generate and validate transformed items
  → run available detectors and controls
  → compute paired statistics
  → write JSON + Markdown + HTML evidence package`}</Code>
            <P>
              Model adapters support replay, mock responses, OpenAI-compatible HTTP endpoints,
              vLLM-compatible servers, local Hugging Face Transformers, and custom subprocesses.
              Content-addressed caching makes interrupted runs resumable and includes model and
              generation settings in every cache key.
            </P>

            <H2 id="evidence">Evidence, not a verdict</H2>
            <P>
              Findings distinguish exact or near-reference exposure, semantic exposure, template
              and protocol dependence, choice or position sensitivity, evaluator exploitation,
              distribution shift, fresh-set transfer, legitimate capability, and inconclusive or
              unavailable evidence. Every detector declares its requirements and emits <C>not_run</C>
              when those requirements are absent.
            </P>

            <H2 id="statistics">Statistics</H2>
            <P>
              Score variants retain parent-item lineage. Comparisons use paired parent-item
              bootstrap intervals, permutation tests, and McNemar analyses where applicable, with
              clustered uncertainty and effect sizes. The configurable Benchmark Robustness Index
              is explicitly uncalibrated and must not be read as a probability of contamination.
            </P>

            <H2 id="install">Install</H2>
            <P>
              The package is not published on PyPI yet. Install from a local checkout; the second
              form adds direct local Transformers inference, the named benchmark catalog, and may install PyTorch.
            </P>
            <Code>{`python -m pip install -e "/absolute/path/to/veritas[cli]"
python -m pip install -e "/absolute/path/to/veritas[cli,local-model,benchmarks]"

# or, from the repository root
uv sync --extra cli --extra local-model --extra benchmarks

veritas benchmarks
veritas benchmarks mmlu`}</Code>

            <H2 id="run">Run an audit</H2>
            <Code>{`veritas inspect --config audit.yaml
veritas audit --config audit.yaml --out audit-run/

# uv-managed checkout
uv run veritas inspect --config examples/benchmark_integrity/open_weight_audit.json
uv run veritas audit \\
  --config examples/benchmark_integrity/open_weight_audit.json \\
  --out audit-run/`}</Code>
            <P>
              A catalog audit uses <C>{`benchmark: {adapter: catalog, name: mmlu, limit: 100}`}</C>.
              Presets currently cover MMLU, MMLU-Pro, ARC-Challenge, OpenBookQA, HellaSwag,
              CommonsenseQA, PIQA, WinoGrande, TruthfulQA, BoolQ, GPQA, HumanEval, and
              SWE-bench Verified. <C>inspect</C> validates the specification and estimates requests, tokens, cost, and
              private-data transfer before inference. The audit directory contains machine-readable
              data and human-readable reports. Open <C>report.json</C> in the{" "}
              <Link href="/report" className={DOC_LINK}>report viewer</Link> to inspect prompts,
              responses, transformations, score comparisons, evidence, unavailable tests, and provenance.
            </P>

            <H2 id="privacy">Private benchmarks</H2>
            <P>
              External adapters require an explicit per-run acknowledgement when the benchmark is
              marked private. Transfer choices are redacted in provenance, and secrets are excluded
              from reports and cache keys. Use a local adapter when benchmark terms prohibit external
              disclosure.
            </P>

            <H2 id="interpretation">Interpretation</H2>
            <P>
              “Benchmark maxxing” is useful shorthand, not a scientific outcome class. A large drop
              under a valid transformation can show protocol fragility; it does not by itself show
              training-set contamination. Strong claims require calibrated detectors, matched
              controls, alternatives, and uncertainty that support that specific claim.
            </P>

            <H2 id="legacy">Legacy biology</H2>
            <P>
              The sequence-based leakage auditor remains supported as a distinct legacy domain. Its
              existing report fixtures open in the <Link href="/report/legacy" className={DOC_LINK}>legacy v1 viewer</Link>.
              Command migration and the v2 schema are documented in the repository&apos;s
              <a href="https://github.com/shreyjain11/veritas/tree/frontend/viewer/docs" className={DOC_LINK}> reference docs</a>.
            </P>
          </article>

          <aside className="order-1 hidden lg:order-2 lg:block">
            <div className="sticky top-20">
              <Toc items={TOC} />
            </div>
          </aside>
        </div>
        <Footer />
      </div>
    </>
  );
}

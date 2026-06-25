import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

import { Footer } from "../../components/Footer";
import { Toc, type TocItem } from "../../components/docs/Toc";
import { Nav } from "../../components/landing/Nav";

export const metadata: Metadata = {
  title: "Docs — Veritas",
  description:
    "How Veritas audits sequence models for train/test leakage: the pipeline, the three detectors, the audit report, tamper-evidence, the locked results, and the disclosed limitations.",
};

const TOC: TocItem[] = [
  { id: "overview", label: "Overview" },
  { id: "how", label: "How it works" },
  { id: "detectors", label: "Detectors" },
  { id: "report", label: "The audit report" },
  { id: "kinds", label: "Report kinds" },
  { id: "tamper", label: "Tamper-evidence" },
  { id: "results", label: "Results" },
  { id: "limitations", label: "Guarantees & limitations" },
  { id: "usage", label: "Using Veritas" },
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

function Demo({ id, title, body }: { id: string; title: string; body: ReactNode }) {
  return (
    <Link
      href={`/report?report=${id}`}
      className="group block border-t border-hairline pt-3 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-iris"
    >
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-[0.875rem] text-fg transition-colors group-hover:text-iris-fg">{title}</span>
        <span className="font-mono text-[0.6875rem] text-iris-fg transition-transform group-hover:translate-x-0.5">
          open →
        </span>
      </div>
      <p className="mt-1 text-pretty text-[0.8125rem] leading-relaxed text-secondary">{body}</p>
    </Link>
  );
}

export default function DocsPage() {
  return (
    <>
      <Nav />
      <div className="mx-auto max-w-[1100px] px-5 py-10 sm:px-8">
        <div className="grid gap-10 lg:grid-cols-[1fr_220px]">
          <article className="order-2 max-w-[680px] lg:order-1">
            <p className="text-[0.6875rem] font-medium uppercase tracking-[0.08em] text-muted">
              documentation
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-fg">
              Veritas — leakage &amp; robustness auditing
            </h1>
            <P>
              Veritas is a model-agnostic, post-hoc auditor for sequence-based biological predictors.
              It answers one question honestly: <em>how much of a model&apos;s reported performance
              survives once train/test leakage is removed?</em> It never runs your model — it works on
              predictions you already have, so it applies equally to a protein language model, a DNA
              CNN, a docking score, or a black-box API.
            </P>

            <H2 id="overview">Overview</H2>
            <P>
              ML benchmarks leak: test examples are often homologous to training examples, so a model
              can score well by recognizing relatives rather than generalizing. Veritas detects that
              homology between an evaluation set and a reference set the model could have memorized,
              re-scores the metric on the de-leaked set, and reports the gap — the{" "}
              <C>reported → honest</C> collapse — with full provenance and a verifiable signature.
            </P>

            <H2 id="how">How it works</H2>
            <P>
              Predictions in → audit out. You give Veritas a benchmark (sequences + labels + a declared
              split, or a model + its reference set) and the model&apos;s per-example predictions. It
              then runs a three-step pipeline:
            </P>
            <Code>{`1. detect    cross-set homology  →  contamination graph
2. re-score  metric on the de-leaked set  +  bootstrap CIs
3. stratify  performance by difficulty  +  sign with audit_hash`}</Code>

            <H2 id="detectors">Detectors</H2>
            <P>
              Contamination is detected three ways, combined into one graph:
            </P>
            <ul className="mt-3 flex flex-col gap-2 text-[0.9375rem] leading-relaxed text-secondary">
              <li>
                <C>sequence</C> — identity search with MMseqs2 (protein or nucleotide), e.g. ≥30%
                identity over ≥50% coverage.
              </li>
              <li>
                <C>family</C> — shared profile-HMM family via Pfam / pyhmmer (protein-only).
              </li>
              <li>
                <C>structural</C> — fold similarity with foldseek TMalign (protein-only). This is{" "}
                <strong className="text-fg">fold-level</strong>, a more permissive signal than
                interface-level redundancy (e.g. iDist) — reported as its own quantity, not directly
                comparable.
              </li>
            </ul>

            <H2 id="report">The audit report</H2>
            <P>
              Every report is a single JSON document. The headline is three traced metrics —{" "}
              <C>reported</C>, <C>honest</C>, and their <C>delta</C> (the leakage), each with a bootstrap
              confidence interval. Alongside: a leakage summary (how many eval items were contaminated,
              by which detector), an optional stratification (performance by difficulty, with
              silent-failure flags), the provenance record, and the disclosed limitations. Every number
              is a <em>traced value</em> carrying where it came from.
            </P>

            <H2 id="kinds">Report kinds</H2>
            <P>
              Not every audit produces a reported-vs-honest metric, so a report declares its{" "}
              <C>report_kind</C>:
            </P>
            <ul className="mt-3 flex flex-col gap-2 text-[0.9375rem] leading-relaxed text-secondary">
              <li>
                <C>metric_audit</C> — the reported→honest collapse (a model was scored).
              </li>
              <li>
                <C>detection</C> — a leakage splits-matrix (split × detector) when no model was scored.
              </li>
              <li>
                <C>stratification</C> — a performance-by-difficulty curve.
              </li>
            </ul>
            <P>
              A validator forbids a detection or stratification report from carrying a (fabricated)
              metric — the no-fabrication guarantee is structural.
            </P>

            <H2 id="tamper">Tamper-evidence</H2>
            <P>
              Every report carries an <C>audit_hash</C>: a SHA-256 over its canonical content
              (everything except wall-clock stamps). The{" "}
              <Link href="/report" className="text-iris-fg underline-offset-4 hover:underline">
                report viewer
              </Link>{" "}
              recomputes that hash in your browser and shows a seal — <span className="text-iris-fg">verified</span>{" "}
              or <span className="text-danger-fg">mismatch</span>. Change one number in a report and the
              seal breaks. The viewer is as tamper-evident as the tool that produced the report.
            </P>

            <H2 id="results">Results</H2>
            <P>
              Five locked audits, each a real run on pinned data, guarded by a test — open any in the
              viewer:
            </P>
            <div className="mt-4 flex flex-col gap-2">
              <Demo
                id="r3_random"
                title="OverfitNN · random split"
                body="A maximally-overfit memorizer scores 0.165; its honest score is 0.018 — a statistical null. 89% was leakage."
              />
              <Demo
                id="r3_chr8_chr9"
                title="OverfitNN · chr8+chr9 holdout"
                body="Even a chromosome-aware split leaves residual leakage: 0.074 reported, 0.030 honest."
              />
              <Demo
                id="r2_reverse_complement"
                title="hashFrag · reverse-complement"
                body="On a naive genomic split, 80.8% of test sequences are exact reverse-complements of training sequences."
              />
              <Demo
                id="proteingym_msa_depth"
                title="ProteinGym · MSA depth"
                body="Variant-effect performance rises with alignment depth: 0.298 → 0.384 → 0.531."
              />
              <Demo
                id="ppi_interface"
                title="PPI · interface leakage"
                body="A 30%-identity sequence split leaves family + fold leakage the sequence detector can't see; a published control stays near zero."
              />
            </div>

            <H2 id="limitations">Guarantees &amp; limitations</H2>
            <P>
              Veritas states both. <strong className="text-fg">Guarantees:</strong> provenance on every
              number; byte-identical reports on the pinned platform (determinism); honest uncertainty —
              bootstrap CIs and the applicable limitations travel inside the report and are hashed into
              it.
            </P>
            <P>
              <strong className="text-fg">Limitations (measured, not assumed):</strong> confidence
              intervals use the percentile bootstrap, which under-covers at small n (~0.927 coverage at
              n=25; BCa not implemented). The MinHash prefilter is recall-oriented (~56% at the nominal
              Jaccard threshold) — disable it for an exhaustive comparison. Family/structural detectors
              are protein-only. Structural detection is fold-level, not interface-level. Results
              corroborate prior work qualitatively, not numerically.
            </P>

            <H2 id="usage">Using Veritas</H2>
            <P>
              Two install paths. <strong className="text-fg">Docker</strong> bakes in the
              version-pinned detector binaries (MMseqs2, Diamond, Foldseek, HMMER) plus the CLI, so it
              runs on any OS with no conda setup — the binaries match the versions stamped into the
              report&apos;s provenance:
            </P>
            <Code>{`docker pull ghcr.io/shreyjain11/veritas-leakage:latest
docker run --rm -v "$PWD:/work" ghcr.io/shreyjain11/veritas-leakage audit \\
  --sequences /work/eval.fasta --table /work/table.csv \\
  --reference /work/reference.fasta --config /work/config.json \\
  --metric accuracy --out /work/report.json
# …or build it yourself: docker build -t veritas-leakage .`}</Code>
            <P>
              Or install from PyPI with the <C>cli</C> extra and bring your own detector binaries
              (pinned in <C>environment.yml</C>):
            </P>
            <Code>{`pip install "veritas-leakage[cli]"
veritas audit --sequences eval.fasta --table table.csv \\
  --reference reference.fasta --config config.json --metric accuracy --out report.json`}</Code>
            <P>
              Full usage, the dataset manifests, and the reproducible demos live on{" "}
              <a
                href="https://github.com/shreyjain11/veritas"
                target="_blank"
                rel="noreferrer"
                className="text-iris-fg underline-offset-4 hover:underline"
              >
                GitHub
              </a>
              . This is an independent research project; every number on this site comes from a real
              run on pinned data, locked by a test — nothing is fabricated.
            </P>
          </article>

          <aside className="order-1 hidden lg:order-2 lg:block">
            <div className="lg:sticky lg:top-20">
              <Toc items={TOC} />
            </div>
          </aside>
        </div>
        <Footer />
      </div>
    </>
  );
}

"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

type Choice = { id: string; text: string };
type Item = {
  id: string;
  prompt: string | { role?: string; content?: unknown }[];
  expected_output: unknown;
  choices?: Choice[] | null;
  family_id?: string | null;
  metadata?: Record<string, unknown>;
};
type Response = {
  item_id: string;
  request?: { prompt?: unknown };
  raw_text: string;
  parsed_answer?: unknown;
  token_logprobs?: number[] | null;
  latency_ms?: number | null;
  token_count?: number | null;
  error?: string | null;
};
type Finding = {
  detector_id: string;
  hypothesis: string;
  status: string;
  strength: string;
  direction: string;
  effect_size?: number | null;
  ci?: [number, number] | null;
  p_value?: number | null;
  alternative_explanations?: string[];
  details?: Record<string, unknown>;
};
type V2Report = {
  schema_version: "2.0";
  audit_hash: string;
  benchmark: {
    id: string;
    version: string;
    task_type: string;
    visibility: string;
    items: Item[];
  };
  score: {
    reported_score?: number | null;
    canonical_reproduced_score?: number | null;
    robust_score?: number | null;
    fresh_score?: number | null;
    robustness_gap?: number | null;
    ci?: [number, number] | null;
  };
  findings: Finding[];
  evidence_matrix: {
    hypothesis: string;
    supporting: string[];
    contradicting: string[];
    unavailable: string[];
    confidence: string;
  }[];
  transformations: {
    family: string;
    parent_item_id: string;
    child_item_id: string;
    validation: string;
  }[];
  responses: Response[];
  limitations: string[];
  provenance: {
    benchmark_hash: string;
    audit_spec_hash: string;
    cache_state: string;
    privacy_warnings: string[];
    external_transfer_acknowledged: boolean;
    model: { id: string; revision?: string | null; adapter: string };
  };
};

function percent(value: number | null | undefined) {
  return value == null ? "Unavailable" : `${(value * 100).toFixed(1)}%`;
}

function promptText(prompt: Item["prompt"]) {
  if (typeof prompt === "string") return prompt;
  return prompt.map((message) => `${message.role ?? "message"}: ${String(message.content ?? "")}`).join("\n");
}

function answerText(value: unknown) {
  if (value == null) return "Unavailable";
  return typeof value === "string" ? value : JSON.stringify(value);
}

export function V2Viewer() {
  const [report, setReport] = useState<V2Report | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  async function load(file: File) {
    try {
      const parsed = JSON.parse(await file.text()) as Partial<V2Report>;
      if (
        parsed.schema_version !== "2.0" ||
        !parsed.benchmark ||
        !parsed.score ||
        !Array.isArray(parsed.findings) ||
        !Array.isArray(parsed.responses)
      ) {
        throw new Error("This is not a complete schema-v2 Veritas audit package.");
      }
      setReport(parsed as V2Report);
      setSelectedId(parsed.benchmark.items[0]?.id ?? null);
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not read the report.");
    }
  }

  const items = useMemo(() => {
    if (!report) return [];
    const normalized = query.trim().toLowerCase();
    return report.benchmark.items.filter((item) =>
      `${item.id} ${promptText(item.prompt)} ${item.family_id ?? ""}`.toLowerCase().includes(normalized),
    );
  }, [query, report]);
  const selected = report?.benchmark.items.find((item) => item.id === selectedId) ?? null;
  const selectedResponse = report?.responses.find((response) => response.item_id === selectedId);
  const selectedTransforms = report?.transformations.filter((value) => value.parent_item_id === selectedId) ?? [];

  return (
    <main className="mx-auto max-w-[1240px] px-5 py-10 sm:px-8">
      <header className="flex flex-wrap items-end justify-between gap-5 border-b border-hairline pb-8">
        <div>
          <Link href="/" className="font-mono text-sm text-iris-fg">veritas</Link>
          <p className="mt-3 text-sm text-muted">benchmark integrity report viewer · schema v2</p>
        </div>
        <label className="cursor-pointer rounded-md border border-iris/40 bg-iris-dim px-4 py-2 font-mono text-sm text-iris-fg">
          Load audit JSON
          <input className="sr-only" type="file" accept="application/json,.json" onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) void load(file);
          }} />
        </label>
      </header>

      {error && <p className="mt-5 rounded-md border border-danger/40 bg-danger-dim p-4 text-sm text-danger-fg">{error}</p>}
      {!report && <EmptyState />}
      {report && <div className="space-y-10 py-8">
        <AuditHeader report={report} />
        <ScoreCards report={report} />
        <ItemExplorer
          items={items}
          query={query}
          setQuery={setQuery}
          selected={selected}
          selectedResponse={selectedResponse}
          selectedTransforms={selectedTransforms}
          responses={report.responses}
          select={setSelectedId}
        />
        <EvidenceMatrix rows={report.evidence_matrix} />
        <Findings findings={report.findings} />
        <ReportFooter report={report} />
      </div>}
    </main>
  );
}

function EmptyState() {
  return <section className="py-20">
    <h1 className="text-3xl font-semibold text-fg">Open a benchmark-integrity audit.</h1>
    <p className="mt-4 max-w-xl text-secondary">Load the `report.json` created by `veritas audit` to inspect aggregate evidence and every benchmark prompt, response, transformation, and likelihood trace.</p>
    <Link className="mt-6 inline-block text-sm text-iris-fg underline" href="/report/legacy">Open a legacy biological report →</Link>
  </section>;
}

function AuditHeader({ report }: { report: V2Report }) {
  return <section>
    <p className="font-mono text-xs uppercase tracking-widest text-muted">{report.benchmark.visibility} · {report.benchmark.task_type}</p>
    <h1 className="mt-2 text-3xl font-semibold text-fg">{report.benchmark.id} <span className="font-mono text-base text-muted">v{report.benchmark.version}</span></h1>
    <p className="mt-3 font-mono text-xs text-muted">{report.provenance.model.id} · {report.provenance.model.adapter} · cache {report.provenance.cache_state}</p>
    <p className="mt-1 break-all font-mono text-[0.6875rem] text-faint">audit hash {report.audit_hash}</p>
  </section>;
}

function ScoreCards({ report }: { report: V2Report }) {
  const values = [
    ["Reported", report.score.reported_score],
    ["Canonical", report.score.canonical_reproduced_score],
    ["Robust", report.score.robust_score],
    ["Robustness gap", report.score.robustness_gap],
  ] as const;
  return <section>
    <div className="grid gap-3 sm:grid-cols-4">{values.map(([label, value]) => <div key={label} className="rounded-lg border border-line bg-surface/30 p-4"><p className="text-xs text-muted">{label}</p><p className="mt-2 font-mono text-2xl text-fg">{percent(value)}</p></div>)}</div>
    {report.score.ci && <p className="mt-2 text-xs text-muted">Paired robustness-gap interval: {percent(report.score.ci[0])} to {percent(report.score.ci[1])}</p>}
  </section>;
}

function ItemExplorer({ items, query, setQuery, selected, selectedResponse, selectedTransforms, responses, select }: {
  items: Item[];
  query: string;
  setQuery: (value: string) => void;
  selected: Item | null;
  selectedResponse: Response | undefined;
  selectedTransforms: V2Report["transformations"];
  responses: Response[];
  select: (id: string) => void;
}) {
  const correct = selected && selectedResponse
    ? answerText(selectedResponse.parsed_answer).trim() === answerText(selected.expected_output).trim()
    : null;
  return <section>
    <div className="flex flex-wrap items-end justify-between gap-3"><div><h2 className="text-lg text-fg">Prompt and response explorer</h2><p className="mt-1 text-sm text-muted">{items.length} matching canonical items</p></div><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search id, family, or prompt…" aria-label="Search benchmark items" className="w-full rounded-md border border-line bg-base px-3 py-2 text-sm text-fg outline-none focus:border-iris/60 sm:w-72" /></div>
    <div className="mt-4 grid overflow-hidden rounded-lg border border-line lg:grid-cols-[300px_1fr]">
      <div className="max-h-[560px] overflow-y-auto border-b border-line lg:border-b-0 lg:border-r">{items.map((item) => <button type="button" key={item.id} onClick={() => select(item.id)} className={`block w-full border-b border-hairline px-4 py-3 text-left transition-colors ${selected?.id === item.id ? "bg-iris-dim/40" : "hover:bg-elevated/50"}`}><span className="block font-mono text-xs text-fg">{item.id}</span><span className="mt-1 line-clamp-2 block text-xs leading-relaxed text-muted">{promptText(item.prompt)}</span></button>)}</div>
      <div className="min-h-80 p-5">{selected ? <div className="space-y-5">
        <div className="flex flex-wrap items-center gap-2"><span className="font-mono text-xs text-muted">{selected.id}</span>{correct != null && <span className={`rounded-full px-2 py-0.5 font-mono text-[0.6875rem] ${correct ? "bg-iris-dim text-iris-fg" : "bg-danger-dim text-danger-fg"}`}>{correct ? "correct" : "incorrect"}</span>}<span className="font-mono text-[0.6875rem] text-muted">{selectedTransforms.length} variants</span></div>
        <Field label="Prompt" value={promptText(selected.prompt)} />
        {selected.choices?.length ? <div><p className="text-xs uppercase tracking-wide text-muted">Choices</p><ul className="mt-2 space-y-1 font-mono text-sm text-secondary">{selected.choices.map(choice => <li key={choice.id}>{choice.id}. {choice.text}</li>)}</ul></div> : null}
        <div className="grid gap-4 sm:grid-cols-2"><Field label="Expected" value={answerText(selected.expected_output)} /><Field label="Parsed answer" value={answerText(selectedResponse?.parsed_answer)} /></div>
        <Field label="Raw model response" value={selectedResponse?.raw_text || selectedResponse?.error || "Unavailable"} />
        <div className="flex flex-wrap gap-4 font-mono text-xs text-muted"><span>{selectedResponse?.token_count ?? "—"} tokens</span><span>{selectedResponse?.latency_ms?.toFixed(0) ?? "—"} ms</span><span>{selectedResponse?.token_logprobs?.length ?? 0} log probabilities</span></div>
        {selectedTransforms.length ? <div><p className="text-xs uppercase tracking-wide text-muted">Transformed prompts and responses</p><div className="mt-2 space-y-2">{selectedTransforms.map(value => {
          const response = responses.find(candidate => candidate.item_id === value.child_item_id);
          return <details key={value.child_item_id} className="rounded border border-line p-3"><summary className="cursor-pointer font-mono text-xs text-secondary">{value.family} · {value.validation}</summary><div className="mt-3 space-y-3"><Field label="Variant prompt" value={answerText(response?.request?.prompt)} /><Field label="Variant response" value={response?.raw_text || response?.error || "Unavailable"} /></div></details>;
        })}</div></div> : null}
      </div> : <p className="text-sm text-muted">Select an item.</p>}</div>
    </div>
  </section>;
}

function Field({ label, value }: { label: string; value: string }) {
  return <div><p className="text-xs uppercase tracking-wide text-muted">{label}</p><pre className="mt-2 whitespace-pre-wrap break-words rounded-md bg-elevated/50 p-3 font-mono text-xs leading-relaxed text-secondary">{value}</pre></div>;
}

function EvidenceMatrix({ rows }: { rows: V2Report["evidence_matrix"] }) {
  return <section><h2 className="text-lg text-fg">Evidence matrix</h2><div className="mt-4 overflow-x-auto rounded-lg border border-line"><table className="w-full text-left text-sm"><thead className="bg-elevated text-muted"><tr><th className="p-3">Hypothesis</th><th className="p-3">Supporting</th><th className="p-3">Contradicting</th><th className="p-3">Unavailable</th><th className="p-3">Confidence</th></tr></thead><tbody>{rows.map(row => <tr key={row.hypothesis} className="border-t border-line"><td className="p-3 text-fg">{row.hypothesis}</td><td className="p-3 text-secondary">{row.supporting.join(", ") || "—"}</td><td className="p-3 text-secondary">{row.contradicting.join(", ") || "—"}</td><td className="p-3 text-secondary">{row.unavailable.join(", ") || "—"}</td><td className="p-3 font-mono text-xs text-iris-fg">{row.confidence}</td></tr>)}</tbody></table></div></section>;
}

function Findings({ findings }: { findings: Finding[] }) {
  return <section><h2 className="text-lg text-fg">Detector findings</h2><div className="mt-4 grid gap-3">{findings.map(finding => <article key={finding.detector_id} className="rounded-lg border border-line p-4"><div className="flex flex-wrap justify-between gap-2"><h3 className="font-mono text-sm text-fg">{finding.detector_id}</h3><span className="font-mono text-xs text-muted">{finding.status} · {finding.strength}</span></div><p className="mt-2 text-sm text-secondary">{finding.hypothesis}</p><div className="mt-2 flex flex-wrap gap-4 text-sm text-secondary"><span>Effect: {percent(finding.effect_size)}</span><span>p: {finding.p_value?.toPrecision(3) ?? "—"}</span>{finding.ci && <span>CI: {percent(finding.ci[0])}–{percent(finding.ci[1])}</span>}</div>{finding.alternative_explanations?.length ? <p className="mt-2 text-xs text-muted">Alternatives: {finding.alternative_explanations.join("; ")}</p> : null}</article>)}</div></section>;
}

function ReportFooter({ report }: { report: V2Report }) {
  return <section className="grid gap-6 sm:grid-cols-2"><div><h2 className="text-lg text-fg">Limitations</h2><ul className="mt-3 space-y-2 text-sm text-secondary">{report.limitations.map(value => <li key={value}>— {value}</li>)}</ul></div><div><h2 className="text-lg text-fg">Provenance</h2><div className="mt-3 space-y-2 break-all font-mono text-xs text-muted"><p>benchmark {report.provenance.benchmark_hash}</p><p>spec {report.provenance.audit_spec_hash}</p><p>external transfer acknowledged: {String(report.provenance.external_transfer_acknowledged)}</p>{report.provenance.privacy_warnings.map(value => <p key={value} className="text-warn-fg">{value}</p>)}</div></div></section>;
}

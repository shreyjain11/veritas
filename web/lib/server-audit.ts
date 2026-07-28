import { createHash } from "node:crypto";

import { createOpenAICompatible } from "@ai-sdk/openai-compatible";
import { generateText } from "ai";

import {
  type BrowserAuditReport,
  type BrowserAuditRequest,
  type BrowserBenchmarkId,
  type BrowserBenchmarkItem,
  type BrowserChoice,
  type BrowserModelResponse,
} from "./browser-audit";

const PROVIDER_URLS = {
  openai: "https://api.openai.com/v1",
  together: "https://api.together.xyz/v1",
  fireworks: "https://api.fireworks.ai/inference/v1",
  openrouter: "https://openrouter.ai/api/v1",
  groq: "https://api.groq.com/openai/v1",
  huggingface: "https://router.huggingface.co/v1",
} as const;

type CatalogSpec = {
  dataset: string;
  config: string;
  split: string;
  normalize: (row: Record<string, unknown>, index: number) => BrowserBenchmarkItem;
};

type DatasetServerRow = { row_idx: number; row: Record<string, unknown> };

const label = (index: number) => String.fromCharCode(97 + index);
const strings = (value: unknown): string[] => {
  if (!Array.isArray(value)) throw new Error("Benchmark row has invalid choices.");
  return value.map(String);
};
const choices = (values: string[], labels?: string[]): BrowserChoice[] =>
  values.map((text, index) => ({ id: labels?.[index]?.toLowerCase() ?? label(index), text }));
const item = (
  benchmark: BrowserBenchmarkId,
  index: number,
  prompt: unknown,
  itemChoices: BrowserChoice[],
  expected: string,
  metadata: Record<string, unknown> = {},
): BrowserBenchmarkItem => ({
  id: `${benchmark}:${index}`,
  prompt: String(prompt),
  expected_output: expected.toLowerCase(),
  choices: itemChoices,
  task_type: "multiple_choice",
  metadata,
});

function mappedChoices(value: unknown): { labels: string[]; texts: string[] } {
  if (!value || typeof value !== "object") throw new Error("Benchmark row has invalid choice mapping.");
  const map = value as Record<string, unknown>;
  return { labels: strings(map.label), texts: strings(map.text) };
}

const CATALOG: Record<BrowserBenchmarkId, CatalogSpec> = {
  mmlu: {
    dataset: "cais/mmlu",
    config: "all",
    split: "test",
    normalize: (row, index) => {
      const values = choices(strings(row.choices));
      return item("mmlu", index, row.question, values, values[Number(row.answer)]?.id ?? "", { subject: row.subject });
    },
  },
  arc_challenge: {
    dataset: "allenai/ai2_arc",
    config: "ARC-Challenge",
    split: "test",
    normalize: (row, index) => {
      const mapped = mappedChoices(row.choices);
      return item("arc_challenge", index, row.question, choices(mapped.texts, mapped.labels), String(row.answerKey));
    },
  },
  openbookqa: {
    dataset: "allenai/openbookqa",
    config: "main",
    split: "test",
    normalize: (row, index) => {
      const mapped = mappedChoices(row.choices);
      return item("openbookqa", index, row.question_stem, choices(mapped.texts, mapped.labels), String(row.answerKey));
    },
  },
  hellaswag: {
    dataset: "Rowan/hellaswag",
    config: "default",
    split: "validation",
    normalize: (row, index) => {
      const values = choices(strings(row.endings));
      return item("hellaswag", index, row.ctx, values, values[Number(row.label)]?.id ?? "", { activity: row.activity_label });
    },
  },
  commonsense_qa: {
    dataset: "tau/commonsense_qa",
    config: "default",
    split: "validation",
    normalize: (row, index) => {
      const mapped = mappedChoices(row.choices);
      return item("commonsense_qa", index, row.question, choices(mapped.texts, mapped.labels), String(row.answerKey));
    },
  },
  winogrande: {
    dataset: "allenai/winogrande",
    config: "winogrande_xl",
    split: "validation",
    normalize: (row, index) => item("winogrande", index, row.sentence, choices([String(row.option1), String(row.option2)]), Number(row.answer) === 1 ? "a" : "b"),
  },
  truthfulqa: {
    dataset: "truthfulqa/truthful_qa",
    config: "multiple_choice",
    split: "validation",
    normalize: (row, index) => {
      const targets = row.mc1_targets as Record<string, unknown>;
      const labels = strings(targets.labels).map(Number);
      const correct = labels.findIndex((value) => value === 1);
      const values = choices(strings(targets.choices));
      return item("truthfulqa", index, row.question, values, values[correct]?.id ?? "");
    },
  },
  boolq: {
    dataset: "google/boolq",
    config: "default",
    split: "validation",
    normalize: (row, index) => item("boolq", index, `${row.passage}\n\nQuestion: ${row.question}`, choices(["No", "Yes"]), row.answer ? "b" : "a"),
  },
};

function formatPrompt(entry: BrowserBenchmarkItem, mode: "canonical" | "choice_order" | "formatting"): string {
  const ordered = mode === "choice_order" ? [...entry.choices].reverse() : entry.choices;
  const lines = ordered.map((choice) => `${choice.id}. ${choice.text}`).join("\n");
  if (mode === "formatting") return `Select exactly one answer label.\n\nQUESTION\n${entry.prompt}\n\nOPTIONS\n${lines}\n\nLABEL:`;
  return `${entry.prompt}\n\nChoices:\n${lines}\n\nAnswer with the choice label only.`;
}

function parseAnswer(text: string, entry: BrowserBenchmarkItem): string | null {
  const ids = new Set(entry.choices.map((choice) => choice.id.toLowerCase()));
  const tokens = text.toLowerCase().match(/[a-z]+|\d+/g) ?? [];
  return tokens.find((token) => ids.has(token)) ?? null;
}

function stable(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    return `{${Object.keys(record).sort().map((key) => `${JSON.stringify(key)}:${stable(record[key])}`).join(",")}}`;
  }
  const encoded = JSON.stringify(value);
  return encoded === undefined ? "null" : encoded;
}

function hash(value: unknown): string {
  return createHash("sha256").update(stable(value)).digest("hex");
}

function timedSignal(signal: AbortSignal, timeout: number): AbortSignal {
  return AbortSignal.any([signal, AbortSignal.timeout(timeout)]);
}

async function loadBenchmark(request: BrowserAuditRequest, signal: AbortSignal): Promise<{ items: BrowserBenchmarkItem[]; revision: string }> {
  const spec = CATALOG[request.benchmark];
  const query = new URLSearchParams({ dataset: spec.dataset, config: spec.config, split: spec.split, offset: String(request.offset), length: String(request.itemCount) });
  const [rowsResponse, metadataResponse] = await Promise.all([
    fetch(`https://datasets-server.huggingface.co/rows?${query}`, { signal: timedSignal(signal, 30000) }),
    fetch(`https://huggingface.co/api/datasets/${spec.dataset}`, { signal: timedSignal(signal, 15000) }),
  ]);
  if (!rowsResponse.ok) throw new Error(`Benchmark host returned HTTP ${rowsResponse.status}.`);
  const body = (await rowsResponse.json()) as { rows?: DatasetServerRow[] };
  if (!body.rows?.length) throw new Error("The selected benchmark window returned no items.");
  const metadata = metadataResponse.ok ? ((await metadataResponse.json()) as { sha?: string }) : {};
  return {
    items: body.rows.map((entry) => spec.normalize(entry.row, entry.row_idx)),
    revision: metadata.sha ?? "hub-main-unresolved",
  };
}

async function mapConcurrent<T, R>(values: T[], limit: number, task: (value: T) => Promise<R>): Promise<R[]> {
  const output = new Array<R>(values.length);
  let cursor = 0;
  async function worker() {
    while (cursor < values.length) {
      const index = cursor++;
      const value = values[index];
      if (value !== undefined) output[index] = await task(value);
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, values.length) }, worker));
  return output;
}

type PromptJob = { item: BrowserBenchmarkItem; itemId: string; mode: "canonical" | "choice_order" | "formatting" };

export async function runBrowserAudit(
  request: BrowserAuditRequest,
  signal: AbortSignal = new AbortController().signal,
): Promise<BrowserAuditReport> {
  const loaded = await loadBenchmark(request, signal);
  const provider = createOpenAICompatible({
    name: request.provider,
    baseURL: PROVIDER_URLS[request.provider],
    apiKey: request.apiKey,
  });
  const model = provider.chatModel(request.model);
  const jobs: PromptJob[] = loaded.items.flatMap((entry) => [
    { item: entry, itemId: entry.id, mode: "canonical" },
    { item: entry, itemId: `${entry.id}::choice_order::browser_v1`, mode: "choice_order" },
    { item: entry, itemId: `${entry.id}::formatting::browser_v1`, mode: "formatting" },
  ]);
  const responses = await mapConcurrent(jobs, 4, async (job): Promise<BrowserModelResponse> => {
    const prompt = formatPrompt(job.item, job.mode);
    const started = performance.now();
    try {
      const result = await generateText({ model, prompt, temperature: 0, maxOutputTokens: 16, maxRetries: 2, timeout: 30000, abortSignal: signal });
      return {
        item_id: job.itemId,
        request: { prompt },
        normalized_request: { prompt },
        raw_text: result.text,
        parsed_answer: parseAnswer(result.text, job.item),
        token_logprobs: null,
        latency_ms: performance.now() - started,
        token_count: (result.totalUsage.inputTokens ?? 0) + (result.totalUsage.outputTokens ?? 0) || null,
        finish_reason: result.finishReason,
        attempt: 1,
        error: null,
        provenance: { adapter: "openai_compatible_byok", provider: request.provider },
      };
    } catch {
      return {
        item_id: job.itemId,
        request: { prompt },
        normalized_request: { prompt },
        raw_text: "",
        parsed_answer: null,
        token_logprobs: null,
        latency_ms: performance.now() - started,
        token_count: null,
        finish_reason: "error",
        attempt: 1,
        error: "Provider request failed. Verify the provider, model ID, key, balance, and model permissions.",
        provenance: { adapter: "openai_compatible_byok", provider: request.provider },
      };
    }
  });
  if (responses.every((response) => response.error)) throw new Error("Every model request failed. Verify the provider, model ID, key, balance, and model permissions.");

  const responseMap = new Map(responses.map((response) => [response.item_id, response]));
  const correct = (entry: BrowserBenchmarkItem, suffix = "") => responseMap.get(`${entry.id}${suffix}`)?.parsed_answer === entry.expected_output;
  const canonicalScore = loaded.items.filter((entry) => correct(entry)).length / loaded.items.length;
  const robustValues = loaded.items.map((entry) => Number(correct(entry, "::choice_order::browser_v1")) + Number(correct(entry, "::formatting::browser_v1")));
  const robustScore = robustValues.reduce((sum, value) => sum + value, 0) / (loaded.items.length * 2);
  const optionScore = loaded.items.filter((entry) => correct(entry, "::choice_order::browser_v1")).length / loaded.items.length;
  const templateScore = loaded.items.filter((entry) => correct(entry, "::formatting::browser_v1")).length / loaded.items.length;
  const gap = canonicalScore - robustScore;
  const transformations = loaded.items.flatMap((entry) => (["choice_order", "formatting"] as const).map((family) => ({
    id: `${entry.id}::${family}::browser_v1`,
    family,
    parent_item_id: entry.id,
    child_item_id: `${entry.id}::${family}::browser_v1`,
    parameters: { implementation: "browser_v1" },
    seed: 42,
    validation: "valid" as const,
    validation_method: "deterministic label-preserving transformation",
    expected_output: entry.expected_output,
    content_hash: hash(formatPrompt(entry, family)),
  })));
  const benchmarkHash = hash({ revision: loaded.revision, items: loaded.items });
  const specHash = hash({ provider: request.provider, model: request.model, benchmark: request.benchmark, itemCount: request.itemCount, offset: request.offset });
  const findings = [
    finding("perturbation", "surface-form dependence", gap, gap > 0),
    finding("option_order", "answer-position dependence", canonicalScore - optionScore, canonicalScore > optionScore),
    finding("template_dependence", "prompt-template dependence", canonicalScore - templateScore, canonicalScore > templateScore),
    {
      detector_id: "probability",
      detector_version: "browser_v1",
      hypothesis: "exposure evidence from calibrated token probabilities",
      status: "not_run",
      evidence_type: "token likelihood",
      direction: "inconclusive",
      strength: "unavailable",
      calibration: "not_calibrated",
      assumptions: ["The provider returns comparable token probabilities."],
      alternative_explanations: ["This BYOK browser adapter does not request log probabilities."],
    },
    {
      detector_id: "training_membership",
      detector_version: "browser_v1",
      hypothesis: "the exact benchmark item was present in model training",
      status: "not_run",
      evidence_type: "matched membership controls",
      direction: "inconclusive",
      strength: "unavailable",
      calibration: "not_calibrated",
      assumptions: ["Known member and non-member controls are supplied."],
      alternative_explanations: ["Capability, domain familiarity, or protocol sensitivity can produce the same behavior."],
    },
  ];
  const hashPayload = { benchmarkHash, specHash, responses: responses.map(({ item_id, raw_text, parsed_answer, error }) => ({ item_id, raw_text, parsed_answer, error })), findings };
  return {
    schema_version: "2.0",
    audit_hash: hash(hashPayload),
    benchmark: { id: request.benchmark, version: loaded.revision, task_type: "multiple_choice", visibility: "public", split: CATALOG[request.benchmark].split, items: loaded.items },
    score: { reported_score: null, canonical_reproduced_score: canonicalScore, robust_score: robustScore, fresh_score: null, robustness_gap: gap, fresh_generalization_gap: null, ci: null },
    findings,
    evidence_matrix: [
      { hypothesis: "protocol dependence", supporting: gap > 0 ? ["perturbation"] : [], contradicting: gap <= 0 ? ["perturbation"] : [], unavailable: [], confidence: gap > 0 ? "weak_indirect" : "inconclusive", assumptions: ["Transformations preserve intended task content."] },
      { hypothesis: "answer-position dependence", supporting: canonicalScore > optionScore ? ["option_order"] : [], contradicting: [], unavailable: [], confidence: canonicalScore > optionScore ? "weak_indirect" : "inconclusive", assumptions: ["Choice labels and correct-answer mapping remain valid."] },
      { hypothesis: "exact training membership", supporting: [], contradicting: [], unavailable: ["training_membership", "probability"], confidence: "unavailable", assumptions: ["Behavior alone cannot establish training membership."] },
    ],
    transformations,
    responses,
    limitations: [
      "This synchronous browser audit is capped at 20 parent items and two variants per item.",
      "Behavioral evidence cannot establish whether an item was present in model training.",
      "Token-likelihood, fresh-set, temporal, repeated-sampling, and external code-grader evidence are not run in this browser release.",
      "Provider keys are used in request memory and are not stored, cached, logged, or serialized into this report by Veritas.",
    ],
    provenance: {
      benchmark_hash: benchmarkHash,
      audit_spec_hash: specHash,
      seeds: { transformation: 42 },
      cache_state: "disabled",
      privacy_warnings: ["Benchmark prompts were transferred to the selected external provider."],
      external_transfer_acknowledged: true,
      package_version: "browser-v1",
      execution_surface: "veritas_browser_backend",
      secret_handling: "ephemeral_request_memory_only",
      model: { id: request.model, adapter: "openai_compatible_byok", provider: request.provider, revision: null, open_weight: request.provider !== "openai" },
    },
  };
}

function finding(detector: string, hypothesis: string, effect: number, supports: boolean): Record<string, unknown> {
  return {
    detector_id: detector,
    detector_version: "browser_v1",
    hypothesis,
    status: "complete",
    evidence_type: "paired accuracy",
    statistic: effect,
    effect_size: effect,
    ci: null,
    p_value: null,
    corrected_p_value: null,
    direction: supports ? "supports" : "inconclusive",
    strength: supports ? "weak_indirect" : "inconclusive",
    assumptions: ["Deterministic transformations preserve task meaning."],
    alternative_explanations: ["Ordinary distribution shift", "parser sensitivity", "provider nondeterminism"],
    calibration: "not_calibrated",
    item_ids: [],
    details: {},
  };
}

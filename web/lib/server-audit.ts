import { createOpenAICompatible } from "@ai-sdk/openai-compatible";
import { generateText } from "ai";

import {
  benjaminiHochberg,
  classify,
  evidenceMatrix,
  formatPrompt,
  isReasoningModel,
  pairedStats,
  parseAnswer,
  permuteChoices,
  type PairedStats,
  type Template,
} from "./audit-logic";
import {
  BROWSER_PROVIDERS,
  MAX_BROWSER_ITEMS,
  type BrowserAuditReport,
  type BrowserAuditRequest,
  type BrowserBenchmarkId,
  type BrowserBenchmarkItem,
  type BrowserChoice,
  type BrowserModelResponse,
} from "./browser-audit";
import { canonicalV2Json, v2ReportHash } from "./v2-hash";

const PROVIDER_URLS: Record<BrowserAuditRequest["provider"], string> = {
  openai: "https://api.openai.com/v1",
  anthropic: "https://api.anthropic.com/v1",
  google: "https://generativelanguage.googleapis.com/v1beta/openai",
  xai: "https://api.x.ai/v1",
  mistral: "https://api.mistral.ai/v1",
  deepseek: "https://api.deepseek.com/v1",
  together: "https://api.together.xyz/v1",
  fireworks: "https://api.fireworks.ai/inference/v1",
  openrouter: "https://openrouter.ai/api/v1",
  groq: "https://api.groq.com/openai/v1",
  huggingface: "https://router.huggingface.co/v1",
};

const IMPLEMENTATION = "browser_v2";
const SEED = 42;
const CONCURRENCY = 6;
/** Stop starting new requests here so the function returns before the platform limit. */
export const TIME_BUDGET_MS = 240_000;

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
  prompt: String(prompt ?? "").trim(),
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

/** An item is usable when it has ≥2 distinct options and its key names one of them. */
function usable(entry: BrowserBenchmarkItem): boolean {
  const texts = new Set(entry.choices.map((choice) => choice.text.trim().toLowerCase()));
  return (
    entry.prompt.length > 0 &&
    entry.choices.length >= 2 &&
    texts.size === entry.choices.length &&
    entry.choices.some((choice) => choice.id === entry.expected_output)
  );
}

async function sha256(value: unknown): Promise<string> {
  const digest = await globalThis.crypto.subtle.digest("SHA-256", new TextEncoder().encode(canonicalV2Json(value)));
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function timedSignal(signal: AbortSignal, timeout: number): AbortSignal {
  return AbortSignal.any([signal, AbortSignal.timeout(timeout)]);
}

export type AuditDependencies = { fetch: typeof globalThis.fetch; now: () => number };

async function loadBenchmark(
  request: BrowserAuditRequest,
  signal: AbortSignal,
  fetcher: typeof globalThis.fetch,
): Promise<{ items: BrowserBenchmarkItem[]; skipped: number; revision: string }> {
  const spec = CATALOG[request.benchmark];
  const query = new URLSearchParams({ dataset: spec.dataset, config: spec.config, split: spec.split, offset: String(request.offset), length: String(request.itemCount) });
  const [rowsResponse, metadataResponse] = await Promise.all([
    fetcher(`https://datasets-server.huggingface.co/rows?${query}`, { signal: timedSignal(signal, 30000) }).catch((cause: unknown) => {
      if (signal.aborted) throw cause;
      throw new Error("Could not reach the benchmark host (Hugging Face datasets server). It may be down or rate-limiting; try again in a minute.");
    }),
    fetcher(`https://huggingface.co/api/datasets/${spec.dataset}`, { signal: timedSignal(signal, 15000) }).catch(() => null),
  ]);
  if (!rowsResponse.ok) {
    throw new Error(`The benchmark host returned HTTP ${rowsResponse.status}. It may be busy; try again in a minute.`);
  }
  const body = (await rowsResponse.json()) as { rows?: DatasetServerRow[] };
  if (!body.rows?.length) throw new Error("The selected benchmark window returned no items. Try a smaller offset.");
  const metadata = metadataResponse?.ok ? ((await metadataResponse.json()) as { sha?: string }) : {};
  const normalized = body.rows.flatMap((entry) => {
    try {
      return [spec.normalize(entry.row, entry.row_idx)];
    } catch {
      return [];
    }
  });
  const items = normalized.filter(usable);
  if (!items.length) throw new Error("No usable items in this benchmark window. Try a different offset.");
  return { items, skipped: body.rows.length - items.length, revision: metadata.sha ?? "hub-main-unresolved" };
}

async function mapConcurrent<T, R>(values: T[], limit: number, task: (value: T) => Promise<R>): Promise<R[]> {
  const output = new Array<R>(values.length);
  let cursor = 0;
  async function worker() {
    while (cursor < values.length) {
      const index = cursor++;
      output[index] = await task(values[index]!);
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, values.length) }, worker));
  return output;
}

type Family = "choice_order" | "formatting";
type PromptJob = { itemId: string; prompt: string; expected: string; choices: BrowserChoice[]; parent: BrowserBenchmarkItem; family: Family | null; parameters: Record<string, unknown> };

function jobsFor(entry: BrowserBenchmarkItem): PromptJob[] {
  const permuted = permuteChoices(entry);
  const formatted: Template = "qa_block";
  return [
    { itemId: entry.id, prompt: formatPrompt(entry), expected: entry.expected_output, choices: entry.choices, parent: entry, family: null, parameters: {} },
    {
      itemId: `${entry.id}::choice_order::${IMPLEMENTATION}`,
      prompt: formatPrompt({ prompt: entry.prompt, choices: permuted.choices }),
      expected: permuted.expected,
      choices: permuted.choices,
      parent: entry,
      family: "choice_order",
      parameters: { implementation: IMPLEMENTATION, rotation: permuted.shift, answer_moved_from: entry.expected_output, answer_moved_to: permuted.expected },
    },
    {
      itemId: `${entry.id}::formatting::${IMPLEMENTATION}`,
      prompt: formatPrompt(entry, formatted),
      expected: entry.expected_output,
      choices: entry.choices,
      parent: entry,
      family: "formatting",
      parameters: { implementation: IMPLEMENTATION, template: formatted },
    },
  ];
}

function errorMessage(error: unknown): string {
  // generateText wraps exhausted retries in a RetryError; the HTTP detail is on lastError.
  const cause = typeof error === "object" && error && "lastError" in error ? (error as { lastError: unknown }).lastError : error;
  const status = typeof cause === "object" && cause && "statusCode" in cause ? Number((cause as { statusCode: unknown }).statusCode) : null;
  if (status === 401 || status === 403) return `Provider rejected the key (HTTP ${status}). Check the key and its model permissions.`;
  if (status === 404) return "Provider returned HTTP 404: the model ID was not found for this provider.";
  if (status === 429) return "Provider rate limit (HTTP 429) persisted after retries.";
  if (status === 400) return "Provider rejected the request (HTTP 400). The model may not support chat completions or these parameters.";
  if (status) return `Provider request failed (HTTP ${status}).`;
  if (cause instanceof Error && /timeout|aborted/i.test(cause.name + cause.message)) return "Provider request timed out.";
  return "Provider request failed. Verify the provider, model ID, key, balance, and model permissions.";
}

export async function runBrowserAudit(
  request: BrowserAuditRequest,
  signal: AbortSignal = new AbortController().signal,
  deps: AuditDependencies = { fetch: globalThis.fetch, now: () => performance.now() },
): Promise<BrowserAuditReport> {
  const startedAt = deps.now();
  const loaded = await loadBenchmark(request, signal, deps.fetch);
  const reasoning = isReasoningModel(request.model);
  const provider = createOpenAICompatible({
    name: request.provider,
    baseURL: PROVIDER_URLS[request.provider],
    apiKey: request.apiKey,
    fetch: deps.fetch,
    // OpenAI's current models take max_completion_tokens, and reasoning models reject a
    // non-default temperature; other compatible providers accept the standard body.
    transformRequestBody:
      request.provider === "openai"
        ? (body) => {
            const { max_tokens: maxTokens, temperature, ...rest } = body as Record<string, unknown>;
            return { ...rest, max_completion_tokens: maxTokens, ...(reasoning ? {} : { temperature }) };
          }
        : undefined,
  });
  const model = provider.chatModel(request.model);
  const jobs = loaded.items.flatMap(jobsFor);
  const requestTimeout = request.maxOutputTokens > 256 ? 120_000 : 30_000;

  const responses = await mapConcurrent(jobs, CONCURRENCY, async (job): Promise<BrowserModelResponse> => {
    const record = { prompt: job.prompt, max_output_tokens: request.maxOutputTokens };
    const base = { item_id: job.itemId, request: record, normalized_request: record, token_logprobs: null, attempt: 1, provenance: { adapter: "openai_compatible_byok", provider: request.provider } } as const;
    if (deps.now() - startedAt > TIME_BUDGET_MS) {
      return { ...base, raw_text: "", parsed_answer: null, latency_ms: 0, token_count: null, finish_reason: "skipped", error: "Skipped: the hosted run's time budget was exhausted." };
    }
    const started = deps.now();
    try {
      const result = await generateText({
        model,
        prompt: job.prompt,
        temperature: reasoning ? undefined : 0,
        maxOutputTokens: request.maxOutputTokens,
        maxRetries: 2,
        timeout: requestTimeout,
        abortSignal: signal,
      });
      return {
        ...base,
        raw_text: result.text,
        parsed_answer: parseAnswer(result.text, job.choices),
        latency_ms: deps.now() - started,
        token_count: (result.totalUsage.inputTokens ?? 0) + (result.totalUsage.outputTokens ?? 0) || null,
        finish_reason: result.finishReason,
        error: null,
      };
    } catch (cause) {
      if (signal.aborted) throw cause;
      return { ...base, raw_text: "", parsed_answer: null, latency_ms: deps.now() - started, token_count: null, finish_reason: "error", error: errorMessage(cause) };
    }
  });
  if (responses.every((response) => response.error)) {
    throw new Error(responses[0]?.error ?? "Every model request failed. Verify the provider, model ID, key, balance, and model permissions.");
  }

  // -- scoring: errored responses are excluded, never counted as wrong ----------------
  const byId = new Map(responses.map((response) => [response.item_id, response]));
  const outcome = (job: PromptJob): number | null => {
    const response = byId.get(job.itemId);
    if (!response || response.error) return null;
    return response.parsed_answer === job.expected ? 1 : 0;
  };
  const canonicalJobs = jobs.filter((job) => job.family === null);
  const canonicalOutcomes = new Map(canonicalJobs.map((job) => [job.parent.id, outcome(job)]));
  const scored = [...canonicalOutcomes.values()].filter((value): value is number => value !== null);
  const canonicalScore = scored.length ? scored.reduce((sum, value) => sum + value, 0) / scored.length : null;

  const paired = (families: Family[]) => {
    const left: number[] = [];
    const right: number[] = [];
    let errored = 0;
    for (const entry of loaded.items) {
      const base = canonicalOutcomes.get(entry.id);
      const values = jobs
        .filter((job) => job.parent.id === entry.id && job.family && families.includes(job.family))
        .map(outcome);
      errored += values.filter((value) => value === null).length;
      const valid = values.filter((value): value is number => value !== null);
      if (base == null || !valid.length) continue;
      left.push(base);
      right.push(valid.reduce((sum, value) => sum + value, 0) / valid.length);
    }
    return { stats: pairedStats(left, right, SEED), errored };
  };
  const detectors: Array<{ id: string; hypothesis: string; families: Family[] }> = [
    { id: "perturbation", hypothesis: "benchmark-template overfitting or surface-form dependence", families: ["choice_order", "formatting"] },
    { id: "option_order", hypothesis: "answer-position or label-token dependence", families: ["choice_order"] },
    { id: "template_dependence", hypothesis: "benchmark-template or prompt-protocol dependence", families: ["formatting"] },
  ];
  const results = detectors.map((detector) => ({ ...detector, ...paired(detector.families) }));
  const tested = results.filter((result): result is typeof result & { stats: PairedStats } => result.stats !== null);
  const corrected = benjaminiHochberg(tested.map((result) => result.stats.permutation_p_value));
  const findings: Array<Record<string, unknown>> = results.map((result) => {
    if (!result.stats) return notRun(result.id, result.hypothesis, "no scorable canonical/variant pairs", "Every paired response errored.");
    const correctedP = corrected[tested.indexOf(result as (typeof tested)[number])]!;
    const verdict = classify(result.stats, correctedP);
    return {
      detector_id: result.id,
      detector_version: IMPLEMENTATION,
      hypothesis: result.hypothesis,
      status: "complete",
      evidence_type: "paired parent-item accuracy (canonical minus validated variants)",
      statistic: result.stats.gap,
      effect_size: result.stats.gap,
      ci: result.stats.ci,
      p_value: result.stats.permutation_p_value,
      corrected_p_value: correctedP,
      direction: verdict.direction,
      strength: verdict.strength,
      assumptions: ["Deterministic transformations preserve task meaning."],
      alternative_explanations: ["ordinary distribution shift", "parser sensitivity", "provider nondeterminism"],
      calibration: "paired sign-flip permutation test; Benjamini-Hochberg across findings",
      item_ids: [],
      details: { ...result.stats, errored_variant_count: result.errored, decision_rule: verdict.rule },
    };
  });
  findings.push(
    notRun("probability", "exposure evidence from token probabilities", "token likelihood", "This BYOK browser adapter does not request log probabilities.", ["The provider returns comparable token probabilities."]),
    notRun("training_membership", "the exact benchmark item was present in model training", "matched membership controls", "Capability, domain familiarity, or protocol sensitivity can produce the same behavior.", ["Known member and non-member controls are supplied."]),
  );
  const overall = results[0]!.stats;

  const transformations = await Promise.all(
    jobs
      .filter((job) => job.family !== null)
      .map(async (job) => ({
        id: `${job.family}:${job.itemId}`,
        family: job.family as string,
        parent_item_id: job.parent.id,
        child_item_id: job.itemId,
        parameters: job.parameters,
        seed: SEED,
        validation: "valid" as const,
        validation_method: job.family === "choice_order" ? "deterministic option-text rotation under positional labels" : "prompt-template change; task text and options preserved",
        expected_output: job.expected,
        content_hash: await sha256({ prompt: job.prompt, expected: job.expected }),
      })),
  );
  const failed = responses.filter((response) => response.error).length;
  const limitations = [
    `This hosted audit is capped at ${MAX_BROWSER_ITEMS} parent items and two validated variants per item; use the CLI for larger, cached runs.`,
    "Behavioral evidence cannot establish whether an item was present in model training.",
    "Token-likelihood, fresh-set, temporal, repeated-sampling, and external code-grader evidence are not run in this browser release.",
    "Provider keys are used in request memory and are not stored, cached, logged, or serialized into this report by Veritas.",
  ];
  if (failed) limitations.push(`${failed} request(s) failed or were skipped and were excluded from scoring rather than counted as wrong.`);
  if (loaded.skipped) limitations.push(`${loaded.skipped} row(s) in the window were malformed (duplicate options or a missing answer key) and were skipped.`);
  if (overall && overall.parent_item_count < 10) limitations.push(`Only ${overall.parent_item_count} paired item(s): paired findings stay inconclusive below 10; audit more items for a decision.`);

  const providerInfo = BROWSER_PROVIDERS.find((entry) => entry.id === request.provider);
  const benchmarkHash = await sha256({ revision: loaded.revision, items: loaded.items });
  const specHash = await sha256({ provider: request.provider, model: request.model, benchmark: request.benchmark, itemCount: request.itemCount, offset: request.offset, maxOutputTokens: request.maxOutputTokens, implementation: IMPLEMENTATION });
  const report: BrowserAuditReport = {
    schema_version: "2.0",
    audit_hash: "",
    benchmark: { id: request.benchmark, version: loaded.revision, task_type: "multiple_choice", visibility: "public", split: CATALOG[request.benchmark].split, items: loaded.items },
    score: {
      reported_score: null,
      canonical_reproduced_score: canonicalScore,
      robust_score: overall?.transformed_score ?? null,
      fresh_score: null,
      robustness_gap: overall?.gap ?? null,
      fresh_generalization_gap: null,
      ci: overall?.ci ?? null,
    },
    findings,
    evidence_matrix: evidenceMatrix(findings as never, [
      ["template overfitting", ["perturbation", "template_dependence"]],
      ["protocol dependence", ["template_dependence", "perturbation"]],
      ["answer-position dependence", ["option_order"]],
      ["exact training membership", ["training_membership", "probability"]],
    ]),
    transformations,
    responses,
    limitations,
    provenance: {
      benchmark_hash: benchmarkHash,
      audit_spec_hash: specHash,
      seeds: { transformation: SEED, statistics: SEED },
      cache_state: "disabled",
      privacy_warnings: ["Benchmark prompts were transferred to the selected external provider."],
      external_transfer_acknowledged: true,
      package_version: IMPLEMENTATION,
      execution_surface: "veritas_browser_backend",
      secret_handling: "ephemeral_request_memory_only",
      model: { id: request.model, adapter: "openai_compatible_byok", provider: request.provider, revision: null, open_weight: providerInfo?.openWeight ?? null, max_output_tokens: request.maxOutputTokens },
    },
  };
  report.audit_hash = await v2ReportHash(report as unknown as Record<string, unknown>);
  return report;
}

function notRun(detector: string, hypothesis: string, evidenceType: string, reason: string, assumptions: string[] = []): Record<string, unknown> {
  return {
    detector_id: detector,
    detector_version: IMPLEMENTATION,
    hypothesis,
    status: "not_run",
    evidence_type: evidenceType,
    statistic: null,
    effect_size: null,
    ci: null,
    p_value: null,
    corrected_p_value: null,
    direction: "inconclusive",
    strength: "unavailable",
    assumptions,
    alternative_explanations: [reason],
    calibration: "not_calibrated",
    item_ids: [],
    details: {},
  };
}

export type BrowserProviderId =
  | "openai"
  | "together"
  | "fireworks"
  | "openrouter"
  | "groq"
  | "huggingface";

export type BrowserBenchmarkId =
  | "mmlu"
  | "arc_challenge"
  | "openbookqa"
  | "hellaswag"
  | "commonsense_qa"
  | "winogrande"
  | "truthfulqa"
  | "boolq";

export type BrowserAuditRequest = {
  provider: BrowserProviderId;
  apiKey: string;
  model: string;
  benchmark: BrowserBenchmarkId;
  itemCount: number;
  offset: number;
  acknowledgeExternalTransfer: boolean;
};

export type BrowserChoice = { id: string; text: string };

export type BrowserBenchmarkItem = {
  id: string;
  prompt: string;
  expected_output: string;
  choices: BrowserChoice[];
  task_type: "multiple_choice";
  family_id?: string;
  metadata: Record<string, unknown>;
};

export type BrowserModelResponse = {
  item_id: string;
  request: { prompt: string };
  normalized_request: { prompt: string };
  raw_text: string;
  parsed_answer: string | null;
  token_logprobs: null;
  latency_ms: number;
  token_count: number | null;
  finish_reason: string;
  attempt: number;
  error: string | null;
  provenance: { adapter: string; provider: BrowserProviderId };
};

export type BrowserAuditReport = {
  schema_version: "2.0";
  audit_hash: string;
  benchmark: {
    id: BrowserBenchmarkId;
    version: string;
    task_type: "multiple_choice";
    visibility: "public";
    split: string;
    items: BrowserBenchmarkItem[];
  };
  score: {
    reported_score: null;
    canonical_reproduced_score: number;
    robust_score: number;
    fresh_score: null;
    robustness_gap: number;
    fresh_generalization_gap: null;
    ci: null;
  };
  findings: Array<Record<string, unknown>>;
  evidence_matrix: Array<{
    hypothesis: string;
    supporting: string[];
    contradicting: string[];
    unavailable: string[];
    confidence: string;
    assumptions: string[];
  }>;
  transformations: Array<{
    id: string;
    family: string;
    parent_item_id: string;
    child_item_id: string;
    parameters: Record<string, unknown>;
    seed: number;
    validation: "valid";
    validation_method: string;
    expected_output: string;
    content_hash: string;
  }>;
  responses: BrowserModelResponse[];
  limitations: string[];
  provenance: {
    benchmark_hash: string;
    audit_spec_hash: string;
    seeds: Record<string, number>;
    cache_state: "disabled";
    privacy_warnings: string[];
    external_transfer_acknowledged: true;
    package_version: string;
    execution_surface: "veritas_browser_backend";
    secret_handling: "ephemeral_request_memory_only";
    model: {
      id: string;
      adapter: "openai_compatible_byok";
      provider: BrowserProviderId;
      revision: null;
      open_weight: boolean;
    };
  };
};

export const BROWSER_PROVIDERS: ReadonlyArray<{
  id: BrowserProviderId;
  name: string;
  description: string;
}> = [
  { id: "openai", name: "OpenAI", description: "OpenAI API key" },
  { id: "together", name: "Together AI", description: "Hosted open-weight models" },
  { id: "fireworks", name: "Fireworks AI", description: "Hosted open-weight models" },
  { id: "openrouter", name: "OpenRouter", description: "Multi-provider model access" },
  { id: "groq", name: "Groq", description: "Fast hosted open-weight inference" },
  { id: "huggingface", name: "Hugging Face", description: "Inference Providers router" },
];

export const BROWSER_BENCHMARKS: ReadonlyArray<{
  id: BrowserBenchmarkId;
  name: string;
  description: string;
  split: string;
}> = [
  { id: "mmlu", name: "MMLU", description: "57-subject knowledge and reasoning", split: "test" },
  { id: "arc_challenge", name: "ARC-Challenge", description: "Hard grade-school science", split: "test" },
  { id: "openbookqa", name: "OpenBookQA", description: "Elementary science reasoning", split: "test" },
  { id: "hellaswag", name: "HellaSwag", description: "Commonsense completion", split: "validation" },
  { id: "commonsense_qa", name: "CommonsenseQA", description: "Everyday concept reasoning", split: "validation" },
  { id: "winogrande", name: "WinoGrande", description: "Pronoun and commonsense reasoning", split: "validation" },
  { id: "truthfulqa", name: "TruthfulQA", description: "Misconception resistance", split: "validation" },
  { id: "boolq", name: "BoolQ", description: "Passage-grounded yes/no questions", split: "validation" },
];

export const MAX_BROWSER_ITEMS = 20;
export const VARIANTS_PER_ITEM = 2;

export function requestCount(itemCount: number): number {
  return itemCount * (1 + VARIANTS_PER_ITEM);
}

export function validateBrowserAuditRequest(value: unknown): BrowserAuditRequest {
  if (!value || typeof value !== "object") throw new Error("Request body must be an object.");
  const raw = value as Record<string, unknown>;
  const provider = String(raw.provider ?? "") as BrowserProviderId;
  const benchmark = String(raw.benchmark ?? "") as BrowserBenchmarkId;
  const apiKey = String(raw.apiKey ?? "");
  const model = String(raw.model ?? "").trim();
  const itemCount = Number(raw.itemCount);
  const offset = Number(raw.offset ?? 0);
  if (!BROWSER_PROVIDERS.some((entry) => entry.id === provider)) throw new Error("Unsupported provider.");
  if (!BROWSER_BENCHMARKS.some((entry) => entry.id === benchmark)) throw new Error("Unsupported benchmark.");
  if (apiKey.length < 8 || apiKey.length > 512 || /[\r\n]/.test(apiKey)) throw new Error("API key is malformed.");
  if (!model || model.length > 200 || /[\r\n]/.test(model)) throw new Error("Model ID is malformed.");
  if (!Number.isInteger(itemCount) || itemCount < 1 || itemCount > MAX_BROWSER_ITEMS) throw new Error(`Item count must be between 1 and ${MAX_BROWSER_ITEMS}.`);
  if (!Number.isInteger(offset) || offset < 0 || offset > 10000) throw new Error("Offset must be between 0 and 10000.");
  if (raw.acknowledgeExternalTransfer !== true) throw new Error("External benchmark transfer must be acknowledged.");
  return { provider, benchmark, apiKey, model, itemCount, offset, acknowledgeExternalTransfer: true };
}

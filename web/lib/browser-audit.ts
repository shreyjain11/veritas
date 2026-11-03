import { isReasoningModel } from "./audit-logic";

export type BrowserProviderId =
  | "openai"
  | "anthropic"
  | "google"
  | "xai"
  | "mistral"
  | "deepseek"
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
  maxOutputTokens: number;
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
  request: { prompt: string; max_output_tokens: number };
  normalized_request: { prompt: string; max_output_tokens: number };
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
    canonical_reproduced_score: number | null;
    robust_score: number | null;
    fresh_score: null;
    robustness_gap: number | null;
    fresh_generalization_gap: null;
    ci: [number, number] | null;
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
      open_weight: boolean | null;
      max_output_tokens: number;
    };
  };
};

export type BrowserProvider = {
  id: BrowserProviderId;
  name: string;
  description: string;
  /** An example model ID; providers rename models, so the UI asks users to verify it. */
  example: string;
  /** Whether the provider serves open-weight checkpoints (null: depends on the model). */
  openWeight: boolean | null;
};

export const BROWSER_PROVIDERS: ReadonlyArray<BrowserProvider> = [
  { id: "openai", name: "OpenAI", description: "GPT and o-series models", example: "gpt-4o-mini", openWeight: false },
  { id: "anthropic", name: "Anthropic", description: "Claude via the OpenAI-compatible endpoint", example: "claude-haiku-5-5", openWeight: false },
  { id: "google", name: "Google Gemini", description: "Gemini via the OpenAI-compatible endpoint", example: "gemini-2.5-flash", openWeight: false },
  { id: "xai", name: "xAI", description: "Grok models", example: "grok-3-mini", openWeight: false },
  { id: "mistral", name: "Mistral", description: "Mistral La Plateforme", example: "mistral-small-latest", openWeight: null },
  { id: "deepseek", name: "DeepSeek", description: "DeepSeek platform API", example: "deepseek-chat", openWeight: null },
  { id: "together", name: "Together AI", description: "Hosted open-weight models", example: "meta-llama/Llama-3.3-70B-Instruct-Turbo", openWeight: true },
  { id: "fireworks", name: "Fireworks AI", description: "Hosted open-weight models", example: "accounts/fireworks/models/llama-v3p3-70b-instruct", openWeight: true },
  { id: "groq", name: "Groq", description: "Fast hosted open-weight inference", example: "llama-3.3-70b-versatile", openWeight: true },
  { id: "openrouter", name: "OpenRouter", description: "Multi-provider model access", example: "openai/gpt-4o-mini", openWeight: null },
  { id: "huggingface", name: "Hugging Face", description: "Inference Providers router", example: "meta-llama/Llama-3.1-8B-Instruct", openWeight: true },
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

export const MAX_BROWSER_ITEMS = 50;
export const VARIANTS_PER_ITEM = 2;
export const MAX_OUTPUT_TOKENS = 4096;
export const OUTPUT_BUDGETS = [16, 64, 256, 1024, 4096] as const;

export function requestCount(itemCount: number): number {
  return itemCount * (1 + VARIANTS_PER_ITEM);
}

/** Short answers need few tokens; reasoning models spend output tokens before answering. */
export function defaultOutputTokens(model: string): number {
  return isReasoningModel(model) ? 1024 : 16;
}

export function validateBrowserAuditRequest(value: unknown): BrowserAuditRequest {
  if (!value || typeof value !== "object") throw new Error("Request body must be an object.");
  const raw = value as Record<string, unknown>;
  const provider = String(raw.provider ?? "") as BrowserProviderId;
  const benchmark = String(raw.benchmark ?? "") as BrowserBenchmarkId;
  const apiKey = String(raw.apiKey ?? "").trim();
  const model = String(raw.model ?? "").trim();
  const itemCount = Number(raw.itemCount);
  const offset = Number(raw.offset ?? 0);
  const maxOutputTokens = raw.maxOutputTokens == null ? defaultOutputTokens(model) : Number(raw.maxOutputTokens);
  if (!BROWSER_PROVIDERS.some((entry) => entry.id === provider)) throw new Error("Unsupported provider.");
  if (!BROWSER_BENCHMARKS.some((entry) => entry.id === benchmark)) throw new Error("Unsupported benchmark.");
  if (apiKey.length < 8 || apiKey.length > 512 || /[\s]/.test(apiKey)) throw new Error("API key is malformed (it should be one line with no spaces).");
  if (!model || model.length > 200 || /[\r\n]/.test(model)) throw new Error("Model ID is malformed.");
  if (!Number.isInteger(itemCount) || itemCount < 1 || itemCount > MAX_BROWSER_ITEMS) throw new Error(`Item count must be between 1 and ${MAX_BROWSER_ITEMS}.`);
  if (!Number.isInteger(offset) || offset < 0 || offset > 10000) throw new Error("Offset must be between 0 and 10000.");
  if (!Number.isInteger(maxOutputTokens) || maxOutputTokens < 1 || maxOutputTokens > MAX_OUTPUT_TOKENS) {
    throw new Error(`Output budget must be between 1 and ${MAX_OUTPUT_TOKENS} tokens.`);
  }
  if (raw.acknowledgeExternalTransfer !== true) throw new Error("External benchmark transfer must be acknowledged.");
  return { provider, benchmark, apiKey, model, itemCount, offset, maxOutputTokens, acknowledgeExternalTransfer: true };
}

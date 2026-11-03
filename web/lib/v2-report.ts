/** Schema-v2 report shape as rendered by the viewer (CLI and hosted reports alike). */

export type V2Choice = { id: string; text: string };
export type V2Item = {
  id: string;
  prompt: string | { role?: string; content?: unknown }[];
  expected_output: unknown;
  choices?: V2Choice[] | null;
  family_id?: string | null;
  metadata?: Record<string, unknown>;
};
export type V2Response = {
  item_id: string;
  request?: { prompt?: unknown; messages?: unknown };
  raw_text: string;
  parsed_answer?: unknown;
  token_logprobs?: number[] | null;
  latency_ms?: number | null;
  token_count?: number | null;
  finish_reason?: string | null;
  error?: string | null;
};
export type V2Finding = {
  detector_id: string;
  hypothesis: string;
  status: string;
  strength: string;
  direction: string;
  evidence_type?: string;
  effect_size?: number | null;
  ci?: [number, number] | null;
  p_value?: number | null;
  corrected_p_value?: number | null;
  alternative_explanations?: string[];
  details?: Record<string, unknown>;
};
export type V2Transformation = {
  id?: string;
  family: string;
  parent_item_id: string;
  child_item_id: string;
  validation: string;
  expected_output?: unknown;
  parameters?: Record<string, unknown>;
};
export type V2MatrixRow = {
  hypothesis: string;
  supporting: string[];
  contradicting: string[];
  unavailable: string[];
  confidence: string;
};
export type V2Report = {
  schema_version: "2.0";
  audit_hash: string;
  benchmark: { id: string; version: string; task_type: string; visibility: string; split?: string; items: V2Item[] };
  score: {
    reported_score?: number | null;
    canonical_reproduced_score?: number | null;
    robust_score?: number | null;
    fresh_score?: number | null;
    robustness_gap?: number | null;
    ci?: [number, number] | null;
  };
  findings: V2Finding[];
  evidence_matrix: V2MatrixRow[];
  transformations: V2Transformation[];
  responses: V2Response[];
  limitations: string[];
  provenance: {
    benchmark_hash: string;
    audit_spec_hash: string;
    cache_state?: string;
    privacy_warnings?: string[];
    external_transfer_acknowledged?: boolean;
    package_version?: string;
    execution_surface?: string;
    model: { id: string; revision?: string | null; adapter: string; provider?: string | null };
  };
};

const isObject = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

/** Validate the fields the viewer relies on, with a message that says what is wrong. */
export function parseV2Report(data: unknown): V2Report {
  if (!isObject(data)) throw new Error("The file is not a JSON object.");
  if (data.schema_version !== "2.0") {
    if ("honest" in data && "reported" in data) {
      throw new Error("This is a legacy (v1) biological report. Open it in the legacy viewer.");
    }
    throw new Error("This is not a schema-v2 Veritas report (schema_version must be \"2.0\").");
  }
  const missing = ["audit_hash", "benchmark", "score", "findings", "responses", "provenance"].filter((key) => !(key in data));
  if (missing.length) throw new Error(`The report is incomplete: missing ${missing.join(", ")}.`);
  const benchmark = data.benchmark;
  if (!isObject(benchmark) || !Array.isArray(benchmark.items)) throw new Error("The report's benchmark has no items list.");
  if (!Array.isArray(data.findings) || !Array.isArray(data.responses)) throw new Error("findings and responses must be lists.");
  if (!isObject(data.provenance) || !isObject(data.provenance.model)) throw new Error("The report's provenance has no model record.");
  return {
    ...(data as unknown as V2Report),
    evidence_matrix: Array.isArray(data.evidence_matrix) ? (data.evidence_matrix as V2MatrixRow[]) : [],
    transformations: Array.isArray(data.transformations) ? (data.transformations as V2Transformation[]) : [],
    limitations: Array.isArray(data.limitations) ? (data.limitations as string[]) : [],
  };
}

export function promptText(prompt: V2Item["prompt"]): string {
  if (typeof prompt === "string") return prompt;
  return prompt.map((message) => `${message.role ?? "message"}: ${String(message.content ?? "")}`).join("\n");
}

/** The exact prompt a response was generated from, whichever adapter recorded it. */
export function requestPrompt(response: V2Response | undefined): string | null {
  const request = response?.request;
  if (!request) return null;
  if (typeof request.prompt === "string") return request.prompt;
  if (Array.isArray(request.messages)) {
    return request.messages
      .map((message) => (isObject(message) ? `${String(message.role ?? "message")}: ${String(message.content ?? "")}` : String(message)))
      .join("\n\n");
  }
  return null;
}

export function answerText(value: unknown): string {
  if (value == null) return "—";
  return typeof value === "string" ? value : JSON.stringify(value);
}

/** null when the response is missing or errored: such items are excluded, not wrong. */
export function isCorrect(response: V2Response | undefined, expected: unknown): boolean | null {
  if (!response || response.error) return null;
  if (response.parsed_answer == null) return false;
  return answerText(response.parsed_answer).trim() === answerText(expected).trim();
}

export function percent(value: number | null | undefined, signed = false): string {
  if (value == null) return "—";
  const text = `${(value * 100).toFixed(1)}%`;
  return signed && value > 0 ? `+${text}` : text;
}

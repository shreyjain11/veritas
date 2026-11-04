/**
 * Pure, network-free audit logic for the hosted browser runner. It mirrors the Python
 * engine (src/veritas/benchmark_integrity): the same answer parser, answer-moving
 * permutations, paired statistics, Benjamini-Hochberg correction, and decision rule,
 * so a hosted report means what a CLI report means.
 */

export type Choice = { id: string; text: string };
export type McqItem = { id: string; prompt: string; expected_output: string; choices: Choice[] };

// ---------------------------------------------------------------------------------------
// Prompt rendering (matches veritas.benchmark_integrity.prompting templates)
// ---------------------------------------------------------------------------------------

export type Template = "default" | "qa_block";

export function formatPrompt(item: Pick<McqItem, "prompt" | "choices">, template: Template = "default"): string {
  if (template === "qa_block") {
    const options = item.choices.map((choice) => `(${choice.id}) ${choice.text}`).join("\n");
    return `Question:\n${item.prompt}\n\nOptions:\n${options}\n\nRespond with only the label of the correct option.`;
  }
  const options = item.choices.map((choice) => `${choice.id}. ${choice.text}`).join("\n");
  return `${item.prompt}\n\nChoices:\n${options}\n\nAnswer with the choice label only.`;
}

/** FNV-1a: a tiny stable string hash for deterministic per-item choices. */
export function stableHash(text: string): number {
  let hash = 0x811c9dc5;
  for (let index = 0; index < text.length; index++) {
    hash ^= text.charCodeAt(index);
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return hash >>> 0;
}

/**
 * Rotate option texts under fixed positional labels by k in [1, n-1], so every text —
 * including the correct one — moves to a new label. Returns the new choices and key.
 */
export function permuteChoices(item: McqItem): { choices: Choice[]; expected: string; shift: number } {
  const count = item.choices.length;
  if (count < 2) throw new Error("permutation needs at least two options");
  const shift = 1 + (stableHash(item.id) % (count - 1));
  const choices = item.choices.map((choice, position) => ({
    id: choice.id,
    text: item.choices[(position + shift) % count]!.text,
  }));
  const correctText = item.choices.find((choice) => choice.id === item.expected_output)?.text;
  const expected = choices.find((choice) => choice.text === correctText)?.id ?? item.expected_output;
  return { choices, expected, shift };
}

// ---------------------------------------------------------------------------------------
// Answer parsing (port of veritas.benchmark_integrity.prompting.parse_answer)
// ---------------------------------------------------------------------------------------

// These patterns run on untrusted model output, so they must stay linear-time (no ReDoS).
// They are applied to whitespace-collapsed text: every gap is at most ONE space, matched by
// " ?", so no two quantifiers compete for the same characters. Labels start with an
// alphanumeric so the leading-noise class (which includes "_") cannot overlap them.
const LABEL = String.raw`(?<label>[A-Za-z0-9][A-Za-z0-9_]*)(?![A-Za-z0-9_])`;
const ANSWER_STATEMENT = new RegExp(
  String.raw`\b(?:final )?answer\b ?(?:(?:is|would be|should be|:|=|-|–) ?)?(?:(?:\*\*|__) ?)?(?:(?:option|choice|label) )?[(\[]? ?` + LABEL,
  "gi",
);
const LEADING_LABEL = new RegExp(String.raw`^[ *_\x60"'“‘(\[]*(?:(?:option|choice) )?` + LABEL, "i");
const EDGE_NOISE = new Set(" \t\r\n*_`\"'“”‘’()[]{}<>.:;,!?");

function stripEdges(text: string): string {
  let start = 0;
  let end = text.length;
  while (start < end && EDGE_NOISE.has(text[start]!)) start++;
  while (end > start && EDGE_NOISE.has(text[end - 1]!)) end--;
  return text.slice(start, end);
}

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function labelAt(match: RegExpMatchArray, text: string, labels: Map<string, string>): string | null {
  const token = match.groups?.label ?? "";
  const label = labels.get(token.toLowerCase());
  if (!label) return null;
  const end = (match.index ?? 0) + match[0].length;
  // "a" and "I" double as English words: "the answer is a tricky one" names no label.
  if ((token === "a" || token === "I") && /^ [A-Za-z]/.test(text.slice(end))) return null;
  return label;
}

/** The declared choice id the response names, or null when it names none or several. */
export function parseAnswer(text: string, choices: Choice[]): string | null {
  const stripped = text.trim().replace(/\s+/g, " ");
  const labels = new Map(choices.map((choice) => [choice.id.toLowerCase(), choice.id]));
  const bare = stripEdges(stripped);
  const direct = labels.get(bare.toLowerCase());
  if (direct) return direct;
  const statements = [...stripped.matchAll(ANSWER_STATEMENT)].reverse();
  for (const match of statements) {
    const label = labelAt(match, stripped, labels);
    if (label) return label;
  }
  const leading = stripped.match(LEADING_LABEL);
  if (leading) {
    const label = labelAt(leading, stripped, labels);
    if (label) return label;
  }
  const options = choices.map((choice) => ({ id: choice.id, text: choice.text.replace(/\s+/g, " ").trim().toLowerCase() }));
  const exact = options.filter((option) => option.text === bare.toLowerCase());
  if (exact.length === 1) return exact[0]!.id;
  const folded = stripped.toLowerCase();
  const mentioned = options.filter(
    (option) => option.text.length >= 2 && new RegExp(`(?<![A-Za-z0-9_])${escapeRegExp(option.text)}(?![A-Za-z0-9_])`).test(folded),
  );
  return mentioned.length === 1 ? mentioned[0]!.id : null;
}

// ---------------------------------------------------------------------------------------
// Paired statistics (mirrors veritas.benchmark_integrity.statistics)
// ---------------------------------------------------------------------------------------

/** Small seeded PRNG so reports are reproducible run to run. */
export function mulberry32(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function quantile(sorted: number[], q: number): number {
  const position = (sorted.length - 1) * q;
  const lower = Math.floor(position);
  const upper = Math.ceil(position);
  return sorted[lower]! + (sorted[upper]! - sorted[lower]!) * (position - lower);
}

function checkPaired(left: number[], right: number[]): void {
  if (!left.length || left.length !== right.length) {
    throw new Error("paired statistics require equal, non-empty samples");
  }
}

export function pairedBootstrapGap(
  left: number[],
  right: number[],
  { samples = 2000, confidence = 0.95, seed = 42 } = {},
): [number, number] {
  checkPaired(left, right);
  const random = mulberry32(seed);
  const gaps: number[] = [];
  for (let sample = 0; sample < samples; sample++) {
    let total = 0;
    for (let index = 0; index < left.length; index++) {
      const pick = Math.floor(random() * left.length);
      total += left[pick]! - right[pick]!;
    }
    gaps.push(total / left.length);
  }
  gaps.sort((a, b) => a - b);
  const alpha = (1 - confidence) / 2;
  return [quantile(gaps, alpha), quantile(gaps, 1 - alpha)];
}

export function pairedPermutationPValue(left: number[], right: number[], { samples = 5000, seed = 42 } = {}): number {
  checkPaired(left, right);
  const differences = left.map((value, index) => value - right[index]!);
  const observed = Math.abs(differences.reduce((sum, value) => sum + value, 0) / differences.length);
  const random = mulberry32(seed);
  let extreme = 0;
  for (let sample = 0; sample < samples; sample++) {
    let total = 0;
    for (const difference of differences) total += random() < 0.5 ? -difference : difference;
    if (Math.abs(total / differences.length) >= observed - 1e-12) extreme++;
  }
  return (extreme + 1) / (samples + 1);
}

export function benjaminiHochberg(values: number[]): number[] {
  const order = values.map((value, index) => ({ value, index })).sort((a, b) => a.value - b.value);
  const adjusted = new Array<number>(values.length).fill(0);
  let running = 1;
  for (let rank = order.length; rank >= 1; rank--) {
    const entry = order[rank - 1]!;
    running = Math.min(running, (entry.value * values.length) / rank);
    adjusted[entry.index] = Math.min(1, running);
  }
  return adjusted;
}

// ---------------------------------------------------------------------------------------
// Decision rule (mirrors service._Analysis._correct_and_classify)
// ---------------------------------------------------------------------------------------

export const DECISION = { alpha: 0.05, equivalenceMargin: 0.05, minParentItems: 10 } as const;

export type Direction = "supports" | "contradicts" | "inconclusive";
export type Strength = "direct" | "strong_indirect" | "weak_indirect" | "against" | "inconclusive" | "unavailable";

export type PairedStats = {
  parent_item_count: number;
  canonical_score: number;
  transformed_score: number;
  gap: number;
  ci: [number, number];
  permutation_p_value: number;
};

export function pairedStats(left: number[], right: number[], seed = 42): PairedStats | null {
  if (!left.length) return null;
  const mean = (values: number[]) => values.reduce((sum, value) => sum + value, 0) / values.length;
  const canonical = mean(left);
  const transformed = mean(right);
  return {
    parent_item_count: left.length,
    canonical_score: canonical,
    transformed_score: transformed,
    gap: canonical - transformed,
    ci: pairedBootstrapGap(left, right, { seed }),
    permutation_p_value: pairedPermutationPValue(left, right, { seed }),
  };
}

export function classify(stats: PairedStats, correctedP: number): { direction: Direction; strength: Strength; rule: string } {
  if (stats.parent_item_count < DECISION.minParentItems) {
    return { direction: "inconclusive", strength: "inconclusive", rule: `fewer than ${DECISION.minParentItems} paired parent items` };
  }
  if (stats.gap > 0 && stats.ci[0] > 0 && correctedP <= DECISION.alpha) {
    return { direction: "supports", strength: "weak_indirect", rule: `paired drop with interval above 0 and corrected p <= ${DECISION.alpha}` };
  }
  if (stats.ci[1] < DECISION.equivalenceMargin) {
    return { direction: "contradicts", strength: "against", rule: `paired drop bounded below the ${DECISION.equivalenceMargin} equivalence margin` };
  }
  return { direction: "inconclusive", strength: "inconclusive", rule: "interval is compatible with both no effect and a meaningful drop" };
}

// ---------------------------------------------------------------------------------------
// Evidence matrix (mirrors service._matrix)
// ---------------------------------------------------------------------------------------

export type FindingLike = { detector_id: string; status: string; direction: string; strength: string; assumptions?: string[] };

const STRENGTH_ORDER: Strength[] = ["direct", "strong_indirect", "weak_indirect", "against", "inconclusive", "unavailable"];

export function evidenceMatrix(findings: FindingLike[], rows: Array<[string, string[]]>) {
  const byId = new Map(findings.map((finding) => [finding.detector_id, finding]));
  return rows.map(([hypothesis, detectors]) => {
    const completed = detectors.map((id) => byId.get(id)).filter((f): f is FindingLike => f?.status === "complete");
    const supporting = completed.filter((f) => f.direction === "supports");
    const contradicting = completed.filter((f) => f.direction === "contradicts");
    const confidence: Strength = supporting.length
      ? supporting.map((f) => f.strength as Strength).sort((a, b) => STRENGTH_ORDER.indexOf(a) - STRENGTH_ORDER.indexOf(b))[0]!
      : contradicting.length
        ? "against"
        : completed.length
          ? "inconclusive"
          : "unavailable";
    return {
      hypothesis,
      supporting: supporting.map((f) => f.detector_id),
      contradicting: contradicting.map((f) => f.detector_id),
      unavailable: detectors.filter((id) => byId.get(id)?.status !== "complete"),
      confidence,
      assumptions: [...new Set(completed.flatMap((f) => f.assumptions ?? []))],
    };
  });
}

/** Model IDs that spend output tokens on hidden reasoning and reject temperature 0. */
export function isReasoningModel(model: string): boolean {
  return /(^|\/)(o\d|gpt-5)|reasoner|(^|[-_/])r1([-_/]|$)|thinking|qwq|gemini-(2\.5|[3-9])/i.test(model);
}

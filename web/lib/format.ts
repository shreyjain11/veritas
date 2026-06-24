/** Display formatting for the viewer. Values themselves are never rounded in the data;
 * these are presentation helpers only. */

/** A metric value (Spearman, etc.) to 3 dp, preserving a leading sign for negatives. */
export function fmtMetric(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return value.toFixed(3);
}

/** A signed delta, e.g. "+0.147". */
export function fmtSigned(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const s = value.toFixed(3);
  return value > 0 ? `+${s}` : s;
}

/** A confidence interval "[lo, hi]" or "" when absent. */
export function fmtCI(lo: number | null | undefined, hi: number | null | undefined): string {
  if (lo === null || lo === undefined || hi === null || hi === undefined) return "";
  return `[${lo.toFixed(3)}, ${hi.toFixed(3)}]`;
}

/** A rate as a percentage, e.g. 0.385 -> "38.5%". */
export function fmtPct(rate: number, digits = 1): string {
  return `${(rate * 100).toFixed(digits)}%`;
}

/** Leakage as an integer percentage of the reported metric: round(delta / reported * 100).
 * The single source of truth for every "X% of the reported metric" figure (hero, proof
 * cards, viewer) so they round identically. Returns 0 when reported is 0/absent. */
export function leakageShare(delta: number | null | undefined, reported: number | null | undefined): number {
  if (delta === null || delta === undefined || !reported) return 0;
  return Math.round((delta / reported) * 100);
}

/** A short, copyable hash preview: first 10 + last 6. */
export function shortHash(hash: string): string {
  if (hash.length <= 20) return hash;
  return `${hash.slice(0, 10)}…${hash.slice(-6)}`;
}

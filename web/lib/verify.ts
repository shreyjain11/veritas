/**
 * Client-side audit_hash re-verification — the viewer is as tamper-evident as the CLI.
 *
 * Rebuilds the exact hashed-content subset that veritas.report.model._hashable_content
 * produces (EXCLUDING audit_hash, created_at, and the computed wire-only fields
 * leakage.fraction_contaminated, provenance.version_mismatches, DetectorCell.rate),
 * canonicalizes it the same way, and SHA-256s it. The hash gate (web/test/hash.test.ts)
 * re-derives every committed fixture's audit_hash and asserts it equals the stored value,
 * which (since the fixtures were hashed by Python) proves this port is byte-identical.
 */

import type {
  AuditReport,
  DetectorCell,
  LeakageSplit,
  LeakageSummary,
  StratumResult,
  TracedValue,
} from "./audit-report";
import { canonicalJson } from "./canonical";

export interface VerifyResult {
  ok: boolean;
  computed: string;
  stored: string;
}

function tracedPayload(t: TracedValue | null | undefined): unknown {
  if (t === null || t === undefined) return null;
  return {
    name: t.name,
    value: t.value ?? null,
    status: t.status,
    provenance_ref: t.provenance_ref,
    ci_low: t.ci_low ?? null,
    ci_high: t.ci_high ?? null,
  };
}

function leakagePayload(l: LeakageSummary | null | undefined): unknown {
  if (l === null || l === undefined) return null;
  return { n_eval: l.n_eval, n_contaminated: l.n_contaminated, per_detector: l.per_detector };
}

function splitsPayload(splits: LeakageSplit[] | undefined): unknown {
  return (splits ?? []).map((split) => ({
    split_name: split.split_name,
    role: split.role,
    note: split.note ?? null,
    cells: split.cells.map((cell: DetectorCell) => ({
      detector: cell.detector,
      n_flagged: cell.n_flagged,
      n_total: cell.n_total,
      threshold_label: cell.threshold_label,
    })),
  }));
}

function stratificationPayload(strata: StratumResult[] | undefined): unknown {
  return (strata ?? []).map((s) => ({
    axis_name: s.axis_name,
    bucket_index: s.bucket_index,
    bucket_label: s.bucket_label,
    n: s.n,
    metric: tracedPayload(s.metric),
    is_silent_failure: s.is_silent_failure ?? false,
  }));
}

/** The deterministic subset the audit_hash is computed over (mirrors _hashable_content). */
export function hashableContent(report: AuditReport): unknown {
  const p = report.provenance;
  return {
    benchmark_name: report.benchmark_name,
    report_kind: report.report_kind ?? "metric_audit",
    status: report.status ?? "ok",
    reported: tracedPayload(report.reported),
    honest: tracedPayload(report.honest),
    delta: tracedPayload(report.delta),
    leakage: leakagePayload(report.leakage),
    splits: splitsPayload(report.splits),
    provenance: {
      input_hashes: p.input_hashes,
      params: p.params,
      seed: p.seed,
      pinned_versions: p.pinned_versions,
      runtime_versions: p.runtime_versions,
    },
    limitations: (report.limitations ?? []).map((lim) => ({
      id: lim.id,
      title: lim.title,
      detail: lim.detail,
    })),
    stratification: stratificationPayload(report.stratification),
  };
}

async function sha256Hex(text: string): Promise<string> {
  const bytes = new TextEncoder().encode(text);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

/** Recompute the report's audit_hash and compare it to the stored value. */
export async function verifyAuditHash(report: AuditReport): Promise<VerifyResult> {
  const computed = await sha256Hex(canonicalJson(hashableContent(report)));
  return { ok: computed === report.audit_hash, computed, stored: report.audit_hash };
}

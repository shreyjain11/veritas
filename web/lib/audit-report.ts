/* GENERATED from schema/audit-report.schema.json by 'npm run gen:types'. Do not edit. */

export type AuditHash = string;
export type BenchmarkName = string;
export type CreatedAt = string | null;
export type CiHigh = number | null;
export type CiLow = number | null;
export type Name = string;
export type ProvenanceRef = string;
export type ResultStatus = "ok" | "insufficient_clean_data" | "undefined_metric";
export type Value = number | null;
export type NContaminated = number;
export type NEval = number;
export type Detail = string;
export type Id = string;
export type Title = string;
export type Limitations = Limitation[];
export type CreatedAt1 = string | null;
export type Seed = number;
/**
 * What an AuditReport carries (the wire-format discriminator).
 *
 * ``metric_audit`` is the reported-vs-honest audit (the metric slots are present);
 * ``detection`` carries a leakage splits-matrix and no metric (no model was scored);
 * ``stratification`` carries only a performance-by-difficulty curve. The kind is part
 * of the hashed content, and a validator forbids fabricating a metric for the
 * non-metric kinds (their reported/honest/delta must be null).
 */
export type ReportKind = "metric_audit" | "detection" | "stratification";
/**
 * @minItems 1
 */
export type Cells = [DetectorCell, ...DetectorCell[]];
export type Detector = string;
export type NFlagged = number;
export type NTotal = number;
export type ThresholdLabel = string;
export type Note = string | null;
/**
 * The intent of a split in a detection report's matrix (drives viewer emphasis).
 */
export type SplitRole = "demonstration" | "control" | "finding";
export type SplitName = string;
export type Splits = LeakageSplit[];
export type ResultStatus1 = "ok" | "insufficient_clean_data" | "undefined_metric";
export type AxisName = string;
export type BucketIndex = number;
export type BucketLabel = string;
export type IsSilentFailure = boolean;
export type N = number;
export type Stratification = StratumResult[];

export interface AuditReport {
  audit_hash: AuditHash;
  benchmark_name: BenchmarkName;
  created_at?: CreatedAt;
  delta?: TracedValue | null;
  honest?: TracedValue | null;
  leakage?: LeakageSummary | null;
  limitations?: Limitations;
  provenance: ProvenanceRecord;
  report_kind?: ReportKind;
  reported?: TracedValue | null;
  splits?: Splits;
  status?: ResultStatus1;
  stratification?: Stratification;
}
export interface TracedValue {
  ci_high?: CiHigh;
  ci_low?: CiLow;
  name: Name;
  provenance_ref: ProvenanceRef;
  status?: ResultStatus;
  value: Value;
}
export interface LeakageSummary {
  fraction_contaminated: number;
  n_contaminated: NContaminated;
  n_eval: NEval;
  per_detector?: PerDetector;
}
export interface PerDetector {
  [k: string]: number;
}
/**
 * A disclosed methodological caveat (e.g. bootstrap small-n under-coverage).
 *
 * Limitations are part of the report's hashed content: dropping or changing one
 * changes the ``audit_hash`` (assembled in ``veritas.report``).
 */
export interface Limitation {
  detail: Detail;
  id: Id;
  title: Title;
}
export interface ProvenanceRecord {
  created_at?: CreatedAt1;
  input_hashes: InputHashes;
  params: Params;
  pinned_versions: PinnedVersions;
  runtime_versions?: RuntimeVersions;
  seed: Seed;
  version_mismatches: string[];
}
export interface InputHashes {
  [k: string]: string;
}
export interface Params {
  [k: string]: unknown;
}
export interface PinnedVersions {
  [k: string]: string;
}
export interface RuntimeVersions {
  [k: string]: string;
}
/**
 * One named split (a matrix row) with its per-detector cells.
 *
 * A single-split detection report (e.g. a naive genomic split) is the degenerate
 * one-row case; a multi-split report (demonstration / control / findings) renders
 * the cross-split contrast. ``role`` lets the viewer mark intent without inferring
 * it from the numbers.
 */
export interface LeakageSplit {
  cells: Cells;
  note?: Note;
  role: SplitRole;
  split_name: SplitName;
}
/**
 * One cell of a detection splits-matrix: a detector's leakage on one split.
 *
 * The cell carries the raw ``n_flagged / n_total`` count and the detector's
 * ``threshold_label`` (e.g. ``"Pfam e<=1e-3"``) so the viewer renders an anchored
 * claim, not a bare percentage. ``rate`` is derived (never stored) to avoid drift.
 */
export interface DetectorCell {
  detector: Detector;
  n_flagged: NFlagged;
  n_total: NTotal;
  rate: number;
  threshold_label: ThresholdLabel;
}
/**
 * One difficulty bucket's traced performance, for the silent-failure analysis.
 *
 * The per-bucket metric is a TracedValue (so stratification numbers are stamped
 * exactly like the headline metrics), and the whole tuple is part of the report's
 * hashed content.
 */
export interface StratumResult {
  axis_name: AxisName;
  bucket_index: BucketIndex;
  bucket_label: BucketLabel;
  is_silent_failure?: IsSilentFailure;
  metric: TracedValue;
  n: N;
}

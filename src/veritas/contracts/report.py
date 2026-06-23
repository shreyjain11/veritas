"""Report-level contracts: TracedValue, LeakageSummary, AuditReport.

TracedValue makes provenance unforgeable: a number can only enter a report
wrapped in a TracedValue, which requires a non-empty ``provenance_ref``
(first principle #3). AuditReport's metric slots are typed as TracedValue, so a
raw/untraced number cannot be placed in a report.
"""

from __future__ import annotations

from typing import Self

from pydantic import Field, model_validator

from veritas.contracts.base import FrozenModel
from veritas.contracts.enums import ReportKind, ResultStatus, SplitRole
from veritas.contracts.provenance import ProvenanceRecord


class TracedValue(FrozenModel):
    name: str
    value: float | None
    status: ResultStatus = ResultStatus.OK
    provenance_ref: str = Field(min_length=1)
    ci_low: float | None = None
    ci_high: float | None = None

    @model_validator(mode="after")
    def _check_invariants(self) -> Self:
        if self.status is ResultStatus.OK and self.value is None:
            raise ValueError("an OK TracedValue must carry a value")
        if self.status is not ResultStatus.OK and self.value is not None:
            raise ValueError("a non-OK TracedValue must not carry a value")
        if self.ci_low is not None and self.ci_high is not None and self.ci_low > self.ci_high:
            raise ValueError("ci_low must be <= ci_high")
        return self


class LeakageSummary(FrozenModel):
    n_eval: int = Field(ge=0)
    n_contaminated: int = Field(ge=0)
    per_detector: dict[str, int] = Field(default_factory=dict)

    @property
    def fraction_contaminated(self) -> float:
        if self.n_eval == 0:
            return 0.0
        return self.n_contaminated / self.n_eval


class Limitation(FrozenModel):
    """A disclosed methodological caveat (e.g. bootstrap small-n under-coverage).

    Limitations are part of the report's hashed content: dropping or changing one
    changes the ``audit_hash`` (assembled in ``veritas.report``).
    """

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    detail: str = Field(min_length=1)


class DetectorCell(FrozenModel):
    """One cell of a detection splits-matrix: a detector's leakage on one split.

    The cell carries the raw ``n_flagged / n_total`` count and the detector's
    ``threshold_label`` (e.g. ``"Pfam e<=1e-3"``) so the viewer renders an anchored
    claim, not a bare percentage. ``rate`` is derived (never stored) to avoid drift.
    """

    detector: str = Field(min_length=1)
    n_flagged: int = Field(ge=0)
    n_total: int = Field(ge=0)
    threshold_label: str = Field(min_length=1)

    @model_validator(mode="after")
    def _check_counts(self) -> Self:
        if self.n_flagged > self.n_total:
            raise ValueError("n_flagged must be <= n_total")
        return self

    @property
    def rate(self) -> float:
        if self.n_total == 0:
            return 0.0
        return self.n_flagged / self.n_total


class LeakageSplit(FrozenModel):
    """One named split (a matrix row) with its per-detector cells.

    A single-split detection report (e.g. a naive genomic split) is the degenerate
    one-row case; a multi-split report (demonstration / control / findings) renders
    the cross-split contrast. ``role`` lets the viewer mark intent without inferring
    it from the numbers.
    """

    split_name: str = Field(min_length=1)
    role: SplitRole
    cells: tuple[DetectorCell, ...] = Field(min_length=1)
    note: str | None = None


class StratumResult(FrozenModel):
    """One difficulty bucket's traced performance, for the silent-failure analysis.

    The per-bucket metric is a TracedValue (so stratification numbers are stamped
    exactly like the headline metrics), and the whole tuple is part of the report's
    hashed content.
    """

    axis_name: str
    bucket_index: int = Field(ge=0)
    bucket_label: str
    n: int = Field(ge=0)
    metric: TracedValue
    is_silent_failure: bool = False


class AuditReport(FrozenModel):
    audit_hash: str = Field(min_length=1)
    benchmark_name: str
    # The wire-format discriminator; part of the hashed content (it cannot be swapped
    # silently). Defaults to metric_audit so existing reported-vs-honest reports are
    # unchanged.
    report_kind: ReportKind = ReportKind.METRIC_AUDIT
    status: ResultStatus = ResultStatus.OK
    # Metric slots + top-level leakage are present ONLY for metric_audit; the validator
    # forbids a detection/stratification report from carrying a (fabricated) metric.
    reported: TracedValue | None = None
    honest: TracedValue | None = None
    delta: TracedValue | None = None
    leakage: LeakageSummary | None = None
    # Detection splits-matrix (one+ rows for a detection report; empty otherwise).
    splits: tuple[LeakageSplit, ...] = ()
    provenance: ProvenanceRecord
    # Disclosed methodological caveats; additive (defaults empty) and part of the
    # hashed content (the report assembler stamps audit_hash over these too).
    limitations: tuple[Limitation, ...] = ()
    # Stratified robustness analysis (additive, hashed): empty when no axes are run.
    stratification: tuple[StratumResult, ...] = ()
    created_at: str | None = None

    @model_validator(mode="after")
    def _check_kind_invariants(self) -> Self:
        metric_slots = (self.reported, self.honest, self.delta)
        if self.report_kind is ReportKind.METRIC_AUDIT:
            if any(slot is None for slot in metric_slots):
                raise ValueError("a metric_audit report requires reported, honest, and delta")
            if self.leakage is None:
                raise ValueError("a metric_audit report requires a leakage summary")
            if self.splits:
                raise ValueError("a metric_audit report must not carry detection splits")
            return self
        # detection / stratification: no model was scored -> no fabricated metric.
        kind = self.report_kind.value
        if any(slot is not None for slot in metric_slots):
            raise ValueError(f"a {kind} report must not carry a metric (reported/honest/delta)")
        if self.leakage is not None:
            raise ValueError(f"a {kind} report must not carry a top-level leakage summary")
        if self.report_kind is ReportKind.DETECTION:
            if not self.splits:
                raise ValueError("a detection report requires at least one split")
            if self.stratification:
                raise ValueError("a detection report must not carry stratification")
        else:  # STRATIFICATION
            if not self.stratification:
                raise ValueError("a stratification report requires at least one stratum")
            if self.splits:
                raise ValueError("a stratification report must not carry detection splits")
        return self

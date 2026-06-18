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
from veritas.contracts.enums import ResultStatus
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
    status: ResultStatus = ResultStatus.OK
    reported: TracedValue
    honest: TracedValue
    delta: TracedValue
    leakage: LeakageSummary
    provenance: ProvenanceRecord
    # Disclosed methodological caveats; additive (defaults empty) and part of the
    # hashed content (the report assembler stamps audit_hash over these too).
    limitations: tuple[Limitation, ...] = ()
    # Stratified robustness analysis (additive, hashed): empty when no axes are run.
    stratification: tuple[StratumResult, ...] = ()
    created_at: str | None = None

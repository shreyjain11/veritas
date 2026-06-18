"""AuditInputs: the validated bundle a single audit runs over.

Bundling the benchmark and the reference set behind one frozen, self-validating
contract means the orchestrator can assume a consistent world (one alphabet,
well-formed unique ids) before any detector runs.
"""

from __future__ import annotations

from typing import Self

from pydantic import Field, model_validator

from veritas.contracts.base import FrozenModel
from veritas.contracts.benchmark import Benchmark
from veritas.contracts.reference_item import ReferenceItem


class AuditInputs(FrozenModel):
    benchmark: Benchmark
    reference_items: tuple[ReferenceItem, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        seq_types = {item.seq_type for item in self.benchmark.eval_items}
        seq_types |= {item.seq_type for item in self.reference_items}
        if len(seq_types) > 1:
            raise ValueError(
                "eval and reference items must share a single sequence alphabet; "
                f"got {sorted(str(s) for s in seq_types)}"
            )
        ref_ids = [item.id for item in self.reference_items]
        if len(ref_ids) != len(set(ref_ids)):
            raise ValueError("reference items contain duplicate ids")
        return self

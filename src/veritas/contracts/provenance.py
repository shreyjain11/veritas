"""ProvenanceRecord: the stamp attached to every computed value.

Carries both the pinned (declared) and runtime-captured backend versions so a
mismatch can be surfaced rather than silently trusted (docs/PLAN.md req C).
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from veritas.contracts.base import FrozenModel


class ProvenanceRecord(FrozenModel):
    input_hashes: dict[str, str]
    params: dict[str, Any]
    seed: int
    pinned_versions: dict[str, str]
    runtime_versions: dict[str, str] = Field(default_factory=dict)
    # Wall-clock stamp; deliberately excluded from the audit hash (determinism).
    created_at: str | None = None

    @property
    def version_mismatches(self) -> tuple[str, ...]:
        """Tools present in *both* pinned and runtime maps whose versions differ (sorted).

        Absence on either side is not a mismatch.
        """
        return tuple(
            sorted(
                tool
                for tool, pinned in self.pinned_versions.items()
                if tool in self.runtime_versions and self.runtime_versions[tool] != pinned
            )
        )

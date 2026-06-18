"""Base model for all Veritas contracts: immutable and strict about unknown fields."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class FrozenModel(BaseModel):
    """Immutable pydantic base. Subclasses reject unknown fields and field reassignment."""

    model_config = ConfigDict(frozen=True, extra="forbid")

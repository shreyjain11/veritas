"""Regulatory-DNA demo adapter: a nucleotide expression task with a genomic split.

Contamination claim is strong: the reference set is the model's TRAIN split, so a test
sequence homologous to a training sequence lets a memorizer cheat (hashFrag). The
``chromosome`` column rides along as per-item metadata (a candidate stratification key);
the primary difficulty axis is identity-to-nearest-reference.
"""

from __future__ import annotations

from pathlib import Path

from veritas.contracts import Benchmark, MetricName, MetricSpec, ReferenceItem, SeqType, SplitSpec
from veritas.demos._tabular import eval_items_from_table, reference_items_from_table


class RegulatoryDNAAdapter:
    def __init__(
        self,
        *,
        eval_table: Path,
        reference_table: Path,
        benchmark_name: str = "regulatory_dna",
        metric: MetricSpec | None = None,
    ) -> None:
        self._eval_table = eval_table
        self._reference_table = reference_table
        self._benchmark_name = benchmark_name
        self._metric = metric if metric is not None else MetricSpec(name=MetricName.AUROC)

    def load_benchmark(self) -> Benchmark:
        eval_items = eval_items_from_table(
            self._eval_table, seq_type=SeqType.NUCLEOTIDE, metadata_columns=("chromosome",)
        )
        return Benchmark(
            name=self._benchmark_name,
            eval_items=eval_items,
            split=SplitSpec(name=self._benchmark_name, kind="regulatory_dna"),
            metric=self._metric,
        )

    def load_reference(self) -> tuple[ReferenceItem, ...]:
        return reference_items_from_table(
            self._reference_table,
            seq_type=SeqType.NUCLEOTIDE,
            seen_reason=(
                f"train split of {self._benchmark_name}: homology to a training sequence is leakage"
            ),
        )

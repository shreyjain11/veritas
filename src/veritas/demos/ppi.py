"""PPI demo adapter: a protein-interaction benchmark with a declared train split.

Contamination claim is strong here: the reference set is the model's TRAIN split, so a
test protein homologous (family) or structurally near-identical (interface) to a
training protein is genuine leakage (Bushuiev et al., arXiv:2404.10457). The exact
upstream column names are reconciled when the dataset is vendored; the adapter consumes
the normalized eval/reference tables (id, sequence, label, prediction[, structure]).
"""

from __future__ import annotations

from pathlib import Path

from veritas.contracts import Benchmark, MetricName, MetricSpec, ReferenceItem, SeqType, SplitSpec
from veritas.demos._tabular import eval_items_from_table, reference_items_from_table


class PPIAdapter:
    def __init__(
        self,
        *,
        eval_table: Path,
        reference_table: Path,
        structures_dir: Path | None = None,
        benchmark_name: str = "ppi",
        metric: MetricSpec | None = None,
    ) -> None:
        self._eval_table = eval_table
        self._reference_table = reference_table
        self._structures_dir = structures_dir
        self._benchmark_name = benchmark_name
        self._metric = metric if metric is not None else MetricSpec(name=MetricName.AUROC)

    def load_benchmark(self) -> Benchmark:
        eval_items = eval_items_from_table(
            self._eval_table, seq_type=SeqType.PROTEIN, structures_dir=self._structures_dir
        )
        return Benchmark(
            name=self._benchmark_name,
            eval_items=eval_items,
            split=SplitSpec(name=self._benchmark_name, kind="ppi"),
            metric=self._metric,
        )

    def load_reference(self) -> tuple[ReferenceItem, ...]:
        return reference_items_from_table(
            self._reference_table,
            seq_type=SeqType.PROTEIN,
            seen_reason=(
                f"train split of {self._benchmark_name}: "
                "homology (family/structure) to a training protein is leakage"
            ),
            structures_dir=self._structures_dir,
        )

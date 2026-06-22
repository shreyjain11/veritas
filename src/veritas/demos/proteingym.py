"""ProteinGym demo adapter: a DMS variant-effect assay, for the STRATIFICATION demo.

Per the approved framing this is a stratification / silent-failure showcase only --
the difficulty gradient is ProteinGym's ``MSA_Neff_L_category`` (Low/Medium/High). It
makes NO model-training contamination claim: the reference wild-type is exposed purely
as a benchmark-redundancy reference, and ``seen_reason`` says so explicitly.

Inputs (confirmed ProteinGym columns):
- assay CSV (one DMS assay): ``mutant, mutated_sequence, DMS_score, DMS_score_bin``
- reference metadata CSV: ``DMS_id, UniProt_ID, target_seq, MSA_Neff_L_category`` (a row per assay)
- scores CSV: ``mutant, score`` (a model's per-variant prediction; the vendoring step
  normalizes a ProteinGym per-model score file to this two-column form)
"""

from __future__ import annotations

from pathlib import Path

from veritas.contracts import (
    Benchmark,
    EvalItem,
    MetricName,
    MetricSpec,
    ReferenceItem,
    SeqType,
    SplitSpec,
)
from veritas.io._tables import read_table

_ASSAY_REQUIRED = ("mutant", "mutated_sequence", "DMS_score")
_REFERENCE_REQUIRED = ("DMS_id", "UniProt_ID", "target_seq", "MSA_Neff_L_category")
_SCORES_REQUIRED = ("mutant", "score")

_REDUNDANCY_REASON = (
    "ProteinGym assay wild-type: benchmark-redundancy reference only, NOT model-training leakage"
)


class ProteinGymAdapter:
    def __init__(
        self,
        *,
        assay_csv: Path,
        reference_csv: Path,
        scores_csv: Path,
        dms_id: str,
        metric: MetricSpec | None = None,
    ) -> None:
        self._assay_csv = assay_csv
        self._reference_csv = reference_csv
        self._scores_csv = scores_csv
        self._dms_id = dms_id
        # DMS scores are a continuous fitness ranking -> Spearman is the ProteinGym metric.
        self._metric = metric if metric is not None else MetricSpec(name=MetricName.SPEARMAN)

    def _assay_metadata(self) -> tuple[str, str, str]:
        """Return ``(target_seq, uniprot_id, msa_depth_category)`` for this assay."""
        frame = read_table(self._reference_csv)
        missing = [column for column in _REFERENCE_REQUIRED if column not in frame.columns]
        if missing:
            raise ValueError(f"{self._reference_csv} is missing required columns: {missing}")
        for row in frame.iter_rows(named=True):
            if str(row["DMS_id"]) == self._dms_id:
                return (
                    str(row["target_seq"]),
                    str(row["UniProt_ID"]),
                    str(row["MSA_Neff_L_category"]),
                )
        raise ValueError(f"DMS_id {self._dms_id!r} not found in {self._reference_csv}")

    def _scores(self) -> dict[str, float]:
        frame = read_table(self._scores_csv)
        missing = [column for column in _SCORES_REQUIRED if column not in frame.columns]
        if missing:
            raise ValueError(f"{self._scores_csv} is missing required columns: {missing}")
        return {str(row["mutant"]): float(row["score"]) for row in frame.iter_rows(named=True)}

    def load_benchmark(self) -> Benchmark:
        _target_seq, uniprot_id, category = self._assay_metadata()
        scores = self._scores()
        frame = read_table(self._assay_csv)
        missing = [column for column in _ASSAY_REQUIRED if column not in frame.columns]
        if missing:
            raise ValueError(f"{self._assay_csv} is missing required columns: {missing}")

        eval_items: list[EvalItem] = []
        for row in frame.iter_rows(named=True):
            mutant = str(row["mutant"])
            if mutant not in scores:
                raise ValueError(f"no model score for mutant {mutant!r} in {self._scores_csv}")
            eval_items.append(
                EvalItem(
                    id=f"{self._dms_id}:{mutant}",
                    seq_type=SeqType.PROTEIN,
                    sequence=str(row["mutated_sequence"]),
                    label=float(row["DMS_score"]),
                    prediction=scores[mutant],
                    metadata={
                        "DMS_id": self._dms_id,
                        "UniProt_ID": uniprot_id,
                        "MSA_Neff_L_category": category,
                    },
                )
            )
        return Benchmark(
            name=self._dms_id,
            eval_items=tuple(eval_items),
            split=SplitSpec(name=f"proteingym:{self._dms_id}", kind="dms_substitution"),
            metric=self._metric,
        )

    def load_reference(self) -> tuple[ReferenceItem, ...]:
        target_seq, uniprot_id, _category = self._assay_metadata()
        return (
            ReferenceItem(
                id=uniprot_id,
                seq_type=SeqType.PROTEIN,
                sequence=target_seq,
                seen_reason=_REDUNDANCY_REASON,
            ),
        )

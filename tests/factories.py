"""Synthetic dataset factories with planted ground truth (docs/PLAN.md §0).

These build eval items + a ContaminationGraph whose reported/honest metric gap is
known by construction, so the honest goldens and their specificity twins assert
exact values. The metric used by these cases is thresholded accuracy@0.5, which
is exact (no float fuzz) and well-defined on single-class labels.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from veritas.contamination.base import ContaminationDetector
from veritas.contracts import (
    AuditConfig,
    AuditInputs,
    AuditReport,
    Benchmark,
    ContaminationEdge,
    ContaminationGraph,
    DeLeakPolicy,
    DetectorConfig,
    DetectorKind,
    EvalItem,
    LeakageSummary,
    MetricName,
    MetricSpec,
    ProvenanceRecord,
    ReferenceItem,
    ResultStatus,
    SeqType,
    SplitSpec,
    TracedValue,
)


def _item(item_id: str, label: float, prediction: float) -> EvalItem:
    return EvalItem(
        id=item_id, sequence="MKV", seq_type=SeqType.PROTEIN, label=label, prediction=prediction
    )


def _edge(eval_id: str, score: float = 1.0) -> ContaminationEdge:
    return ContaminationEdge(
        eval_id=eval_id,
        ref_id=f"r_{eval_id}",
        score=score,
        kind=DetectorKind.SEQUENCE,
        detector_id="factory",
    )


@dataclass(frozen=True)
class HonestCase:
    eval_items: tuple[EvalItem, ...]
    graph: ContaminationGraph
    expected_reported: float
    expected_honest: float
    expected_delta: float


def make_inflation_construction() -> HonestCase:
    """Contamination correlated with correctness ⇒ a planted reported>honest gap.

    Contaminated items are all predicted correctly (easy); clean items are partly
    wrong (hard). accuracy@0.5: reported = 16/20 = 0.8, honest(clean) = 6/10 = 0.6.
    """
    items: list[EvalItem] = []
    edges: list[ContaminationEdge] = []
    for i in range(10):  # contaminated, all correct
        items.append(_item(f"c{i}", 1.0, 0.9))
        edges.append(_edge(f"c{i}"))
    for i in range(6):  # clean, correct
        items.append(_item(f"k{i}", 1.0, 0.9))
    for i in range(4):  # clean, wrong (pred < 0.5)
        items.append(_item(f"kw{i}", 1.0, 0.1))
    return HonestCase(tuple(items), ContaminationGraph(edges=tuple(edges)), 0.8, 0.6, 0.2)


def make_specificity_control() -> HonestCase:
    """Contamination present but UNcorrelated with correctness ⇒ no gap (req A).

    Contaminated and clean items have identical accuracy (0.5 each), so honest
    must equal reported: reported = 10/20 = 0.5, honest = 5/10 = 0.5, delta = 0.
    """
    items: list[EvalItem] = []
    edges: list[ContaminationEdge] = []
    for i in range(5):
        items.append(_item(f"c{i}", 1.0, 0.9))
        edges.append(_edge(f"c{i}"))
    for i in range(5):
        items.append(_item(f"cw{i}", 1.0, 0.1))
        edges.append(_edge(f"cw{i}"))
    for i in range(5):
        items.append(_item(f"k{i}", 1.0, 0.9))
    for i in range(5):
        items.append(_item(f"kw{i}", 1.0, 0.1))
    return HonestCase(tuple(items), ContaminationGraph(edges=tuple(edges)), 0.5, 0.5, 0.0)


@dataclass(frozen=True)
class PartialCase:
    eval_items: tuple[EvalItem, ...]
    graph: ContaminationGraph
    expected_reported: float
    expected_drop_honest: float
    expected_reweight_honest: float


def make_partial_contamination() -> PartialCase:
    """A dataset where fractional reweight differs from drop.

    A borderline item (identity 0.7 -> weight 0.3) contributes partially; a
    near-duplicate (identity 1.0 -> weight 0.0) drops out. accuracy@0.5:
      reported (all 4)      = 2/4 = 0.5
      drop honest (clean)   = 1/2 = 0.5            (a correct, d wrong)
      reweight honest       = (1*1 + 0.3*1) / (1 + 0.3 + 0 + 1) = 1.3/2.3 != drop
    """
    items = (
        _item("a", 1.0, 0.9),  # clean, correct
        _item("b", 1.0, 0.9),  # borderline contaminated, correct
        _item("c", 1.0, 0.1),  # near-duplicate contaminated, wrong
        _item("d", 1.0, 0.1),  # clean, wrong
    )
    graph = ContaminationGraph(
        edges=(
            ContaminationEdge(
                eval_id="b", ref_id="r_b", score=0.7, kind=DetectorKind.SEQUENCE, detector_id="f"
            ),
            ContaminationEdge(
                eval_id="c", ref_id="r_c", score=1.0, kind=DetectorKind.SEQUENCE, detector_id="f"
            ),
        )
    )
    return PartialCase(items, graph, 0.5, 0.5, 1.3 / 2.3)


# --- Phase 4: stratification / silent-failure regimes -----------------------
#
# The difficulty axis is identity-to-nearest-reference, read straight from the
# ContaminationGraph edge scores. Items are bucketed on that axis with 4 fixed
# bins over [0, 1): edge scores 0.0 / 0.3 / 0.6 / 0.9 land in buckets 0/1/2/3.
# Metric is accuracy@0.5 (exact), labels all 1.0; prediction 0.9 = correct, 0.1 = wrong.


@dataclass(frozen=True)
class StratifyRegime:
    eval_items: tuple[EvalItem, ...]
    graph: ContaminationGraph
    n_bins: int
    expected_aggregate: float
    #: bucket index -> expected accuracy in that bucket
    expected_bucket_values: dict[int, float]
    #: bucket indices that a correct silent-failure detector must flag (may be empty)
    expected_flagged_buckets: tuple[int, ...]


def _bucket(
    prefix: str, score: float | None, n: int, prediction: float
) -> tuple[list[EvalItem], list[ContaminationEdge]]:
    items: list[EvalItem] = []
    edges: list[ContaminationEdge] = []
    for i in range(n):
        item_id = f"{prefix}{i}"
        items.append(_item(item_id, 1.0, prediction))
        if score is not None:
            edges.append(_edge(item_id, score))
    return items, edges


def make_failure_regime() -> StratifyRegime:
    """Planted silent failure: healthy headline, one difficulty bucket that fails.

    50 items across 4 identity buckets. The three low/mid-identity buckets predict
    correctly; the high-identity (near-train) bucket of 5 items is entirely wrong.
    accuracy: aggregate = 45/50 = 0.90 (looks fine), but bucket 3 = 0/5 = 0.00.
    A correct detector flags exactly bucket 3.
    """
    items: list[EvalItem] = []
    edges: list[ContaminationEdge] = []
    for prefix, score, n, pred in (
        ("clean", None, 15, 0.9),  # identity 0.0 -> bucket 0, correct
        ("low", 0.3, 15, 0.9),  # identity 0.3 -> bucket 1, correct
        ("mid", 0.6, 15, 0.9),  # identity 0.6 -> bucket 2, correct
        ("near", 0.9, 5, 0.1),  # identity 0.9 -> bucket 3, WRONG (silent failure)
    ):
        bucket_items, bucket_edges = _bucket(prefix, score, n, pred)
        items.extend(bucket_items)
        edges.extend(bucket_edges)
    return StratifyRegime(
        eval_items=tuple(items),
        graph=ContaminationGraph(edges=tuple(edges)),
        n_bins=4,
        expected_aggregate=0.9,
        expected_bucket_values={0: 1.0, 1: 1.0, 2: 1.0, 3: 0.0},
        expected_flagged_buckets=(3,),
    )


def make_failure_specificity_control() -> StratifyRegime:
    """Specificity twin (req A): performance is FLAT across the difficulty axis.

    48 items across the same 4 identity buckets; every bucket has accuracy 9/12 =
    0.75, equal to the aggregate. A correct detector must flag NOTHING (no invented
    silent failure just because difficulty varies).
    """
    items: list[EvalItem] = []
    edges: list[ContaminationEdge] = []
    for prefix, score in (("clean", None), ("low", 0.3), ("mid", 0.6), ("near", 0.9)):
        correct_items, correct_edges = _bucket(f"{prefix}_ok", score, 9, 0.9)
        wrong_items, wrong_edges = _bucket(f"{prefix}_no", score, 3, 0.1)
        items.extend(correct_items + wrong_items)
        edges.extend(correct_edges + wrong_edges)
    return StratifyRegime(
        eval_items=tuple(items),
        graph=ContaminationGraph(edges=tuple(edges)),
        n_bins=4,
        expected_aggregate=0.75,
        expected_bucket_values={0: 0.75, 1: 0.75, 2: 0.75, 3: 0.75},
        expected_flagged_buckets=(),
    )


# --- Phase 5: a representative AuditReport for renderer tests ----------------


def _traced(name: str, value: float | None, status: ResultStatus, ref: str) -> TracedValue:
    # OK requires a value (+ CI); a non-OK status forbids a value (contract invariant).
    if status is ResultStatus.OK:
        return TracedValue(
            name=name, value=value, status=status, provenance_ref=ref, ci_low=0.5, ci_high=0.95
        )
    return TracedValue(name=name, value=None, status=status, provenance_ref=ref)


def make_audit_report(
    *,
    reported_value: float = 0.875,
    honest_value: float = 0.625,
    delta_value: float = 0.25,
    reported_status: ResultStatus = ResultStatus.OK,
    honest_status: ResultStatus = ResultStatus.OK,
    delta_status: ResultStatus = ResultStatus.OK,
    prefilter_enabled: bool = True,
    version_mismatch: bool = False,
) -> AuditReport:
    """A fully-populated, deterministic AuditReport for Phase-5 renderer tests.

    Built via the real assembler so limitations are populated and ``audit_hash`` is
    computed over them. Imported lazily so importing ``tests.factories`` does not
    pull in the report layer for non-report tests.
    """
    from veritas.report import assemble_report

    provenance = ProvenanceRecord(
        input_hashes={"benchmark": "sha256:cafef00d"},
        params={
            "identity_threshold": 0.3,
            "prefilter_enabled": prefilter_enabled,
            "bootstrap_n": 1000,
        },
        seed=1729,
        pinned_versions={"mmseqs": "18.8cc5c"},
        runtime_versions={"mmseqs": "99.9.9" if version_mismatch else "18.8cc5c"},
    )
    return assemble_report(
        benchmark_name="demo-benchmark",
        reported=_traced("auroc", reported_value, reported_status, "prov:reported"),
        honest=_traced("auroc", honest_value, honest_status, "prov:honest"),
        delta=_traced("auroc_delta", delta_value, delta_status, "prov:delta"),
        leakage=LeakageSummary(n_eval=50, n_contaminated=5, per_detector={"mmseqs": 5}),
        provenance=provenance,
        prefilter_enabled=prefilter_enabled,
    )


# --- Phase 6: hermetic orchestration helpers --------------------------------
#
# A detector that returns a *planted* graph regardless of input, so the audit
# pipeline can run end-to-end with no binaries; and a fake version runner so
# runtime-version capture (req C) stays offline.


class PlantedDetector(ContaminationDetector):
    kind = DetectorKind.SEQUENCE
    supported_alphabets = frozenset({SeqType.PROTEIN})

    def __init__(
        self,
        graph: ContaminationGraph,
        detector_id: str = "planted",
        *,
        binary_path: str | None = None,
    ) -> None:
        self.detector_id = detector_id
        self.binary_path = binary_path
        self._graph = graph

    def detect(
        self,
        eval_items: Sequence[EvalItem],
        reference_items: Sequence[ReferenceItem],
        config: DetectorConfig,
    ) -> ContaminationGraph:
        return self._graph


def planted_factory(graph: ContaminationGraph) -> Callable[[str], ContaminationDetector]:
    def factory(name: str) -> ContaminationDetector:
        return PlantedDetector(graph, detector_id=name)

    return factory


def fake_version_runner(version: str = "18.8cc5c") -> Callable[[Sequence[str]], str]:
    """A capture_tool_versions runner that returns a fixed version for any tool."""

    def run(args: Sequence[str]) -> str:
        return version

    return run


#: Declared pin for the planted tool; make_golden_audit's runtime version is
#: compared against this (a different runtime => a surfaced version mismatch).
PLANTED_PINNED_VERSION = "18.8cc5c"


@dataclass(frozen=True)
class AuditCase:
    inputs: AuditInputs
    config: AuditConfig
    detector_factory: Callable[[str], ContaminationDetector]
    version_runner: Callable[[Sequence[str]], str]
    expected_reported: float
    expected_honest: float
    expected_delta: float


def make_golden_audit(*, stratify: bool = True, version: str = PLANTED_PINNED_VERSION) -> AuditCase:
    """A fully-controlled, hermetic end-to-end audit case with known metric values.

    Uses the inflation construction (accuracy: reported 0.8, honest 0.6, delta 0.2)
    with a planted contamination graph, so a full ``run_audit`` is deterministic and
    binary-free. ``version`` is the runtime version the injected runner reports; it
    is compared to the declared pin ``PLANTED_PINNED_VERSION``.
    """
    case = make_inflation_construction()
    inputs = AuditInputs(
        benchmark=Benchmark(
            name="golden",
            eval_items=case.eval_items,
            split=SplitSpec(name="test", kind="holdout"),
            metric=MetricSpec(name=MetricName.ACCURACY),
        ),
        reference_items=(ReferenceItem(id="r", seq_type=SeqType.PROTEIN, sequence="MKV"),),
    )
    config = AuditConfig(
        detectors=(
            DetectorConfig(kind=DetectorKind.SEQUENCE, name="planted", identity_threshold=0.5),
        ),
        seed=1729,
        deleak_policy=DeLeakPolicy.DROP,
        bootstrap_n=200,
        stratify_axes=("identity_to_nearest_reference",) if stratify else (),
        pinned_versions={"planted": PLANTED_PINNED_VERSION},
    )
    return AuditCase(
        inputs=inputs,
        config=config,
        detector_factory=planted_factory(case.graph),
        version_runner=fake_version_runner(version),
        expected_reported=case.expected_reported,
        expected_honest=case.expected_honest,
        expected_delta=case.expected_delta,
    )

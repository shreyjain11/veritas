"""(d) Unified PPI leakage-DETECTION demo -- FAMILY + STRUCTURAL detectors (+ sequence).

No trained model is released by Bushuiev et al. (arXiv:2404.10457), so this is
detection-only: there is no reported-vs-honest metric delta, only cross-split homology
rates. Three parts, locked to the corrected/observed numbers (docs/validation.md). We lock
QUALITATIVE assertions (orderings / floors), not exact rates, so small split nondeterminism
cannot break the demo while a real regression (a detector going silent, or crying wolf on a
clean split) still fails it.

1. Demonstration -- MMseqs2-30% sequence-similarity split (52 test / 296 train, seed 1729):
   sequence 0% BY CONSTRUCTION (the split removes every >=30%-identity/>=50%-coverage pair),
   yet family 34.6% and fold-level structural 38.5% (TM>=0.5). Bushuiev's thesis -- family
   and structure catch homology sequence-identity splitting misses -- shown by Veritas.

2. Pr/PI negative control -- a published SKEMPI Hold_out_type category genuinely independent
   of the immune training set: ~0% across all three detectors (sequence 0 / family 0 /
   structural 3.3%). Veritas does NOT false-alarm on a clean hold-out -- corroborating
   Bushuiev's qualitative finding via an INDEPENDENT method (NOT their numeric 0%).

3. Immune-category finding (co-equal) -- AB/AG and TCR/pMHC hold-outs leak 87-100% across
   ALL detectors because they share immunoglobulin-superfamily domains (C1-set, V-set;
   Ig-fold MHC). Naive interaction-type category separation does NOT remove leakage.

METHOD CAVEAT: Veritas's structural detector is FOLD-level homology (foldseek monomer
TMalign, tm = max(qtmscore, ttmscore)), a related but MORE PERMISSIVE signal than iDist's
INTERFACE-level redundancy -- the rates are NOT directly comparable.

Data: PPIRef interface PDBs + SKEMPI Hold_out_type + Pfam-A are FETCH-ONLY (pinned in
demos/ppi_bushuiev/manifest.toml); only the public-domain per-chain RCSB/PDB sequences
(vendored/chains.fasta) are committed. Opt-in (external + foldseek + mmseqs + Pfam).
"""

from __future__ import annotations

import gzip
import random
import shutil
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import polars as pl
import pyhmmer
import pytest
from pyhmmer.plan7 import HMM

from tests.e2e import demo_data_or_skip
from veritas.contamination.backends.foldseek import FoldseekSearch
from veritas.contamination.backends.mmseqs import MmseqsSearch
from veritas.contamination.backends.pyhmmer_search import PyhmmerSearch
from veritas.contamination.family import FamilyDetector
from veritas.contamination.sequence_identity import SequenceIdentityDetector
from veritas.contamination.structural import StructuralDetector
from veritas.contracts import (
    ContaminationEdge,
    DetectorConfig,
    DetectorKind,
    EvalItem,
    ReferenceItem,
    SeqType,
)
from veritas.io.fasta import read_fasta

pytestmark = [pytest.mark.external, pytest.mark.requires_foldseek, pytest.mark.requires_mmseqs]

_CHAINS_FASTA = Path(__file__).resolve().parents[2] / "demos/ppi_bushuiev/vendored/chains.fasta"
_SEED = 1729
_SEQ_ID, _SEQ_COV = 0.30, 0.50
_TM = 0.50
_EVALUE = 1e-3
_TEST_FRACTION = 0.15
_N_INTERFACES, _N_CHAINS = 348, 921
# A hand-verified vendored row: 1A22 is human growth hormone bound to its receptor; chain A
# (the hormone) begins FPTIPLSRLFDNAML... Guards the committed slice against silent drift.
_REAL_ROW_ID = "1A22_A_B__A"
_REAL_ROW_PREFIX = "FPTIPLSRLFDNAML"
_CATEGORIES = ("Pr/PI", "AB/AG", "TCR/pMHC")


def _iface_of(chain_id: str) -> str:
    return chain_id.rsplit("__", 1)[0]


def _locate_pfam(root: Path) -> Path:
    for candidate in (root / "Pfam-A.hmm", root / "pfam" / "Pfam-A.hmm"):
        if candidate.exists():
            return candidate
    for gz in (root / "Pfam-A.hmm.gz", root / "pfam" / "Pfam-A.hmm.gz"):
        if gz.exists():
            out = gz.with_suffix("")
            with gzip.open(gz, "rb") as fh, out.open("wb") as dst:
                shutil.copyfileobj(fh, dst)
            return out
    pytest.skip(f"Pfam-A.hmm not found under {root} (needed for the family detector)")


def _categories_by_interface(root: Path, interfaces: list[str]) -> dict[str, str]:
    csv = root / "skempi_v2.csv"
    if not csv.exists():
        pytest.skip(f"skempi_v2.csv not found under {root}")
    frame = pl.read_csv(csv, separator=";", infer_schema_length=0)
    by_prefix: dict[str, str] = {}
    for row in frame.iter_rows(named=True):
        prefix, hold_out = row["#Pdb"].split("_")[0].upper(), (row["Hold_out_type"] or "")
        if prefix not in by_prefix or (not by_prefix[prefix] and hold_out):
            by_prefix[prefix] = hold_out
    return {i: by_prefix.get(i.split("_")[0].upper(), "") for i in interfaces}


def _interface_pdb_map(root: Path) -> dict[str, Path]:
    return {p.stem: p for p in root.rglob("*.pdb")}


@dataclass(frozen=True)
class _Rates:
    sequence: float
    family: float
    structural: float
    n_test: int
    n_train: int


@dataclass(frozen=True)
class _PPI:
    demonstration: _Rates
    struct_sweep: dict[float, float]
    control: dict[str, _Rates]
    n_interfaces: int
    n_chains: int
    real_row_ok: bool


def _cross_interface(edges: tuple[ContaminationEdge, ...]) -> list[tuple[str, str]]:
    return [
        (_iface_of(e.eval_id), _iface_of(e.ref_id))
        for e in edges
        if _iface_of(e.eval_id) != _iface_of(e.ref_id)
    ]


@pytest.fixture(scope="module")
def ppi() -> _PPI:
    root = Path(demo_data_or_skip("ppi_bushuiev"))
    if not _CHAINS_FASTA.exists():  # pragma: no cover - committed slice
        pytest.skip(f"vendored chains.fasta missing: {_CHAINS_FASTA}")

    records = read_fasta(_CHAINS_FASTA, seq_type=SeqType.PROTEIN)
    chain_seq = {r.id: r.sequence for r in records}
    real_row_ok = chain_seq.get(_REAL_ROW_ID, "").startswith(_REAL_ROW_PREFIX)
    interfaces = sorted({_iface_of(cid) for cid in chain_seq})
    pdbs = _interface_pdb_map(root)
    missing = [i for i in interfaces if i not in pdbs]
    if missing:
        pytest.skip(f"{len(missing)} interface PDBs missing under {root} (e.g. {missing[:3]})")

    eval_chains = tuple(
        EvalItem(id=c, seq_type=SeqType.PROTEIN, sequence=s, label=0.0)
        for c, s in chain_seq.items()
    )
    ref_chains = tuple(
        ReferenceItem(id=c, seq_type=SeqType.PROTEIN, sequence=s) for c, s in chain_seq.items()
    )
    eval_ifaces = tuple(
        EvalItem(
            id=i,
            seq_type=SeqType.PROTEIN,
            sequence=chain_seq[f"{i}__{_first_chain(i, chain_seq)}"],
            label=0.0,
            structure_path=pdbs[i],
        )
        for i in interfaces
    )
    ref_ifaces = tuple(
        ReferenceItem(
            id=i,
            seq_type=SeqType.PROTEIN,
            sequence=chain_seq[f"{i}__{_first_chain(i, chain_seq)}"],
            structure_path=pdbs[i],
        )
        for i in interfaces
    )

    # --- detectors, ALL-VS-ALL once (Veritas's real classes) ---
    seq_edges = _cross_interface(
        SequenceIdentityDetector(MmseqsSearch(), use_prefilter=False)
        .detect(
            eval_chains,
            ref_chains,
            DetectorConfig(
                kind=DetectorKind.SEQUENCE,
                name="mmseqs",
                identity_threshold=_SEQ_ID,
                coverage_threshold=_SEQ_COV,
            ),
        )
        .edges
    )
    fam_edges = _cross_interface(
        FamilyDetector(PyhmmerSearch(hmms=_load_pfam(root)))
        .detect(
            eval_chains,
            ref_chains,
            DetectorConfig(kind=DetectorKind.FAMILY, name="pyhmmer", e_value_threshold=_EVALUE),
        )
        .edges
    )
    struct_graph = StructuralDetector(FoldseekSearch(timeout=3600.0)).detect(
        eval_ifaces,
        ref_ifaces,
        DetectorConfig(kind=DetectorKind.STRUCTURE, name="foldseek", score_threshold=0.0),
    )
    struct_edges = [
        (e.eval_id, e.ref_id, e.score) for e in struct_graph.edges if e.eval_id != e.ref_id
    ]

    def leak(test: set[str], train: set[str], pairs: list[tuple[str, str]]) -> float:
        return len({e for e, r in pairs if e in test and r in train}) / max(len(test), 1)

    def leak_struct(test: set[str], train: set[str], tm: float) -> float:
        hit = {e for e, r, s in struct_edges if s >= tm and e in test and r in train}
        return len(hit) / max(len(test), 1)

    def rates(test: set[str], train: set[str]) -> _Rates:
        return _Rates(
            sequence=leak(test, train, seq_edges),
            family=leak(test, train, fam_edges),
            structural=leak_struct(test, train, _TM),
            n_test=len(test),
            n_train=len(train),
        )

    # --- MMseqs2-30% split: components of the sequence graph -> whole components to test ---
    parent = {i: i for i in interfaces}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for e, r in seq_edges:
        parent[find(e)] = find(r)
    comps: dict[str, list[str]] = defaultdict(list)
    for i in interfaces:
        comps[find(i)].append(i)
    components = sorted(comps.values(), key=lambda c: (-len(c), c[0]))
    order = components[:]
    random.Random(_SEED).shuffle(order)
    test: set[str] = set()
    target = round(_TEST_FRACTION * len(interfaces))
    for comp in order:
        if len(test) >= target:
            break
        test.update(comp)
    train = set(interfaces) - test
    demonstration = rates(test, train)
    sweep = {tm: leak_struct(test, train, tm) for tm in (0.4, 0.5, 0.6, 0.7)}

    # --- category controls ---
    categories = _categories_by_interface(root, interfaces)
    categorized = {i for i in interfaces if categories[i] in _CATEGORIES}
    control = {
        held: rates(
            {i for i in categorized if categories[i] == held},
            {i for i in categorized if categories[i] != held},
        )
        for held in _CATEGORIES
    }
    return _PPI(
        demonstration=demonstration,
        struct_sweep=sweep,
        control=control,
        n_interfaces=len(interfaces),
        n_chains=len(chain_seq),
        real_row_ok=real_row_ok,
    )


def _first_chain(interface: str, chain_seq: dict[str, str]) -> str:
    return sorted(c.rsplit("__", 1)[1] for c in chain_seq if _iface_of(c) == interface)[0]


def _load_pfam(root: Path) -> tuple[HMM, ...]:
    with pyhmmer.plan7.HMMFile(str(_locate_pfam(root))) as handle:
        return tuple(handle)


def test_vendored_chains_slice_is_intact(ppi: _PPI) -> None:
    # The committed public-domain sequence slice: shape + a hand-verified real row.
    assert ppi.n_interfaces == _N_INTERFACES
    assert ppi.n_chains == _N_CHAINS
    assert ppi.real_row_ok, f"{_REAL_ROW_ID} should start with {_REAL_ROW_PREFIX!r}"


def test_demonstration_split_structure_and_family_catch_what_sequence_misses(ppi: _PPI) -> None:
    d = ppi.demonstration
    assert d.n_test >= 40  # the constructed split is non-degenerate
    # sequence is 0 BY CONSTRUCTION (split removes every >=30%-id/>=50%-cov pair).
    assert d.sequence == 0.0
    # family and structure find SUBSTANTIAL residual homology (observed 0.346 / 0.385).
    assert d.family > 0.20
    assert d.structural > 0.20
    # the ordering is the claim: sequence << family, structural.
    assert d.sequence < d.family and d.sequence < d.structural
    # fold-level structural is threshold-dependent (observed 0.731/0.385/0.135/0.0) -- it must
    # decay monotonically as the TM bar rises, which is what makes "fold-level" honest.
    sweep = ppi.struct_sweep
    assert sweep[0.4] >= sweep[0.5] >= sweep[0.6] >= sweep[0.7]


def test_prpi_control_is_near_zero_across_all_detectors(ppi: _PPI) -> None:
    c = ppi.control["Pr/PI"]
    # genuinely independent of the immune training set: sequence + family EXACTLY zero.
    assert c.sequence == 0.0
    assert c.family == 0.0
    # fold-level structural is near-zero (observed 0.033) -- Veritas does not cry wolf.
    assert c.structural <= 0.10


@pytest.mark.parametrize("held", ["AB/AG", "TCR/pMHC"])
def test_immune_category_separation_does_not_remove_leakage(ppi: _PPI, held: str) -> None:
    c = ppi.control[held]
    # shared immunoglobulin domains -> heavy leakage on EVERY detector (observed 0.87-1.0).
    assert c.sequence >= 0.80
    assert c.family >= 0.80
    assert c.structural >= 0.80

"""Operations over ContaminationGraph: union, intersect, filter, summaries."""

from __future__ import annotations

from veritas.contracts import ContaminationEdge, ContaminationGraph


def _edge_key(edge: ContaminationEdge) -> tuple[str, str, str, str]:
    return (edge.eval_id, edge.ref_id, str(edge.kind), edge.detector_id)


def union(*graphs: ContaminationGraph) -> ContaminationGraph:
    """All edges from all graphs, deduped by (eval_id, ref_id, kind, detector_id)."""
    seen: dict[tuple[str, str, str, str], ContaminationEdge] = {}
    for graph in graphs:
        for edge in graph.edges:
            seen.setdefault(_edge_key(edge), edge)
    return ContaminationGraph(edges=tuple(seen.values()))


def intersect(*graphs: ContaminationGraph) -> ContaminationGraph:
    """Edges whose (eval_id, ref_id) pair appears in *every* graph (deduped)."""
    if not graphs:
        return ContaminationGraph(edges=())
    pair_sets = [{(e.eval_id, e.ref_id) for e in g.edges} for g in graphs]
    common = set.intersection(*pair_sets)
    seen: dict[tuple[str, str, str, str], ContaminationEdge] = {}
    for graph in graphs:
        for edge in graph.edges:
            if (edge.eval_id, edge.ref_id) in common:
                seen.setdefault(_edge_key(edge), edge)
    return ContaminationGraph(edges=tuple(seen.values()))


def filter_by_score(graph: ContaminationGraph, min_score: float) -> ContaminationGraph:
    return ContaminationGraph(edges=tuple(e for e in graph.edges if e.score >= min_score))


def contaminated_eval_ids(graph: ContaminationGraph) -> frozenset[str]:
    return frozenset(edge.eval_id for edge in graph.edges)


def nearest_score_by_eval(graph: ContaminationGraph) -> dict[str, float]:
    """For each eval item, the highest edge score (its closest reference match)."""
    best: dict[str, float] = {}
    for edge in graph.edges:
        if edge.eval_id not in best or edge.score > best[edge.eval_id]:
            best[edge.eval_id] = edge.score
    return best

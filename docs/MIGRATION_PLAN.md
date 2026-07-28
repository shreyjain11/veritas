# v1 to v2 migration

| v1 area | v2 disposition |
| --- | --- |
| sequence `EvalItem` / `ReferenceItem` | remains legacy bio domain |
| `ContaminationGraph` | remains a bio detector artifact |
| reported-versus-honest score | replaced by neutral canonical/robust/fresh scores |
| FASTA and binary adapters | remain optional bio dependencies |
| report viewer | accepts v1 reports and adds schema-v2 rendering |

The initial v2 code lives in `veritas.benchmark_integrity` so imports of the validated v1 biological package remain stable while individual modules are moved behind `veritas.domains.bio` in follow-up compatibility releases.

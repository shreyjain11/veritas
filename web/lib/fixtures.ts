import type { AuditReport } from "./audit-report";
import ppiInterface from "../fixtures/ppi_interface.json";
import proteingymMsaDepth from "../fixtures/proteingym_msa_depth.json";
import r2ReverseComplement from "../fixtures/r2_reverse_complement.json";
import r3Chr8Chr9 from "../fixtures/r3_chr8_chr9.json";
import r3Random from "../fixtures/r3_random.json";

export interface FixtureEntry {
  id: string;
  /** Short rail label. */
  label: string;
  /** One-line description of what this audit shows. */
  blurb: string;
  report: AuditReport;
}

/** The five locked demo reports, bundled so the viewer renders them offline. */
export const FIXTURES: FixtureEntry[] = [
  {
    id: "r3_random",
    label: "OverfitNN · random split",
    blurb: "Reported→honest collapse: all of the apparent signal is leakage.",
    report: r3Random as unknown as AuditReport,
  },
  {
    id: "r3_chr8_chr9",
    label: "OverfitNN · chr8+chr9",
    blurb: "Residual leakage survives a chromosome-aware split.",
    report: r3Chr8Chr9 as unknown as AuditReport,
  },
  {
    id: "ppi_interface",
    label: "PPI · interface leakage",
    blurb: "Splits-matrix: sequence-blind splitting misses family + fold leakage.",
    report: ppiInterface as unknown as AuditReport,
  },
  {
    id: "r2_reverse_complement",
    label: "hashFrag · reverse-complement",
    blurb: "A naive genomic split leaves 80.8% reverse-complement duplicates.",
    report: r2ReverseComplement as unknown as AuditReport,
  },
  {
    id: "proteingym_msa_depth",
    label: "ProteinGym · MSA depth",
    blurb: "Performance rises with alignment depth (a difficulty gradient).",
    report: proteingymMsaDepth as unknown as AuditReport,
  },
];

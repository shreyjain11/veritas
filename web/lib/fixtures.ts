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
  /** One-line description of what this audit shows (viewer rail). */
  blurb: string;
  /** The evidence sentence for the landing proof card. */
  finding: string;
  report: AuditReport;
}

/** The five locked demo reports, bundled so the viewer renders them offline. */
export const FIXTURES: FixtureEntry[] = [
  {
    id: "r3_random",
    label: "OverfitNN · random split",
    blurb: "Reported→honest collapse: all of the apparent signal is leakage.",
    finding:
      "A memorizer with no understanding of regulation scores 0.165; its honest score is 0.018 — a statistical null. 89% was leakage.",
    report: r3Random as unknown as AuditReport,
  },
  {
    id: "r3_chr8_chr9",
    label: "OverfitNN · chr8+chr9",
    blurb: "Residual leakage survives a chromosome-aware split.",
    finding:
      "Even holding out whole chromosomes leaves residual leakage: 0.074 reported, 0.030 honest.",
    report: r3Chr8Chr9 as unknown as AuditReport,
  },
  {
    id: "ppi_interface",
    label: "PPI · interface leakage",
    blurb: "Splits-matrix: sequence-blind splitting misses family + fold leakage.",
    finding:
      "A 30%-identity sequence split leaves family + fold leakage the sequence detector can't see; a published control stays near zero.",
    report: ppiInterface as unknown as AuditReport,
  },
  {
    id: "r2_reverse_complement",
    label: "hashFrag · reverse-complement",
    blurb: "A naive genomic split leaves 80.8% reverse-complement duplicates.",
    finding:
      "On a naive genomic split, 80.8% of test sequences are exact reverse-complements of training sequences.",
    report: r2ReverseComplement as unknown as AuditReport,
  },
  {
    id: "proteingym_msa_depth",
    label: "ProteinGym · MSA depth",
    blurb: "Performance rises with alignment depth (a difficulty gradient).",
    finding:
      "Variant-effect performance rises with alignment depth: 0.298 (low) → 0.384 → 0.531 (high).",
    report: proteingymMsaDepth as unknown as AuditReport,
  },
];

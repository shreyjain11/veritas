import type { Metadata } from "next";

import { Viewer } from "../../components/viewer/Viewer";

export const metadata: Metadata = {
  title: "Report viewer — Veritas",
  description:
    "Render an AuditReport: the reported→honest collapse, leakage splits-matrix, stratification curves, provenance, and in-browser audit_hash verification.",
};

export default function ReportPage() {
  return <Viewer />;
}

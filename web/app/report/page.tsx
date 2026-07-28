import type { Metadata } from "next";

import { V2Viewer } from "../../components/viewer/V2Viewer";

export const metadata: Metadata = {
  title: "Benchmark integrity report viewer — Veritas",
  description:
    "Render a schema-v2 benchmark-integrity audit with evidence matrix, score robustness, limitations, and provenance.",
};

export default function ReportPage() {
  return <V2Viewer />;
}

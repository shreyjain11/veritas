import type { Metadata } from "next";

import { Footer } from "../../components/Footer";
import { Nav } from "../../components/landing/Nav";
import { V2Viewer } from "../../components/viewer/V2Viewer";

export const metadata: Metadata = {
  title: "Benchmark integrity report viewer — Veritas",
  description:
    "Render a schema-v2 benchmark-integrity audit with verdicts, evidence matrix, item-level variants, limitations, and a re-verified audit hash.",
};

export default function ReportPage() {
  return (
    <>
      <Nav />
      <V2Viewer />
      <div className="mx-auto max-w-[1240px] px-5 pb-10 sm:px-8">
        <Footer />
      </div>
    </>
  );
}

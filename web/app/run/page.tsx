import type { Metadata } from "next";

import { Footer } from "../../components/Footer";
import { Nav } from "../../components/landing/Nav";
import { AuditRunner } from "../../components/run/AuditRunner";

export const metadata: Metadata = {
  title: "Run a benchmark audit — Veritas",
  description:
    "Use your own model-provider key to run a bounded benchmark-integrity audit in the browser.",
};

export default function RunPage() {
  return (
    <>
      <Nav />
      <AuditRunner />
      <div className="mx-auto max-w-[1180px] px-5 pb-10 sm:px-8">
        <Footer />
      </div>
    </>
  );
}

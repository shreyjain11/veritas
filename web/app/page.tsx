import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

import type { AuditReport } from "../lib/audit-report";

// PLACEHOLDER deploy smoke-test page (not the real viewer/landing — those are step 4).
// It reads the committed fixtures at build time, proving fixtures + generated types +
// static export all compose. Replaced by the report viewer + landing once the design
// system is built.
const FIXTURES_DIR = join(process.cwd(), "fixtures");

function loadFixtures(): AuditReport[] {
  return readdirSync(FIXTURES_DIR)
    .filter((name) => name.endsWith(".json"))
    .map((name) => JSON.parse(readFileSync(join(FIXTURES_DIR, name), "utf8")) as AuditReport);
}

export default function Page() {
  const reports = loadFixtures();
  return (
    <main style={{ fontFamily: "ui-monospace, monospace", padding: "2rem", maxWidth: 720 }}>
      <h1>Veritas</h1>
      <p>Model-agnostic leakage &amp; robustness auditor. Report viewer — coming soon.</p>
      <ul>
        {reports.map((report) => (
          <li key={report.benchmark_name}>
            <code>{report.benchmark_name}</code> — {report.report_kind} · {report.audit_hash.slice(0, 12)}…
          </li>
        ))}
      </ul>
    </main>
  );
}

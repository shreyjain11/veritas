import { readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import type { AuditReport } from "../lib/audit-report";
import { verifyAuditHash } from "../lib/verify";

const here = dirname(fileURLToPath(import.meta.url));
const fixturesDir = join(here, "..", "fixtures");
const fixtures = readdirSync(fixturesDir).filter((f) => f.endsWith(".json"));

function load(name: string): AuditReport {
  return JSON.parse(readFileSync(join(fixturesDir, name), "utf8")) as AuditReport;
}

describe("audit_hash re-verifies in-browser (the TS port matches Python)", () => {
  it.each(fixtures)("%s re-derives its stored audit_hash", async (name) => {
    const result = await verifyAuditHash(load(name));
    // Stored hashes were produced by Python; a match proves byte-identical canonicalization.
    expect(result.computed).toBe(result.stored);
    expect(result.ok).toBe(true);
  });

  it("flags a tampered report (one changed matrix cell breaks the hash)", async () => {
    const report = load("ppi_interface.json");
    const cell = report.splits?.[0]?.cells?.[0];
    if (cell === undefined) throw new Error("expected a detection cell");
    cell.n_flagged += 1;
    const result = await verifyAuditHash(report);
    expect(result.ok).toBe(false);
  });
});

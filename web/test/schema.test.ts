import { readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import Ajv2020 from "ajv/dist/2020";
import { describe, expect, it } from "vitest";

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = join(here, "..", "..");
const fixturesDir = join(here, "..", "fixtures");

const schema = JSON.parse(
  readFileSync(join(repoRoot, "schema", "audit-report.schema.json"), "utf8"),
);
const fixtures = readdirSync(fixturesDir).filter((f) => f.endsWith(".json"));

const ajv = new Ajv2020({ allErrors: true, strict: false });
const validate = ajv.compile(schema);

describe("committed fixtures validate against the exported JSON Schema", () => {
  it("there are fixtures to check", () => {
    expect(fixtures.length).toBeGreaterThan(0);
  });

  it.each(fixtures)("%s is a valid AuditReport", (name) => {
    const data = JSON.parse(readFileSync(join(fixturesDir, name), "utf8"));
    const ok = validate(data);
    expect(validate.errors ?? []).toEqual([]);
    expect(ok).toBe(true);
  });

  it("rejects a report missing a required field", () => {
    const first = fixtures[0];
    if (first === undefined) throw new Error("no fixtures");
    const data = JSON.parse(readFileSync(join(fixturesDir, first), "utf8"));
    delete data.benchmark_name;
    expect(validate(data)).toBe(false);
  });
});

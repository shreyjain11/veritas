import { describe, expect, it } from "vitest";

import sample from "../fixtures/v2/sample_report.json";
import { canonicalV2Json, pythonFloatRepr, v2ReportHash, verifyV2Report } from "../lib/v2-hash";

describe("schema-v2 audit hash (Python parity)", () => {
  it.each([
    [0.1, "0.1"],
    [3, "3"],
    [-0, "0"],
    [1e-7, "1e-07"],
    [-2.5e-12, "-2.5e-12"],
    [0.0001, "0.0001"],
    [123.456, "123.456"],
    [1e16, "10000000000000000"],
    [0.30000000000000004, "0.30000000000000004"],
    [1.5e300, BigInt(1.5e300).toString()],
    [1234567890123.5, "1234567890123.5"],
  ])("formats %s like Python repr", (value, expected) => {
    expect(pythonFloatRepr(value)).toBe(expected);
  });

  it("matches the vector pinned in tests/benchmark_integrity/test_service_logic.py", async () => {
    const vector = { audit_hash: "ignored", x: 0.1, y: 3.0, z: "é", p: 1e-7, big: 1e16, n: [1.5e300, -2.5e-12] };
    expect(canonicalV2Json({ z: "é", a: [true, null] })).toBe('{"a":[true,null],"z":"\\u00e9"}');
    expect(await v2ReportHash(vector)).toBe("7fea7cae1e900571941817cf84637d69a6561e501710fa109721bb6ca62292ba");
  });

  it("verifies the Python-generated sample report and detects tampering", async () => {
    const report = structuredClone(sample) as unknown as Record<string, unknown>;
    expect((await verifyV2Report(report)).ok).toBe(true);
    (report.score as Record<string, unknown>).robust_score = 0.99;
    expect((await verifyV2Report(report)).ok).toBe(false);
  });
});

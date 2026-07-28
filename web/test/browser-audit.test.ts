import { describe, expect, it } from "vitest";

import {
  MAX_BROWSER_ITEMS,
  requestCount,
  validateBrowserAuditRequest,
} from "../lib/browser-audit";

const valid = {
  provider: "together",
  apiKey: "secret-key-for-one-run",
  model: "meta-llama/Llama-3.3-70B-Instruct-Turbo",
  benchmark: "mmlu",
  itemCount: 10,
  offset: 0,
  acknowledgeExternalTransfer: true,
};

describe("browser audit request boundary", () => {
  it("computes the canonical plus two transformed requests", () => {
    expect(requestCount(10)).toBe(30);
    expect(requestCount(MAX_BROWSER_ITEMS)).toBe(60);
  });

  it("accepts a bounded acknowledged request without changing the key", () => {
    expect(validateBrowserAuditRequest(valid)).toEqual(valid);
  });

  it.each([
    [{ ...valid, provider: "custom" }, "Unsupported provider"],
    [{ ...valid, benchmark: "private_dataset" }, "Unsupported benchmark"],
    [{ ...valid, itemCount: MAX_BROWSER_ITEMS + 1 }, "Item count"],
    [{ ...valid, apiKey: "bad\nkey" }, "API key"],
    [{ ...valid, model: "bad\nmodel" }, "Model ID"],
    [{ ...valid, acknowledgeExternalTransfer: false }, "must be acknowledged"],
  ])("rejects invalid or unsafe input", (input, message) => {
    expect(() => validateBrowserAuditRequest(input)).toThrow(message);
  });
});

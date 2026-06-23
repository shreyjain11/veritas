import { describe, expect, it } from "vitest";

import { canonicalJson } from "../lib/canonical";

// Reference strings produced by veritas.provenance.canonical.canonical_json (Python).
describe("canonicalJson matches the Python encoder byte-for-byte", () => {
  it("sorts keys, uses compact separators, and handles primitives", () => {
    expect(canonicalJson({ b: 1, a: 0.298, z: [3, 1, 2], n: null, t: true })).toBe(
      '{"a":0.298,"b":1,"n":null,"t":true,"z":[3,1,2]}',
    );
  });

  it("applies ensure_ascii escaping incl. non-BMP surrogate pairs and short escapes", () => {
    expect(canonicalJson({ quote: 'a"b\\c', tab: "a\tb", unicode: "café — 😀" })).toBe(
      '{"quote":"a\\"b\\\\c","tab":"a\\tb","unicode":"caf\\u00e9 \\u2014 \\ud83d\\ude00"}',
    );
  });

  it("nests objects and renders a negative non-integer float and an integer", () => {
    expect(canonicalJson({ nested: { y: 2, x: 1 }, neg: -0.016, int: 20000 })).toBe(
      '{"int":20000,"neg":-0.016,"nested":{"x":1,"y":2}}',
    );
  });

  it("normalizes -0 to 0 and rejects non-finite numbers", () => {
    expect(canonicalJson(-0)).toBe("0");
    expect(() => canonicalJson(Infinity)).toThrow();
    expect(() => canonicalJson(NaN)).toThrow();
  });
});

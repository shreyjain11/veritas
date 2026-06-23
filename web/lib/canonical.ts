/**
 * Canonical JSON, byte-identical to veritas.provenance.canonical (the Python encoder).
 *
 * This is the basis for client-side audit_hash re-verification, so it MUST reproduce the
 * Python output exactly for the values that appear in hashed report content:
 *   - object keys sorted lexicographically, compact separators ("," and ":"), no spaces;
 *   - ensure_ascii escaping: control chars and every code unit > 0x7e become \uXXXX
 *     (lowercase hex), with the short forms \b \t \n \f \r \" \\;
 *   - numbers use JS's shortest round-tripping repr, which matches Python's float repr for
 *     the (non-integer-valued) floats that appear in report content; -0 normalizes to 0.
 *
 * Note: Python prints an integer-valued float as "1.0" while JS prints "1"; the hashable
 * content deliberately contains no integer-valued floats (counts/indices are ints, metrics
 * are non-integer), so this divergence cannot occur here. If it ever did, the hash gate
 * (web/test/hash.test.ts) would fail loudly rather than silently mis-verify.
 */

export function canonicalJson(value: unknown): string {
  return serialize(value);
}

function serialize(v: unknown): string {
  if (v === null) return "null";
  const t = typeof v;
  if (t === "boolean") return v ? "true" : "false";
  if (t === "number") return formatNumber(v as number);
  if (t === "string") return formatString(v as string);
  if (Array.isArray(v)) return "[" + v.map(serialize).join(",") + "]";
  if (t === "object") {
    const obj = v as Record<string, unknown>;
    const keys = Object.keys(obj).sort();
    return "{" + keys.map((k) => formatString(k) + ":" + serialize(obj[k])).join(",") + "}";
  }
  throw new Error(`cannot canonicalize value of type ${t}`);
}

function formatNumber(n: number): string {
  if (!Number.isFinite(n)) {
    throw new Error(`non-finite number cannot be canonicalized: ${n}`);
  }
  if (Object.is(n, -0)) return "0";
  return String(n);
}

const SHORT_ESCAPES: Record<number, string> = {
  0x08: "\\b",
  0x09: "\\t",
  0x0a: "\\n",
  0x0c: "\\f",
  0x0d: "\\r",
  0x22: '\\"',
  0x5c: "\\\\",
};

function formatString(s: string): string {
  let out = '"';
  for (let i = 0; i < s.length; i++) {
    const code = s.charCodeAt(i);
    const short = SHORT_ESCAPES[code];
    if (short !== undefined) {
      out += short;
    } else if (code < 0x20 || code > 0x7e) {
      out += "\\u" + code.toString(16).padStart(4, "0");
    } else {
      out += s[i];
    }
  }
  return out + '"';
}

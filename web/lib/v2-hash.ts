/**
 * Schema-v2 audit_hash, byte-identical to veritas.benchmark_integrity.hashing (Python).
 *
 * The hash is SHA-256 over the canonical JSON of the whole report minus `audit_hash`:
 * sorted keys, compact separators, ASCII-only escaping, integer-valued numbers written
 * as integers, and other numbers in Python's float `repr` (fixed notation for decimal
 * exponents -4..15, otherwise `1e-07` style). A JSON round-trip through JavaScript
 * cannot distinguish 1.0 from 1, which is why Python canonicalizes both to `1` too.
 * The shared vector in test/v2-hash.test.ts pins both implementations together.
 */

import { formatString } from "./canonical";

export function pythonFloatRepr(value: number): string {
  if (!Number.isFinite(value)) throw new Error(`non-finite number cannot be hashed: ${value}`);
  if (Number.isInteger(value)) return BigInt(value).toString();
  // toExponential() with no argument yields the shortest round-tripping digits.
  const [mantissa = "", exponentText = "0"] = value.toExponential().split("e");
  const negative = mantissa.startsWith("-");
  const digits = mantissa.replace("-", "").replace(".", "");
  const exponent = Number(exponentText);
  let body: string;
  if (exponent >= -4 && exponent < 16) {
    if (exponent >= 0) {
      const integerDigits = exponent + 1;
      body = `${digits.slice(0, integerDigits).padEnd(integerDigits, "0")}.${digits.slice(integerDigits) || "0"}`;
    } else {
      body = `0.${"0".repeat(-exponent - 1)}${digits}`;
    }
  } else {
    const head = digits.length > 1 ? `${digits[0]}.${digits.slice(1)}` : digits;
    body = `${head}e${exponent < 0 ? "-" : "+"}${String(Math.abs(exponent)).padStart(2, "0")}`;
  }
  return negative ? `-${body}` : body;
}

export function canonicalV2Json(value: unknown): string {
  if (value === null || value === undefined) return "null";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "number") return pythonFloatRepr(value);
  if (typeof value === "string") return formatString(value);
  if (Array.isArray(value)) return `[${value.map(canonicalV2Json).join(",")}]`;
  if (typeof value === "object") {
    const record = value as Record<string, unknown>;
    const keys = Object.keys(record)
      .filter((key) => record[key] !== undefined)
      .sort();
    return `{${keys.map((key) => `${formatString(key)}:${canonicalV2Json(record[key])}`).join(",")}}`;
  }
  throw new Error(`cannot canonicalize value of type ${typeof value}`);
}

async function sha256Hex(text: string): Promise<string> {
  const digest = await globalThis.crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

/** The audit hash of a v2 report object; its own `audit_hash` field is ignored. */
export async function v2ReportHash(report: Record<string, unknown>): Promise<string> {
  const { audit_hash: _ignored, ...content } = report;
  return sha256Hex(canonicalV2Json(content));
}

export async function verifyV2Report(
  report: Record<string, unknown>,
): Promise<{ ok: boolean; computed: string; stored: string }> {
  const computed = await v2ReportHash(report);
  const stored = String(report.audit_hash ?? "");
  return { ok: computed === stored, computed, stored };
}

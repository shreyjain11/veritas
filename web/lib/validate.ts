import type { ErrorObject, ValidateFunction } from "ajv";
import Ajv2020 from "ajv/dist/2020";

import type { AuditReport } from "./audit-report";
import schema from "./report-schema.json";

// Lazy-compiled so ajv + the schema land in a separate chunk, loaded only when a user
// actually ingests a report (the bundled fixtures are already valid by construction).
let compiled: ValidateFunction | null = null;

function validator(): ValidateFunction {
  if (!compiled) {
    const ajv = new Ajv2020({ allErrors: true, strict: false });
    compiled = ajv.compile(schema as object);
  }
  return compiled;
}

export type ValidateResult =
  | { ok: true; report: AuditReport }
  | { ok: false; errors: string[] };

function describe(error: ErrorObject): string {
  const where = error.instancePath ? error.instancePath.replace(/^\//, "").replace(/\//g, ".") : "report";
  return `${where} ${error.message ?? "is invalid"}`;
}

/** Validate parsed JSON against the AuditReport schema; returns the report or field errors. */
export function validateReport(data: unknown): ValidateResult {
  const validate = validator();
  if (validate(data)) return { ok: true, report: data as AuditReport };
  const errors = (validate.errors ?? []).slice(0, 4).map(describe);
  return { ok: false, errors: errors.length ? errors : ["does not match the AuditReport schema"] };
}

"use client";

import { useEffect, useState } from "react";

import type { AuditReport } from "./audit-report";
import { verifyAuditHash, type VerifyResult } from "./verify";

export type SealStatus = "verifying" | "verified" | "mismatch";

export interface VerifyState {
  status: SealStatus;
  result: VerifyResult | null;
}

/** Re-verifies a report's audit_hash in the browser; shared by the seal + the tamper banner. */
export function useVerify(report: AuditReport): VerifyState {
  const [state, setState] = useState<VerifyState>({ status: "verifying", result: null });
  useEffect(() => {
    let active = true;
    setState({ status: "verifying", result: null });
    verifyAuditHash(report)
      .then((result) => {
        if (active) setState({ status: result.ok ? "verified" : "mismatch", result });
      })
      .catch(() => {
        if (active) setState({ status: "mismatch", result: null });
      });
    return () => {
      active = false;
    };
  }, [report]);
  return state;
}

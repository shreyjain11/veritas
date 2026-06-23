"use client";

import { CircleCheck, Loader, ShieldAlert } from "lucide-react";
import { useEffect, useState } from "react";

import type { AuditReport } from "../../lib/audit-report";
import { cn } from "../../lib/cn";
import { verifyAuditHash, type VerifyResult } from "../../lib/verify";

type SealState =
  | { status: "verifying" }
  | { status: "verified"; result: VerifyResult }
  | { status: "mismatch"; result?: VerifyResult };

/** Re-computes the audit_hash in the browser and shows a tamper-evident seal. */
export function HashSeal({ report }: { report: AuditReport }) {
  const [state, setState] = useState<SealState>({ status: "verifying" });

  useEffect(() => {
    let active = true;
    setState({ status: "verifying" });
    verifyAuditHash(report)
      .then((result) => {
        if (!active) return;
        setState({ status: result.ok ? "verified" : "mismatch", result });
      })
      .catch(() => active && setState({ status: "mismatch" }));
    return () => {
      active = false;
    };
  }, [report]);

  const verified = state.status === "verified";
  const verifying = state.status === "verifying";

  return (
    <div
      className={cn(
        "rounded-md border px-3 py-2.5 transition-colors",
        verifying && "border-line bg-elevated",
        verified && "border-iris/40 bg-iris-dim",
        state.status === "mismatch" && "border-danger/50 bg-danger-dim",
      )}
    >
      <div className="flex items-center gap-2">
        {verifying && <Loader className="size-3.5 animate-spin text-muted" aria-hidden />}
        {verified && <CircleCheck className="size-3.5 text-iris-fg" aria-hidden />}
        {state.status === "mismatch" && (
          <ShieldAlert className="size-3.5 text-danger-fg" aria-hidden />
        )}
        <span
          className={cn(
            "font-mono text-[0.6875rem] font-medium uppercase tracking-[0.08em]",
            verifying && "text-muted",
            verified && "text-iris-fg",
            state.status === "mismatch" && "text-danger-fg",
          )}
        >
          {verifying ? "verifying…" : verified ? "audit_hash verified" : "audit_hash mismatch"}
        </span>
      </div>
      <p className="mt-1.5 break-all font-mono text-[0.625rem] leading-relaxed text-secondary tnum">
        {report.audit_hash}
      </p>
      {state.status === "mismatch" && state.result && (
        <p className="mt-1 break-all font-mono text-[0.625rem] leading-relaxed text-danger-fg tnum">
          recomputed {state.result.computed}
        </p>
      )}
      <p className="mt-1.5 text-[0.625rem] leading-snug text-faint">
        {verified
          ? "SHA-256 recomputed in-browser from canonical content."
          : verifying
            ? "recomputing SHA-256 from the report content…"
            : "the stored hash does not match the content — treat as tampered."}
      </p>
    </div>
  );
}

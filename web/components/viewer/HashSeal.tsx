import { CircleCheck, Loader, ShieldAlert } from "lucide-react";

import { cn } from "../../lib/cn";
import type { VerifyState } from "../../lib/useVerify";

const LABEL: Record<VerifyState["status"], string> = {
  verifying: "verifying…",
  verified: "audit_hash verified",
  mismatch: "audit_hash mismatch",
};

function Icon({ status }: { status: VerifyState["status"] }) {
  if (status === "verifying") return <Loader className="size-3.5 animate-spin text-muted" aria-hidden />;
  if (status === "verified") return <CircleCheck className="icon-pop size-3.5 text-iris-fg" aria-hidden />;
  return <ShieldAlert className="icon-pop size-3.5 text-danger-fg" aria-hidden />;
}

/** Full seal for the desktop rail. */
export function HashSeal({ auditHash, state }: { auditHash: string; state: VerifyState }) {
  const { status, result } = state;
  return (
    <div
      className={cn(
        "rounded-md border px-3 py-2.5 transition-colors",
        status === "verifying" && "border-line bg-elevated",
        status === "verified" && "border-iris/40 bg-iris-dim",
        status === "mismatch" && "border-danger/50 bg-danger-dim",
      )}
      role="status"
      aria-live="polite"
    >
      <div className="flex items-center gap-2">
        <Icon status={status} />
        <span
          className={cn(
            "font-mono text-[0.6875rem] font-medium uppercase tracking-[0.08em]",
            status === "verifying" && "text-muted",
            status === "verified" && "text-iris-fg",
            status === "mismatch" && "text-danger-fg",
          )}
        >
          {LABEL[status]}
        </span>
      </div>
      <p className="mt-1.5 break-all font-mono text-[0.625rem] leading-relaxed text-secondary tnum">
        {auditHash}
      </p>
      {status === "mismatch" && result && (
        <p className="mt-1 break-all font-mono text-[0.625rem] leading-relaxed text-danger-fg tnum">
          recomputed {result.computed}
        </p>
      )}
      <p className="mt-1.5 text-[0.625rem] leading-snug text-faint">
        {status === "verified"
          ? "SHA-256 recomputed in-browser from canonical content."
          : status === "verifying"
            ? "recomputing SHA-256 from the report content…"
            : "the stored hash does not match the content — treat as tampered."}
      </p>
    </div>
  );
}

/** Compact seal chip for the mobile bar. */
export function HashSealChip({ state }: { state: VerifyState }) {
  const { status } = state;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-[0.625rem] uppercase tracking-[0.06em]",
        status === "verifying" && "border-line bg-elevated text-muted",
        status === "verified" && "border-iris/40 bg-iris-dim text-iris-fg",
        status === "mismatch" && "border-danger/50 bg-danger-dim text-danger-fg",
      )}
      role="status"
      aria-live="polite"
    >
      <Icon status={status} />
      {status === "verifying" ? "verifying" : status === "verified" ? "verified" : "mismatch"}
    </span>
  );
}

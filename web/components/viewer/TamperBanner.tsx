import { ShieldAlert } from "lucide-react";

import type { VerifyResult } from "../../lib/verify";

/** Prominent, report-level warning shown when the in-browser hash re-verification fails. */
export function TamperBanner({ auditHash, result }: { auditHash: string; result: VerifyResult | null }) {
  return (
    <div
      role="alert"
      className="rounded-md border border-danger/50 bg-danger-dim px-5 py-4"
    >
      <div className="flex items-center gap-2">
        <ShieldAlert className="size-4 text-danger-fg" aria-hidden />
        <h3 className="font-mono text-[0.8125rem] font-semibold uppercase tracking-[0.06em] text-danger-fg">
          audit_hash mismatch — possible tampering
        </h3>
      </div>
      <p className="mt-2 text-[0.8125rem] leading-relaxed text-secondary">
        The SHA-256 recomputed in your browser from this report&apos;s canonical content does not
        match its stored <code className="font-mono text-danger-fg">audit_hash</code>. The numbers
        below may have been altered after the audit was signed — do not trust them.
      </p>
      <dl className="mt-3 grid grid-cols-[5rem_1fr] gap-x-3 gap-y-1 font-mono text-[0.625rem] tnum">
        <dt className="text-faint">stored</dt>
        <dd className="break-all text-secondary">{auditHash}</dd>
        <dt className="text-faint">recomputed</dt>
        <dd className="break-all text-danger-fg">{result?.computed ?? "—"}</dd>
      </dl>
    </div>
  );
}

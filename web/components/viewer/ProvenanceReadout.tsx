"use client";

import { Check, Copy } from "lucide-react";
import { useState } from "react";

import type { AuditReport } from "../../lib/audit-report";
import { cn } from "../../lib/cn";
import { shortHash } from "../../lib/format";
import { Eyebrow, Panel } from "../ui";

function Copyable({ value, display }: { value: string; display: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      onClick={() => {
        navigator.clipboard?.writeText(value).then(() => {
          setCopied(true);
          setTimeout(() => setCopied(false), 1200);
        });
      }}
      className="group inline-flex items-center gap-1.5 font-mono text-[0.6875rem] text-secondary transition-colors hover:text-fg tnum"
      title={value}
    >
      <span>{display}</span>
      {copied ? (
        <Check className="size-3 text-iris-fg" aria-hidden />
      ) : (
        <Copy className="size-3 text-faint opacity-0 transition-opacity group-hover:opacity-100" aria-hidden />
      )}
    </button>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[8rem_1fr] items-baseline gap-3 border-b border-hairline py-1.5 last:border-b-0">
      <span className="font-mono text-[0.6875rem] text-muted">{label}</span>
      <div className="min-w-0">{children}</div>
    </div>
  );
}

export function ProvenanceReadout({ report }: { report: AuditReport }) {
  const p = report.provenance;
  const inputHashes = Object.entries(p.input_hashes ?? {});
  const params = Object.entries(p.params ?? {});
  const tools = Array.from(
    new Set([...Object.keys(p.pinned_versions ?? {}), ...Object.keys(p.runtime_versions ?? {})]),
  ).sort();
  const mismatches = new Set(p.version_mismatches ?? []);

  return (
    <Panel eyebrow="provenance" aside={<span className="font-mono text-[0.6875rem] text-muted tnum">seed {p.seed}</span>}>
      <div className="flex flex-col">
        {inputHashes.map(([key, hash]) => (
          <Row key={key} label={key.replace(/^dataset:/, "")}>
            <Copyable value={hash} display={shortHash(hash)} />
          </Row>
        ))}
        {params.map(([key, value]) => (
          <Row key={key} label={key}>
            <span className="font-mono text-[0.6875rem] text-secondary tnum">{String(value)}</span>
          </Row>
        ))}
      </div>

      {tools.length > 0 && (
        <div className="mt-4">
          <Eyebrow>tool versions</Eyebrow>
          <div className="mt-2 grid grid-cols-[1fr_1fr_1fr] gap-x-3 gap-y-1 font-mono text-[0.6875rem] tnum">
            <span className="text-faint">tool</span>
            <span className="text-faint">pinned</span>
            <span className="text-faint">runtime</span>
            {tools.map((tool) => {
              const drift = mismatches.has(tool);
              return (
                <div key={tool} className="contents">
                  <span className="text-secondary">{tool}</span>
                  <span className="text-secondary">{p.pinned_versions?.[tool] ?? "—"}</span>
                  <span className={drift ? "text-danger-fg" : "text-secondary"}>
                    {p.runtime_versions?.[tool] ?? "—"}
                    {drift && " ⚠"}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </Panel>
  );
}

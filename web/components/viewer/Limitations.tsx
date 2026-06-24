import type { AuditReport } from "../../lib/audit-report";
import { Eyebrow } from "../ui";

export function Limitations({ report }: { report: AuditReport }) {
  const limitations = report.limitations ?? [];
  if (limitations.length === 0) return null;

  return (
    <section className="border-t border-hairline pt-5">
      <header className="mb-3 flex items-baseline justify-between gap-4">
        <Eyebrow>disclosed limitations</Eyebrow>
        <span className="text-[0.625rem] text-faint">part of the hashed content</span>
      </header>
      <div className="flex flex-col gap-3">
        {limitations.map((lim) => (
          <div key={lim.id} className="border-l-2 border-line pl-3">
            <h4 className="text-[0.8125rem] font-medium text-fg">{lim.title}</h4>
            <p className="mt-1 text-[0.8125rem] leading-relaxed text-secondary">{lim.detail}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

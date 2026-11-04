import Link from "next/link";

import { FOCUS_RING } from "./ui";

const LINK = `rounded-sm text-secondary transition-colors hover:text-fg ${FOCUS_RING}`;

export function Footer() {
  return (
    <footer className="mt-16 flex flex-col gap-4 border-t border-hairline pt-6 pb-2 text-[0.8125rem] text-muted sm:flex-row sm:items-center">
      <p>
        <span className="font-medium text-fg">Veritas</span> · benchmark integrity for model evaluation · MIT
      </p>
      <nav className="flex flex-wrap gap-x-5 gap-y-2 sm:ml-auto">
        <Link href="/run" className={LINK}>Run audit</Link>
        <Link href="/report" className={LINK}>Reports</Link>
        <Link href="/docs" className={LINK}>Docs</Link>
        <Link href="/report/legacy" className={LINK}>Legacy viewer</Link>
        <a href="https://github.com/shreyjain11/veritas" target="_blank" rel="noreferrer" className={LINK}>
          GitHub
        </a>
      </nav>
    </footer>
  );
}

import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-5 px-6 text-center">
      <span className="font-mono text-sm font-semibold tracking-tight text-iris-fg">veritas</span>
      <h1 className="font-mono text-6xl leading-none text-fg tnum">404</h1>
      <p className="max-w-sm text-[0.9375rem] leading-relaxed text-secondary">
        This page doesn&apos;t exist. The report viewer renders AuditReport JSON — there&apos;s
        nothing to audit here.
      </p>
      <Link
        href="/"
        className="rounded-md border border-iris/40 bg-iris-dim px-3.5 py-2 font-mono text-[0.8125rem] text-iris-fg transition-colors hover:border-iris/70 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-iris"
      >
        Open the report viewer
      </Link>
    </main>
  );
}

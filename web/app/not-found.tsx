import Link from "next/link";

import { Nav } from "../components/landing/Nav";
import { buttonClass } from "../components/ui";

export default function NotFound() {
  return (
    <>
      <Nav />
      <main className="mx-auto flex min-h-[70vh] max-w-xl flex-col items-start justify-center px-5 sm:px-8">
        <p className="tnum font-mono text-sm text-muted">404</p>
        <h1 className="mt-2 font-display text-[2.5rem] leading-tight font-medium tracking-[-0.015em] text-fg">
          This page doesn&apos;t exist.
        </h1>
        <p className="mt-3 text-[1.0625rem] leading-relaxed text-secondary">
          The link may be out of date. Everything Veritas does starts from one of these.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link href="/run" className={buttonClass("primary")}>Run an audit</Link>
          <Link href="/report" className={buttonClass("secondary")}>Open a report</Link>
          <Link href="/" className={buttonClass("ghost")}>Home</Link>
        </div>
      </main>
    </>
  );
}

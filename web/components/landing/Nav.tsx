import Link from "next/link";

const LINK =
  "group relative rounded-sm text-secondary transition-colors hover:text-fg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-iris";

function Underline() {
  return (
    <span
      aria-hidden
      className="pointer-events-none absolute -bottom-1 left-0 h-px w-full origin-left scale-x-0 bg-iris/70 transition-transform duration-300 ease-out group-hover:scale-x-100"
    />
  );
}

export function Nav() {
  return (
    <header className="sticky top-0 z-20 bg-base/80 backdrop-blur">
      <div className="mx-auto flex max-w-[1100px] items-center gap-3 px-5 py-3.5 sm:px-8">
        <Link
          href="/"
          className="group flex items-center gap-2 rounded-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-iris"
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 32 32"
            fill="none"
            aria-hidden
            className="transition-transform duration-300 ease-out group-hover:rotate-6"
          >
            <rect width="32" height="32" rx="7" fill="#14181E" />
            <rect x="6.5" y="10.5" width="19" height="3.6" rx="1.8" fill="#E0A53B" />
            <rect x="6.5" y="17.9" width="9.5" height="3.6" rx="1.8" fill="#6E78F0" />
          </svg>
          <span className="font-mono text-sm font-semibold tracking-tight text-fg">veritas</span>
        </Link>
        <nav className="ml-auto flex items-center gap-5 text-[0.8125rem]">
          <Link href="/report" className={LINK}>
            Report viewer
            <Underline />
          </Link>
          <Link href="/docs" className={LINK}>
            Docs
            <Underline />
          </Link>
          <a href="https://github.com/shreyjain11/veritas" target="_blank" rel="noreferrer" className={LINK}>
            GitHub
            <Underline />
          </a>
        </nav>
      </div>
    </header>
  );
}

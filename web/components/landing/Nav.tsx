"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "../../lib/cn";
import { ThemeToggle } from "../ThemeToggle";
import { buttonClass, FOCUS_RING } from "../ui";

const LINKS = [
  { href: "/report", label: "Reports" },
  { href: "/docs", label: "Docs" },
];

export function Logo() {
  return (
    <svg width="22" height="22" viewBox="0 0 32 32" fill="none" aria-hidden>
      <rect width="32" height="32" rx="7" fill="#14181E" />
      <rect x="6.5" y="10.5" width="19" height="3.6" rx="1.8" fill="#E0A53B" />
      <rect x="6.5" y="17.9" width="9.5" height="3.6" rx="1.8" fill="#6E78F0" />
    </svg>
  );
}

export function Nav() {
  const pathname = usePathname();
  return (
    <header className="sticky top-0 z-20 border-b border-hairline bg-base/85 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-[1120px] items-center gap-4 px-5 sm:px-8">
        <Link href="/" aria-label="Veritas home" className={cn("flex shrink-0 items-center gap-2 rounded-sm", FOCUS_RING)}>
          <Logo />
          <span className="hidden text-[0.9375rem] font-semibold tracking-tight text-fg min-[400px]:inline">Veritas</span>
        </Link>
        <nav className="ml-auto flex items-center gap-1 whitespace-nowrap text-sm sm:gap-2">
          {LINKS.map((link) => {
            const active = pathname === link.href || pathname.startsWith(`${link.href}/`);
            return (
              <Link
                key={link.href}
                href={link.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "rounded-md px-2.5 py-1.5 transition-colors",
                  FOCUS_RING,
                  active ? "text-fg" : "text-secondary hover:text-fg",
                )}
              >
                {link.label}
              </Link>
            );
          })}
          <a
            href="https://github.com/shreyjain11/veritas"
            target="_blank"
            rel="noreferrer"
            className={cn("hidden rounded-md px-2.5 py-1.5 text-secondary transition-colors hover:text-fg sm:inline", FOCUS_RING)}
          >
            GitHub
          </a>
          <ThemeToggle />
          <Link href="/run" className={buttonClass("primary", "ml-1 px-3 py-1.5")}>
            Run audit
          </Link>
        </nav>
      </div>
    </header>
  );
}

"use client";

import { useEffect, useState } from "react";

import { cn } from "../../lib/cn";

export interface TocItem {
  id: string;
  label: string;
}

/** Sticky table of contents with scroll-spy (highlights the section in view). */
export function Toc({ items }: { items: TocItem[] }) {
  const [active, setActive] = useState(items[0]?.id ?? "");
  useEffect(() => {
    const io = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]) setActive(visible[0].target.id);
      },
      { rootMargin: "-18% 0px -72% 0px", threshold: 0 },
    );
    for (const it of items) {
      const el = document.getElementById(it.id);
      if (el) io.observe(el);
    }
    return () => io.disconnect();
  }, [items]);

  return (
    <nav aria-label="On this page" className="flex flex-col gap-0.5 border-l border-line text-sm">
      {items.map((it) => (
        <a
          key={it.id}
          href={`#${it.id}`}
          className={cn(
            "-ml-px border-l-2 py-1 pl-4 transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-iris",
            active === it.id ? "border-fg font-medium text-fg" : "border-transparent text-muted hover:text-fg",
          )}
        >
          {it.label}
        </a>
      ))}
    </nav>
  );
}

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
    <nav aria-label="On this page" className="flex flex-col gap-0.5 text-[0.8125rem]">
      <span className="mb-1 px-3 text-[0.6875rem] font-medium uppercase tracking-[0.08em] text-faint">
        On this page
      </span>
      {items.map((it) => (
        <a
          key={it.id}
          href={`#${it.id}`}
          className={cn(
            "rounded-sm px-3 py-1 transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-iris",
            active === it.id ? "font-medium text-iris-fg" : "text-muted hover:text-fg",
          )}
        >
          {it.label}
        </a>
      ))}
    </nav>
  );
}

"use client";

import { createElement, type CSSProperties, type ElementType, type ReactNode } from "react";
import { useEffect, useRef, useState } from "react";

/** Fades + slides children in the first time they scroll into view. */
export function Reveal({
  children,
  delay = 0,
  className,
  as = "div",
}: {
  children: ReactNode;
  delay?: number;
  className?: string;
  as?: ElementType;
}) {
  const ref = useRef<HTMLElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.15, rootMargin: "0px 0px -40px 0px" },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return createElement(
    as,
    {
      ref,
      "data-visible": visible,
      className: className ? `reveal ${className}` : "reveal",
      style: { "--delay": `${delay}ms` } as CSSProperties,
    },
    children,
  );
}

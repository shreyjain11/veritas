"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

import { cn } from "../lib/cn";

/** Fade + rise into view on scroll. No-JS safe (renders visible until armed on the client);
 * reduced-motion shows the final state. Use for below-the-fold sections only. */
export function Reveal({
  children,
  className,
  delay = 0,
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [armed, setArmed] = useState(false);
  const [shown, setShown] = useState(false);

  useEffect(() => {
    setArmed(true);
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          setShown(true);
          io.disconnect();
        }
      },
      { threshold: 0.12, rootMargin: "0px 0px -8% 0px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  const hidden = armed && !shown;
  return (
    <div
      ref={ref}
      style={{ transitionDelay: `${delay}ms` }}
      className={cn(
        "transition-all duration-[650ms] ease-out motion-reduce:!translate-y-0 motion-reduce:!opacity-100",
        hidden ? "translate-y-3 opacity-0" : "translate-y-0 opacity-100",
        className,
      )}
    >
      {children}
    </div>
  );
}

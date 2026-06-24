"use client";

import { useEffect, useState } from "react";

const easeOut = (t: number) => 1 - Math.pow(1 - t, 3);

/** Tween a number from 0 → target on mount. duration<=0 or reduced-motion → instant (final). */
export function useCountUp(target: number, duration = 900): number {
  const [value, setValue] = useState(target); // SSR / no-JS shows the final value
  useEffect(() => {
    const reduced =
      typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (duration <= 0 || reduced) {
      setValue(target);
      return;
    }
    let raf = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      setValue(target * easeOut(t));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    setValue(0);
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, duration]);
  return value;
}

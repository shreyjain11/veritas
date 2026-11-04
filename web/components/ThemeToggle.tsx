"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

import { cn } from "../lib/cn";
import { FOCUS_RING } from "./ui";

type Theme = "system" | "light" | "dark";
const KEY = "veritas-theme";
const NEXT: Record<Theme, Theme> = { system: "light", light: "dark", dark: "system" };
const LABEL: Record<Theme, string> = { system: "System theme", light: "Light theme", dark: "Dark theme" };

function apply(theme: Theme) {
  const root = document.documentElement;
  root.classList.add("theme-switching");
  if (theme === "system") delete root.dataset.theme;
  else root.dataset.theme = theme;
  try {
    if (theme === "system") window.localStorage.removeItem(KEY);
    else window.localStorage.setItem(KEY, theme);
  } catch {
    /* storage unavailable: the choice lasts for this page view only */
  }
  // Let the new colors paint before transitions are re-enabled.
  window.requestAnimationFrame(() => window.requestAnimationFrame(() => root.classList.remove("theme-switching")));
}

/** Cycles system → light → dark. The initial theme is set before paint by the layout script. */
export function ThemeToggle({ className }: { className?: string }) {
  const [theme, setTheme] = useState<Theme>("system");
  useEffect(() => {
    const current = document.documentElement.dataset.theme;
    setTheme(current === "light" || current === "dark" ? current : "system");
  }, []);
  const Icon = theme === "light" ? Sun : theme === "dark" ? Moon : Monitor;
  return (
    <button
      type="button"
      onClick={() => {
        const next = NEXT[theme];
        apply(next);
        setTheme(next);
      }}
      aria-label={`${LABEL[theme]} (click to switch)`}
      title={LABEL[theme]}
      className={cn(
        "inline-flex size-8 items-center justify-center rounded-md text-secondary transition-colors hover:bg-elevated hover:text-fg",
        FOCUS_RING,
        className,
      )}
    >
      <Icon aria-hidden className="size-4" strokeWidth={1.75} />
    </button>
  );
}

"use client";

import { useTheme } from "next-themes";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

const ORDER = ["light", "dark", "system"] as const;

export function ThemeToggle() {
  const t = useTranslations("theme");
  const tn = useTranslations("nav");
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const current = (mounted ? theme : "system") as (typeof ORDER)[number];
  const next = ORDER[(ORDER.indexOf(current) + 1) % ORDER.length];
  return (
    <button
      type="button"
      onClick={() => setTheme(next)}
      aria-label={`${tn("theme")}: ${t(current)}`}
      title={`${tn("theme")}: ${t(current)}`}
      data-testid="theme-toggle"
      data-theme={mounted ? resolvedTheme : "system"}
      className="rounded border hairline px-2 py-1 font-mono text-xs text-fg-muted hover:bg-surface hover:text-fg"
    >
      {mounted ? t(current) : "…"}
    </button>
  );
}

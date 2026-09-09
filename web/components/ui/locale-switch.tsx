"use client";

import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";

export function LocaleSwitch() {
  const locale = useLocale();
  const t = useTranslations("nav");
  const router = useRouter();
  const next = locale === "hi" ? "en" : "hi";
  return (
    <button
      type="button"
      aria-label={`${t("language")}: ${locale === "hi" ? "हिन्दी" : "English"}`}
      data-testid="locale-switch"
      onClick={() => {
        document.cookie = `virasat_locale=${next}; path=/; max-age=31536000; samesite=lax`;
        router.refresh();
      }}
      className="rounded border hairline px-2 py-1 font-mono text-xs text-fg-muted hover:bg-surface hover:text-fg"
    >
      {locale === "hi" ? "EN" : "हि"}
    </button>
  );
}

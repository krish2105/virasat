import { useTranslations } from "next-intl";

export function Footer() {
  const t = useTranslations("app");
  return (
    <footer className="border-t hairline">
      <div className="mx-auto max-w-7xl px-4 py-6 text-xs text-fg-muted">
        <p className="mb-1">{t("recommendation")}</p>
        <p className="font-mono text-[11px]">{t("footer")}</p>
      </div>
    </footer>
  );
}

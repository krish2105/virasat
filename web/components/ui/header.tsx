"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Notification, Officer } from "@/lib/types";
import { ThemeToggle } from "./theme-toggle";
import { LocaleSwitch } from "./locale-switch";

const LINKS = [
  ["/queue", "queue"], ["/visits", "visits"], ["/audit", "audit"], ["/health", "health"], ["/dossier", "dossier"],
] as const;

export function Header() {
  const t = useTranslations("nav");
  const ta = useTranslations("app");
  const path = usePathname();
  const router = useRouter();
  const [officer, setOfficer] = useState<Officer | null>(null);
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    api<Officer>("/auth/me").then(setOfficer).catch(() => setOfficer(null));
  }, [path]);
  useEffect(() => {
    if (!officer) return;
    api<Notification[]>("/notifications?unread=true").then((n) => setUnread(n.length)).catch(() => {});
  }, [officer, path]);

  async function logout() {
    await api("/auth/logout", { method: "POST" });
    setOfficer(null);
    router.push("/");
    router.refresh();
  }

  return (
    <header className="sticky top-0 z-40 border-b hairline bg-ground/90 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-4 px-4">
        <Link href="/" className="font-display text-xl tracking-tight text-fg">
          {ta("name")}<span className="ml-2 hidden font-mono text-[11px] uppercase tracking-widest text-fg-muted sm:inline">1605</span>
        </Link>
        <nav aria-label="Primary" className="ml-2 hidden items-center gap-1 md:flex">
          {officer && LINKS.map(([href, key]) => (
            <Link key={href} href={href} aria-current={path.startsWith(href) ? "page" : undefined}
              className="rounded px-2 py-1 text-sm text-fg-muted hover:text-fg aria-[current=page]:bg-surface aria-[current=page]:text-fg">
              {t(key)}
            </Link>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-2">
          {officer && (
            <Link href="/notifications" aria-label={`${t("notifications")}${unread ? ` (${unread})` : ""}`}
              className="relative rounded px-2 py-1 text-sm text-fg-muted hover:text-fg">
              {t("notifications")}
              {unread > 0 && <span className="absolute -right-1 -top-1 rounded-full bg-sandstone px-1.5 font-mono text-[10px] text-plaster">{unread}</span>}
            </Link>
          )}
          <LocaleSwitch />
          <ThemeToggle />
          {officer ? (
            <button onClick={logout} className="rounded border hairline px-2 py-1 text-sm hover:bg-surface">
              <span className="font-mono text-xs text-fg-muted">{officer.display_name}</span> · {t("logout")}
            </button>
          ) : (
            <Link href="/login" className="rounded border hairline px-2 py-1 text-sm hover:bg-surface">{t("login")}</Link>
          )}
        </div>
      </div>
    </header>
  );
}

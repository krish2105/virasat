"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { ChangeSummary, QueuePage } from "@/lib/types";
import { Label, SeverityBar } from "@/components/ui/primitives";

const CHOWKRIS = ["Sarhad", "Purani Basti", "Topkhana Desh", "Modikhana", "Vishveshwarji", "Ghat Darwaza", "Ramchandraji", "Topkhana Hazuri", "Gangapole"];

export function QueueList() {
  const t = useTranslations("queue");
  const tc = useTranslations("change");
  const router = useRouter();
  const params = useSearchParams();
  const [page, setPage] = useState<QueuePage | null>(null);
  const [cursor, setCursor] = useState(0);
  const status = params.get("status") ?? "pending,needs_human_rewrite";
  const zone = params.get("zone") ?? "";
  const severity = params.get("severity") ?? "";
  const chowkri = params.get("chowkri") ?? "";

  const load = useCallback(() => {
    const q = new URLSearchParams({ status, limit: "200" });
    if (zone) q.set("zone", zone);
    if (severity) q.set("severity", severity);
    if (chowkri) q.set("chowkri", chowkri);
    api<QueuePage>(`/queue?${q}`).then(setPage).catch(() => setPage({ items: [], total: 0 }));
  }, [status, zone, severity, chowkri]);
  useEffect(load, [load]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (!page?.items.length || (e.target as HTMLElement).tagName === "INPUT") return;
      if (e.key === "j" || e.key === "ArrowDown") { e.preventDefault(); setCursor((c) => Math.min(c + 1, page.items.length - 1)); }
      if (e.key === "k" || e.key === "ArrowUp") { e.preventDefault(); setCursor((c) => Math.max(c - 1, 0)); }
      if (e.key === "Enter") router.push(`/changes/${page.items[cursor].id}`);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [page, cursor, router]);

  function setFilter(key: string, value: string) {
    const q = new URLSearchParams(params.toString());
    if (value) q.set(key, value); else q.delete(key);
    router.replace(`/queue?${q}`);
  }

  const select = "rounded border hairline bg-surface px-2 py-1 font-mono text-xs";
  return (
    <section aria-labelledby="queue-title">
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <h1 id="queue-title" className="font-display text-3xl">{t("title")}</h1>
        <span className="data text-fg-muted">{page ? t("count", { count: page.total }) : "…"}</span>
        <div className="ml-auto flex flex-wrap gap-2">
          <label className="flex flex-col"><Label>{t("filters.zone")}</Label>
            <select className={select} value={zone} onChange={(e) => setFilter("zone", e.target.value)}>
              <option value="">{t("filters.all")}</option><option value="core">core</option><option value="buffer">buffer</option>
            </select></label>
          <label className="flex flex-col"><Label>{t("filters.severity")}</Label>
            <select className={select} value={severity} onChange={(e) => setFilter("severity", e.target.value)}>
              <option value="">{t("filters.all")}</option>{["high", "medium", "low"].map((s) => <option key={s} value={s}>{tc(`severity.${s}`)}</option>)}
            </select></label>
          <label className="flex flex-col"><Label>{t("filters.chowkri")}</Label>
            <select className={select} value={chowkri} onChange={(e) => setFilter("chowkri", e.target.value)}>
              <option value="">{t("filters.all")}</option>{CHOWKRIS.map((c) => <option key={c} value={c}>{c}</option>)}
            </select></label>
          <label className="flex flex-col"><Label>{t("filters.status")}</Label>
            <select className={select} value={status} onChange={(e) => setFilter("status", e.target.value)}>
              <option value="pending,needs_human_rewrite">pending</option>
              {["approved", "rejected", "escalated", "dropped", "all"].map((s) => <option key={s} value={s}>{s}</option>)}
            </select></label>
        </div>
      </div>
      <p className="mb-2 font-mono text-[11px] text-fg-muted">{t("keys")}</p>
      {page && page.items.length === 0 && <p className="rounded border hairline p-6 text-sm text-fg-muted">{t("empty")}</p>}
      <ol className="divide-y hairline rounded border hairline bg-surface" role="list">
        {page?.items.map((c, i) => <Row key={c.id} c={c} active={i === cursor} onFocus={() => setCursor(i)} />)}
      </ol>
    </section>
  );
}

function Row({ c, active, onFocus }: { c: ChangeSummary; active: boolean; onFocus: () => void }) {
  const tc = useTranslations("change");
  return (
    <li className={`relative ${active ? "bg-ground" : ""}`}>
      <SeverityBar severity={c.severity} />
      <Link href={`/changes/${c.id}`} onFocus={onFocus} data-testid="queue-row"
        className="grid grid-cols-[1fr_auto] items-center gap-x-4 gap-y-1 py-2 pl-4 pr-3 text-sm sm:grid-cols-[7rem_1fr_9rem_6rem_6rem_7rem]">
        <span className="data text-fg-muted">{c.id.slice(0, 8)}</span>
        <span className="truncate">{c.chowkri_id ?? c.zone} <span className="text-fg-muted">· {c.zone}</span></span>
        <span>{tc(`types.${c.change_type}`)}</span>
        <span className="data">{(c.change_prob * 100).toFixed(0)}%</span>
        <span className={`data ${c.severity === "high" ? "text-alarm" : ""}`}>{c.severity ? tc(`severity.${c.severity}`) : "—"}</span>
        <span className="data text-fg-muted">{c.status === "needs_human_rewrite" ? "⚠ " : ""}{tc(`status.${c.status}`)}{c.priority === "urgent" ? " · urgent" : ""}</span>
      </Link>
    </li>
  );
}

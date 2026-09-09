"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Visit } from "@/lib/types";
import { Button, Card, Label } from "@/components/ui/primitives";

export default function VisitsPage() {
  const t = useTranslations("visits");
  const tc = useTranslations("change");
  const [visits, setVisits] = useState<Visit[]>([]);
  const load = () => api<Visit[]>("/visits").then(setVisits).catch(() => setVisits([]));
  useEffect(() => { load(); }, []);
  async function update(id: string, body: Record<string, unknown>) { await api(`/visits/${id}`, { method: "PATCH", body: JSON.stringify(body) }); load(); }
  const byDay = visits.reduce<Record<string, Visit[]>>((acc, v) => { (acc[v.scheduled_for] ??= []).push(v); return acc; }, {});
  return (
    <div className="mx-auto max-w-5xl px-4 py-8 print:max-w-none">
      <div className="mb-4 flex items-center gap-3">
        <h1 className="font-display text-3xl">{t("title")}</h1>
        <Button className="ml-auto print:hidden" onClick={() => window.print()}>{t("print")}</Button>
      </div>
      {visits.length === 0 && <p className="text-sm text-fg-muted">{t("empty")}</p>}
      {Object.entries(byDay).sort().map(([day, list]) => (
        <section key={day} className="mb-6 break-inside-avoid" aria-labelledby={`d-${day}`}>
          <h2 id={`d-${day}`} className="mb-2 data text-fg-muted">{day}</h2>
          <ul className="space-y-2">
            {list.map((v) => (
              <li key={v.id}>
                <Card className="grid gap-2 p-3 sm:grid-cols-[1fr_auto]">
                  <div>
                    <Link href={`/changes/${v.change_id}`} className="text-sm underline">{tc(`types.${v.change.change_type}`)} · {v.change.chowkri_id ?? v.change.zone}</Link>
                    <p className="data text-[11px] text-fg-muted">{v.change_id.slice(0, 8)} · {t("assignee")}: {v.assignee_name ?? "—"} · {v.status}</p>
                    <label className="mt-2 block"><Label>{t("notes")}</Label>
                      <textarea defaultValue={v.field_notes ?? ""} rows={2} onBlur={(e) => e.target.value !== (v.field_notes ?? "") && update(v.id, { field_notes: e.target.value })}
                        className="mt-1 w-full rounded border hairline bg-ground p-2 text-sm print:border-0" /></label>
                  </div>
                  <div className="flex gap-2 print:hidden">
                    {v.status === "scheduled" && <Button onClick={() => update(v.id, { status: "done" })}>{t("done")}</Button>}
                    {v.status === "scheduled" && <Button variant="ghost" onClick={() => update(v.id, { status: "cancelled" })}>{t("cancel")}</Button>}
                  </div>
                </Card>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}

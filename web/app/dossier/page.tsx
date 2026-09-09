"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card, Label } from "@/components/ui/primitives";

interface Dossier { generated: string; count: number; aggregates: Record<string, Record<string, number>> }

export default function DossierPage() {
  const t = useTranslations("nav");
  const [d, setD] = useState<Dossier | null>(null);
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const q = new URLSearchParams({ ...(start && { start }), ...(end && { end }) }).toString();
  useEffect(() => { api<Dossier>(`/dossier?${q}`).then(setD).catch(() => setD(null)); }, [q]);
  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <h1 className="font-display text-3xl">{t("dossier")}</h1>
      <div className="my-4 flex flex-wrap items-end gap-3">
        <label className="flex flex-col"><Label>start</Label><input type="date" value={start} onChange={(e) => setStart(e.target.value)} className="rounded border hairline bg-surface px-2 py-1 font-mono text-xs" /></label>
        <label className="flex flex-col"><Label>end</Label><input type="date" value={end} onChange={(e) => setEnd(e.target.value)} className="rounded border hairline bg-surface px-2 py-1 font-mono text-xs" /></label>
        <a className="rounded border hairline px-3 py-1.5 text-sm hover:bg-surface" href={`/api/dossier.csv?${q}`} data-testid="dossier-csv">CSV</a>
        <a className="rounded border hairline px-3 py-1.5 text-sm hover:bg-surface" href={`/api/dossier.pdf?${q}`}>PDF</a>
        <a className="rounded border hairline px-3 py-1.5 text-sm hover:bg-surface" href={`/api/dossier?${q}`}>JSON</a>
      </div>
      {d && (
        <div className="grid gap-3 sm:grid-cols-2">
          {Object.entries(d.aggregates).map(([k, v]) => (
            <Card key={k} className="p-3"><Label>{k.replace("by_", "by ")}</Label>
              <ul className="mt-2 space-y-1 text-sm">{Object.entries(v).map(([kk, n]) => <li key={kk} className="flex justify-between"><span>{kk}</span><span className="data">{n}</span></li>)}</ul>
            </Card>
          ))}
          <p className="data text-[11px] text-fg-muted sm:col-span-2">{d.count} changes · generated {d.generated}</p>
        </div>
      )}
    </div>
  );
}

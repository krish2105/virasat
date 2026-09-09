"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AuditRow } from "@/lib/types";

export default function AuditPage() {
  const t = useTranslations("audit");
  const [rows, setRows] = useState<AuditRow[]>([]);
  useEffect(() => { api<AuditRow[]>("/audit?limit=300").then(setRows).catch(() => setRows([])); }, []);
  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <h1 className="font-display text-3xl">{t("title")}</h1>
      <p className="mb-4 data text-[11px] text-fg-muted">{t("append")}</p>
      <div className="overflow-x-auto rounded border hairline">
        <table className="w-full text-left text-sm">
          <thead className="bg-surface"><tr>{["when", "who", "what", "change", "models", "tokens"].map((k) => <th key={k} scope="col" className="px-3 py-2 font-mono text-[11px] uppercase tracking-widest text-fg-muted">{t(k)}</th>)}</tr></thead>
          <tbody className="divide-y hairline">
            {rows.map((r) => (
              <tr key={r.id}>
                <td className="whitespace-nowrap px-3 py-1.5 data">{r.ts.slice(0, 19).replace("T", " ")}</td>
                <td className="px-3 py-1.5 data">{r.actor}</td>
                <td className="px-3 py-1.5">{r.action}{"reason" in r.payload && r.payload.reason ? <span className="text-fg-muted"> — {String(r.payload.reason)}</span> : null}</td>
                <td className="px-3 py-1.5 data">{r.change_id ? <Link className="underline" href={`/changes/${r.change_id}`}>{r.change_id.slice(0, 8)}</Link> : "—"}</td>
                <td className="px-3 py-1.5 data text-[11px] text-fg-muted">{Object.values(r.model_ids).join(" / ") || "—"}{r.git_sha ? ` @${r.git_sha.slice(0, 7)}` : ""}</td>
                <td className="px-3 py-1.5 data">{r.total_tokens || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

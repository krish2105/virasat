"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { HealthMetrics } from "@/lib/types";
import { Card, Label } from "@/components/ui/primitives";

function Stat({ label, value, blocked }: { label: string; value: React.ReactNode; blocked?: boolean }) {
  return <Card className="p-3"><Label>{label}</Label><div className={`mt-1 data text-lg ${blocked ? "text-fg-muted" : ""}`}>{value}</div></Card>;
}

export default function HealthPage() {
  const t = useTranslations("health");
  const [m, setM] = useState<HealthMetrics | null>(null);
  useEffect(() => { api<HealthMetrics>("/metrics/health").then(setM).catch(() => setM(null)); }, []);
  if (!m) return <div className="mx-auto max-w-7xl px-4 py-8 data text-fg-muted">…</div>;
  const p = m.pipeline as Record<string, number | Record<string, number>> | null;
  const cal = m.calibration as Record<string, number | string> | null;
  const f = m.fairness;
  const maxFpr = Math.max(0.01, ...Object.values(f.fpr_by_chowkri));
  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <h1 className="mb-4 font-display text-3xl">{t("title")}</h1>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label={`${t("pipeline")} · tiles`} value={p ? String(p.tiles) : t("blocked")} blocked={!p} />
        <Stat label={`${t("pipeline")} · quarantine`} value={p ? `${((p.quarantine_rate as number) * 100).toFixed(1)}%` : t("blocked")} blocked={!p} />
        <Stat label={`${t("calibration")} · ECE`} value={cal ? Number(cal.ece).toFixed(3) : t("blocked")} blocked={!cal} />
        <Stat label={`${t("calibration")} · T`} value={cal ? `${Number(cal.temperature).toFixed(2)} (${cal.calibration_date})` : t("blocked")} blocked={!cal} />
        <Stat label={`${t("retrieval")} · P@3`} value={m.retrieval.status === "measured" ? String(m.retrieval.precision_at_3) : t("blocked")} blocked={m.retrieval.status !== "measured"} />
        <Stat label={t("agreement")} value={m.agreement_rate == null ? t("blocked") : `${(m.agreement_rate * 100).toFixed(0)}%`} blocked={m.agreement_rate == null} />
        {Object.entries(m.queue).map(([k, v]) => <Stat key={k} label={`${t("queue")} · ${k}`} value={v} />)}
      </div>
      <section className="mt-8" aria-labelledby="fair">
        <h2 id="fair" className="font-display text-2xl">{t("fairness")}</h2>
        <p className="data text-sm text-fg-muted">
          {f.status === "measured" ? (
            <>{t("disparity")} {f.disparity_ratio?.toFixed(2) ?? "—"} · {t("threshold")} {f.max_ratio} · <span className={f.passes ? "" : "text-alarm"}>{f.passes ? "PASS" : "FAIL"}</span></>
          ) : <>{t("blocked")} — {f.reason}</>}
        </p>
        <h3 className="mt-3"><Label>{t("fprByChowkri")}</Label></h3>
        <ul className="mt-2 space-y-1">
          {Object.entries(f.fpr_by_chowkri).length === 0 && <li className="text-sm text-fg-muted">—</li>}
          {Object.entries(f.fpr_by_chowkri).map(([k, v]) => (
            <li key={k} className="grid grid-cols-[9rem_1fr_4rem_3rem] items-center gap-2 text-sm">
              <span>{k}</span>
              <span className="h-2 rounded bg-surface"><span className="block h-2 rounded bg-indigo" style={{ width: `${(v / maxFpr) * 100}%` }} /></span>
              <span className="data">{(v * 100).toFixed(1)}%</span>
              <span className="data text-fg-muted">n={f.n_by_chowkri[k]}</span>
            </li>
          ))}
        </ul>
      </section>
      <section className="mt-8" aria-labelledby="runs">
        <h2 id="runs" className="font-display text-2xl">{t("runs")}</h2>
        <ul className="mt-2 space-y-1 text-sm">
          {m.runs.map((r) => <li key={String(r.id)} className="data">{String(r.started_at).slice(0, 16)} · {String(r.status)} · {String(r.epoch_before)}→{String(r.epoch_after)} · tokens {String(r.total_tokens)} · @{String(r.git_sha).slice(0, 7)}</li>)}
        </ul>
      </section>
    </div>
  );
}

"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, evidenceUrl } from "@/lib/api";
import type { ChangeDetail } from "@/lib/types";
import { Button, Card, Label, SeverityBar } from "@/components/ui/primitives";
import { CompareSlider } from "./compare-slider";

export function ChangeReview({ initial }: { initial: ChangeDetail }) {
  const t = useTranslations("change");
  const router = useRouter();
  const [c, setC] = useState(initial);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const decided = c.status !== "pending" && c.status !== "needs_human_rewrite";

  const decide = useCallback(async (decision: "approve" | "reject" | "escalate") => {
    if (decided || busy) return;
    if (decision === "reject" && !reason.trim()) { dialog.current?.showModal(); return; }
    setBusy(true);
    try {
      const out = await api<ChangeDetail>(`/changes/${c.id}/decision`, { method: "POST", body: JSON.stringify({ decision, reason: decision === "reject" ? reason : null }) });
      setC(out);
      setMsg(t("decided"));
      dialog.current?.close();
      setTimeout(() => router.push("/queue"), 600);
    } catch (e) { setMsg(String(e)); } finally { setBusy(false); }
  }, [c.id, reason, decided, busy, router, t]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || dialog.current?.open) return;
      if (e.key === "a") decide("approve");
      if (e.key === "r") dialog.current?.showModal();
      if (e.key === "e") decide("escalate");
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [decide]);

  const clauseFor = (id: string) => c.clauses.find((k) => k.clause_id === id);
  return (
    <article className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <div className="space-y-4">
        <CompareSlider before={evidenceUrl(c.before_uri)} after={evidenceUrl(c.after_uri)} mask={evidenceUrl(c.mask_uri)} />
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm sm:grid-cols-3">
          <div><dt><Label>{t("zone")}</Label></dt><dd className="data">{c.zone}</dd></div>
          <div><dt><Label>{t("chowkri")}</Label></dt><dd>{c.chowkri_id ?? "—"}</dd></div>
          <div><dt><Label>{t("period")}</Label></dt><dd className="data">{c.epoch_before} → {c.epoch_after}</dd></div>
          <div><dt><Label>{t("confidence")}</Label></dt>
            <dd className="data">{(c.change_prob * 100).toFixed(1)}%<br />
              <span className="text-[11px] text-fg-muted">{c.calibration_date ? t("calibrated", { date: c.calibration_date }) : t("uncalibrated")}</span></dd></div>
          <div><dt><Label>{t("building")}</Label></dt>
            <dd className="data">{c.building_id ? <Link className="underline" href={`/buildings/${c.building_id}`}>{c.building_id}</Link> : "—"}</dd></div>
          <div><dt><Label>type</Label></dt><dd>{t(`types.${c.change_type}`)}</dd></div>
        </dl>
      </div>
      <div className="space-y-4">
        {c.status === "needs_human_rewrite" && <p role="alert" className="rounded border border-alarm/60 bg-alarm/10 p-3 text-sm">{t("needsRewrite")}</p>}
        <section aria-labelledby="findings">
          <h2 id="findings" className="mb-2 font-display text-xl">{t("findings")}</h2>
          {c.findings.length === 0 && <p className="text-sm text-fg-muted">{t("noFindings")}</p>}
          <ul className="space-y-2">
            {c.findings.map((f) => {
              const k = clauseFor(f.clause_id);
              return (
                <li key={f.id} className="relative">
                  <SeverityBar severity={f.severity} />
                  <Card className="p-3 pl-4">
                    <p className="text-sm">{f.claim}</p>
                    <p className="mt-1 data text-fg-muted">{f.clause_id} · {t(`severity.${f.severity}`)}{f.is_final ? "" : " · draft"}</p>
                    {k && (
                      <details className="mt-2" open={expanded === f.id} onToggle={(e) => setExpanded((e.target as HTMLDetailsElement).open ? f.id : null)}>
                        <summary className="cursor-pointer text-xs text-fg-muted">{t("clause")} · p.{k.source_page}</summary>
                        <p className="mt-1 data text-[11px] text-fg-muted">{k.path}</p>
                        <blockquote className="mt-2 border-l-2 hairline pl-3 text-sm">{k.text}</blockquote>
                      </details>
                    )}
                  </Card>
                </li>
              );
            })}
          </ul>
        </section>
        <section aria-labelledby="verifier">
          <h2 id="verifier" className="mb-2 font-display text-xl">{t("verifier")}</h2>
          {c.verifier_notes.length ? (
            <ul className="list-disc space-y-1 pl-5 text-sm">{c.verifier_notes.map((n, i) => <li key={i}>{n}</li>)}</ul>
          ) : <p className="text-sm text-fg-muted">{t("verifierEmpty")}</p>}
          {c.triage_reason && <p className="mt-2 data text-[11px] text-fg-muted">triage: {c.triage_reason} · revisions {c.revision_count}</p>}
        </section>
        <section aria-labelledby="decide" className="sticky bottom-4">
          <h2 id="decide" className="sr-only">{t("decisions")}</h2>
          <Card className="flex flex-wrap items-center gap-2 p-3">
            <Button variant="primary" onClick={() => decide("approve")} disabled={decided || busy} data-testid="approve"><span className="kbd">A</span>{t("approve")}</Button>
            <Button variant="danger" onClick={() => dialog.current?.showModal()} disabled={decided || busy} data-testid="reject"><span className="kbd">R</span>{t("reject")}</Button>
            <Button onClick={() => decide("escalate")} disabled={decided || busy} data-testid="escalate"><span className="kbd">E</span>{t("escalate")}</Button>
            <span aria-live="polite" className="ml-auto data text-fg-muted">{msg ?? (decided ? t(`status.${c.status}`) : "")}</span>
          </Card>
        </section>
        {c.decisions.length > 0 && (
          <section aria-labelledby="decisions-list">
            <h2 id="decisions-list" className="mb-2 font-display text-xl">{t("decisions")}</h2>
            <ul className="space-y-1 text-sm">{c.decisions.map((d) => <li key={d.id} className="data">{d.created_at.slice(0, 16)} · {d.officer_name} · {d.decision}{d.reason ? ` — ${d.reason}` : ""}</li>)}</ul>
          </section>
        )}
        <dialog ref={dialog} className="w-full max-w-md rounded border hairline bg-surface p-4 text-fg backdrop:bg-ink/60" aria-labelledby="reject-title">
          <h3 id="reject-title" className="font-display text-lg">{t("reject")}</h3>
          <label className="mt-2 block text-sm" htmlFor="reason">{t("reason")}</label>
          <textarea id="reason" value={reason} onChange={(e) => setReason(e.target.value)} rows={3} required data-testid="reject-reason"
            className="mt-1 w-full rounded border hairline bg-ground p-2 text-sm" />
          <div className="mt-3 flex justify-end gap-2">
            <Button onClick={() => dialog.current?.close()}>{t("cancel")}</Button>
            <Button variant="danger" onClick={() => decide("reject")} disabled={!reason.trim() || busy} data-testid="confirm-reject">{t("confirmReject")}</Button>
          </div>
        </dialog>
      </div>
    </article>
  );
}

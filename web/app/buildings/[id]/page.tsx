import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { notFound, redirect } from "next/navigation";
import { serverApi } from "@/lib/server-api";
import type { Timeline } from "@/lib/types";

export default async function BuildingPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const t = await getTranslations("change");
  let tl: Timeline | null;
  try { tl = await serverApi<Timeline>(`/buildings/${id}/timeline`); } catch { notFound(); }
  if (!tl) redirect(`/login?next=/buildings/${id}`);
  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="font-display text-3xl">{t("timeline")}</h1>
      <p className="data text-fg-muted">{tl.building_id} · {tl.chowkri_id ?? tl.zone}</p>
      <ol className="relative mt-6 space-y-6 border-l hairline pl-6">
        {tl.entries.map(({ change, decisions }) => (
          <li key={change.id} className="relative">
            <span aria-hidden className={`absolute -left-[1.6rem] top-1 h-3 w-3 rounded-full ${change.severity === "high" ? "bg-alarm" : "bg-sandstone"}`} />
            <p className="data text-fg-muted">{change.epoch_before} → {change.epoch_after}</p>
            <Link href={`/changes/${change.id}`} className="underline">{t(`types.${change.change_type}`)}</Link>
            <span className="ml-2 data text-fg-muted">{t(`status.${change.status}`)}</span>
            <ul className="mt-1 text-sm text-fg-muted">{decisions.map((d) => <li key={d.id} className="data">{d.created_at.slice(0, 10)} · {d.officer_name} · {d.decision}{d.reason ? ` — ${d.reason}` : ""}</li>)}</ul>
          </li>
        ))}
      </ol>
    </div>
  );
}

"use client";

import { useTranslations } from "next-intl";
import { useId, useState } from "react";

export function CompareSlider({ before, after, mask }: { before: string; after: string; mask: string }) {
  const t = useTranslations("change");
  const [pos, setPos] = useState(50);
  const [showMask, setShowMask] = useState(false);
  const id = useId();
  return (
    <figure className="space-y-2">
      <div className="relative aspect-square w-full select-none overflow-hidden rounded border hairline bg-ink">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={after} alt={t("after")} className="absolute inset-0 h-full w-full object-cover" draggable={false} />
        <div className="absolute inset-0 overflow-hidden" style={{ width: `${pos}%` }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={before} alt={t("before")} className="h-full w-full object-cover" style={{ width: `${10000 / pos}%`, maxWidth: "none" }} draggable={false} />
        </div>
        {showMask && /* eslint-disable-next-line @next/next/no-img-element */
          <img src={mask} alt={t("mask")} className="pointer-events-none absolute inset-0 h-full w-full object-cover opacity-60 mix-blend-screen" />}
        <div aria-hidden className="absolute inset-y-0 w-0.5 bg-plaster" style={{ left: `${pos}%` }} />
        <span className="absolute left-2 top-2 rounded bg-ink/70 px-1.5 font-mono text-[11px] text-plaster">{t("before")}</span>
        <span className="absolute right-2 top-2 rounded bg-ink/70 px-1.5 font-mono text-[11px] text-plaster">{t("after")}</span>
      </div>
      <label htmlFor={id} className="sr-only">{t("slider")}</label>
      <input id={id} type="range" min={0} max={100} value={pos} onChange={(e) => setPos(Number(e.target.value))}
        aria-label={t("slider")} className="w-full accent-sandstone" />
      <label className="flex items-center gap-2 text-xs text-fg-muted">
        <input type="checkbox" checked={showMask} onChange={(e) => setShowMask(e.target.checked)} className="accent-sandstone" />
        {t("mask")}
      </label>
    </figure>
  );
}

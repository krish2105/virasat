"use client";

import dynamic from "next/dynamic";
import { useTranslations } from "next-intl";
import { useMotionValue, useMotionValueEvent, useReducedMotion, useScroll, useTransform } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { CityFallback } from "./fallback";
import type { CityData } from "./types";

const CityScene = dynamic(() => import("./city-scene").then((m) => m.CityScene), { ssr: false });

function webglAvailable(): boolean {
  try { const c = document.createElement("canvas"); return !!(c.getContext("webgl2") || c.getContext("webgl")); } catch { return false; }
}

export function TimeScrub({ data }: { data: CityData }) {
  const t = useTranslations("landing");
  const reduced = useReducedMotion();
  const section = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  const [webgl, setWebgl] = useState<boolean | null>(null);
  const [sliderYear, setSliderYear] = useState(data.years[1]);
  const [yearLabel, setYearLabel] = useState(data.years[0]);
  const { scrollYProgress } = useScroll({ target: section, offset: ["start start", "end end"] });
  const scrolledYear = useTransform(scrollYProgress, [0, 1], [data.years[0], data.years[1]]);
  const manualYear = useMotionValue(data.years[1]);
  const manualProgress = useMotionValue(0.7);
  const year = reduced ? manualYear : scrolledYear;
  const progress = reduced ? manualProgress : scrollYProgress;

  useEffect(() => { manualYear.set(sliderYear); manualProgress.set((sliderYear - data.years[0]) / (data.years[1] - data.years[0])); }, [sliderYear, manualYear, manualProgress, data.years]);
  useMotionValueEvent(year, "change", (v) => setYearLabel(Math.round(v)));
  useEffect(() => {
    setWebgl(!new URLSearchParams(window.location.search).has("nogl") && webglAvailable());
    const el = section.current; if (!el) return;
    const io = new IntersectionObserver(([e]) => setVisible(e.isIntersecting), { rootMargin: "200px" });
    io.observe(el); return () => io.disconnect();
  }, []);

  // Lenis smooth scroll drives the scroll progress; skipped under reduced motion.
  useEffect(() => {
    if (reduced) return;
    let lenis: { raf: (t: number) => void; destroy: () => void } | undefined;
    let raf = 0;
    import("lenis").then(({ default: Lenis }) => {
      lenis = new Lenis({ lerp: 0.1 });
      const loop = (time: number) => { lenis!.raf(time); raf = requestAnimationFrame(loop); };
      raf = requestAnimationFrame(loop);
    });
    return () => { cancelAnimationFrame(raf); lenis?.destroy(); };
  }, [reduced]);

  const stage = (
    <div className="sticky top-14 h-[calc(100vh-3.5rem)] w-full">
      <div className="absolute inset-0" data-testid="city-stage">
        {webgl === false || !visible ? (
          <div className="h-full w-full p-6"><CityFallback data={data} year={reduced ? sliderYear : yearLabel} /></div>
        ) : (
          <CityScene data={data} year={year} progress={progress} onContextLost={() => setWebgl(false)} />
        )}
      </div>
      <div className="pointer-events-none absolute left-4 top-4 rounded bg-ground/85 px-3 py-2 backdrop-blur">
        <p className="font-mono text-[11px] uppercase tracking-widest text-fg-muted">{t("year")}</p>
        <p className="font-display text-5xl tabular-nums" data-testid="year-label" aria-live="polite">{reduced ? sliderYear : yearLabel}</p>
        <p className="mt-1 max-w-xs text-xs text-fg-muted">{t("ghosts")}</p>
      </div>
      {reduced && (
        <label className="absolute bottom-6 left-4 right-4 rounded bg-ground/85 p-3 text-sm backdrop-blur">
          {t("reduced")}
          <input type="range" min={data.years[0]} max={data.years[1]} value={sliderYear} onChange={(e) => setSliderYear(Number(e.target.value))}
            aria-label={t("year")} data-testid="year-slider" className="mt-2 w-full accent-sandstone" />
        </label>
      )}
    </div>
  );
  return (
    <div ref={section} className={reduced ? "h-[calc(100vh-3.5rem)]" : "h-[400vh]"} aria-label={t("scrub")}>
      {stage}
    </div>
  );
}

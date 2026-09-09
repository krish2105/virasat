import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { promises as fs } from "fs";
import path from "path";
import { TimeScrub } from "@/components/city/time-scrub";
import type { CityData } from "@/components/city/types";
import { AggregateMap } from "@/components/city/aggregate-map";

export default async function Landing() {
  const t = await getTranslations("landing");
  const raw = await fs.readFile(path.join(process.cwd(), "public", "city.json"), "utf8");
  const data = JSON.parse(raw) as CityData;
  return (
    <>
      <section className="mx-auto grid max-w-7xl grid-cols-1 gap-6 px-4 pb-8 pt-16 md:grid-cols-chowkri">
        <div className="md:col-span-6">
          <p className="font-mono text-[11px] uppercase tracking-widest text-sandstone">{t("deadline")}</p>
          <h1 className="mt-3 font-display text-5xl leading-[1.05] sm:text-7xl">{t("hero")}</h1>
          <p className="mt-6 max-w-xl text-lg text-fg-muted">{t("sub")}</p>
          <Link href="/queue" className="mt-8 inline-block rounded bg-indigo px-4 py-2 text-plaster dark:text-ink">{t("openQueue")} →</Link>
        </div>
        <div className="md:col-span-3 md:border-l hairline md:pl-6">
          <dl className="grid grid-cols-2 gap-4 text-sm md:grid-cols-1">
            <div><dt className="font-mono text-[11px] uppercase tracking-widest text-fg-muted">property</dt><dd className="data">643 ha · 9 chowkris</dd></div>
            <div><dt className="font-mono text-[11px] uppercase tracking-widest text-fg-muted">buffer</dt><dd className="data">1,994 ha</dd></div>
            <div><dt className="font-mono text-[11px] uppercase tracking-widest text-fg-muted">buildings modelled</dt><dd className="data">{data.buildings.length.toLocaleString()}</dd></div>
            <div><dt className="font-mono text-[11px] uppercase tracking-widest text-fg-muted">change candidates</dt><dd className="data">{data.buildings.filter((b) => b.change).length} · 2016→2023</dd></div>
          </dl>
        </div>
      </section>
      <p className="mx-auto max-w-7xl px-4 pb-2 font-mono text-[11px] uppercase tracking-widest text-fg-muted">{t("scrub")} ↓</p>
      <TimeScrub data={data} />
      <section className="mx-auto max-w-7xl px-4 py-16" aria-labelledby="map-title">
        <h2 id="map-title" className="font-display text-3xl">Aggregate by chowkri</h2>
        <p className="mb-4 max-w-2xl text-sm text-fg-muted">Public view. Counts per ward only — no individual property is identifiable here.</p>
        <AggregateMap />
      </section>
    </>
  );
}

"use client";

import { useEffect, useRef, useState } from "react";
import type { Aggregate } from "@/lib/types";

/* MapLibre + chowkri choropleth from /map/aggregate. OpenFreeMap style: no token. */
export function AggregateMap() {
  const el = useRef<HTMLDivElement>(null);
  const [agg, setAgg] = useState<Aggregate | null>(null);
  useEffect(() => { fetch("/api/map/aggregate").then((r) => r.json()).then(setAgg).catch(() => setAgg(null)); }, []);
  useEffect(() => {
    if (!el.current || !agg) return;
    let map: import("maplibre-gl").Map | undefined;
    Promise.all([import("maplibre-gl"), fetch("/chowkris.geojson").then((r) => r.json())]).then(([maplibre, chowkris]) => {
      const counts: Record<string, number> = {};
      for (const c of agg.cells) counts[c.chowkri_id] = Object.values(c.counts_by_type).reduce((a, b) => a + b, 0);
      const max = Math.max(1, ...Object.values(counts));
      for (const f of chowkris.features) { f.properties.count = counts[f.properties.name] ?? 0; f.properties.share = (counts[f.properties.name] ?? 0) / max; }
      map = new maplibre.Map({ container: el.current!, style: "https://tiles.openfreemap.org/styles/positron", center: [75.826, 26.924], zoom: 13.6, attributionControl: false });
      map.addControl(new maplibre.AttributionControl({ compact: false, customAttribution: agg.attribution }));
      map.addControl(new maplibre.NavigationControl({ showCompass: false }));
      map.on("load", () => {
        map!.addSource("chowkris", { type: "geojson", data: chowkris });
        map!.addLayer({ id: "chowkri-fill", type: "fill", source: "chowkris", paint: { "fill-color": "#C1622E", "fill-opacity": ["interpolate", ["linear"], ["get", "share"], 0, 0.08, 1, 0.65] } });
        map!.addLayer({ id: "chowkri-line", type: "line", source: "chowkris", paint: { "line-color": "#23304A", "line-width": 1.2 } });
        map!.addLayer({ id: "chowkri-label", type: "symbol", source: "chowkris", layout: { "text-field": ["concat", ["get", "name"], "\n", ["to-string", ["get", "count"]]], "text-size": 11, "text-font": ["Noto Sans Regular"] }, paint: { "text-color": "#1A1614", "text-halo-color": "#F2EBE0", "text-halo-width": 1.2 } });
      });
    });
    return () => map?.remove();
  }, [agg]);
  return (
    <div>
      <link rel="stylesheet" href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" />
      <div ref={el} className="h-[480px] w-full rounded border hairline" role="region" aria-label="Chowkri aggregate map" />
      {agg && <ul className="mt-3 grid grid-cols-3 gap-2 text-xs sm:grid-cols-9">{agg.cells.map((c) => <li key={c.chowkri_id} className="rounded border hairline p-2"><span className="block truncate">{c.chowkri_id}</span><span className="data">{Object.values(c.counts_by_type).reduce((a, b) => a + b, 0)}</span></li>)}</ul>}
    </div>
  );
}

import type { CityData } from "./types";

/* Static isometric SVG: the page stays useful without WebGL. Intentional, not broken. */
export function CityFallback({ data, year }: { data: CityData; year: number }) {
  const iso = ([x, y]: [number, number]) => [(x - y) * 0.7, (x + y) * 0.35] as const;
  const pts = data.buildings.flatMap((b) => b.ring.map(iso));
  const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
  const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
  return (
    <svg viewBox={`${minX - 50} ${minY - 120} ${maxX - minX + 100} ${maxY - minY + 200}`} role="img" aria-label="Isometric massing of the Jaipur walled city"
      className="h-full w-full">
      {data.core.map((r, i) => <polygon key={`c${i}`} points={r.map(iso).map((p) => p.join(",")).join(" ")} fill="none" stroke="#C4361F" strokeWidth={4} />)}
      {data.buildings.map((b) => {
        const ch = b.change;
        const gone = ch?.type === "DEMOLITION" && year >= ch.year;
        const flagged = ch && year >= ch.year;
        const h = (ch?.type === "VERTICAL_ADDITION" && flagged ? b.h * 1.5 : b.h) * 1.2;
        const base = b.ring.map(iso);
        const top = base.map(([x, y]) => [x, y - h] as const);
        const fill = gone ? "none" : flagged ? "#C4361F" : b.core ? "#C1622E" : "#E8DCC6";
        return (
          <g key={b.id} stroke={gone ? "#23304A" : "#1A1614"} strokeWidth={gone ? 1.2 : 0.6} strokeOpacity={gone ? 0.8 : 0.35} strokeDasharray={gone ? "4 3" : undefined}>
            {!gone && base.map((p, i) => { const q = base[(i + 1) % base.length]; return <polygon key={i} points={`${p} ${q} ${top[(i + 1) % base.length]} ${top[i]}`} fill={fill} fillOpacity={0.8} />; })}
            <polygon points={top.map((p) => p.join(",")).join(" ")} fill={gone ? "none" : fill} />
          </g>
        );
      })}
    </svg>
  );
}

import { cookies } from "next/headers";

const API = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Server-side fetch that forwards the officer session cookie. Returns null on 401. */
export async function serverApi<T>(path: string): Promise<T | null> {
  const store = await cookies();
  const session = store.get("virasat_session")?.value;
  const res = await fetch(`${API}${path}`, {
    headers: session ? { cookie: `virasat_session=${session}` } : {},
    cache: "no-store",
  });
  if (res.status === 401) return null;
  if (!res.ok) throw new Error(`${path}: ${res.status}`);
  return res.json() as Promise<T>;
}

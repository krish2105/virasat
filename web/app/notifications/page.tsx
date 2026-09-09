"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Notification } from "@/lib/types";
import { Card } from "@/components/ui/primitives";

export default function NotificationsPage() {
  const t = useTranslations("nav");
  const [items, setItems] = useState<Notification[]>([]);
  const load = () => api<Notification[]>("/notifications").then(setItems).catch(() => setItems([]));
  useEffect(() => { load(); }, []);
  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="mb-4 font-display text-3xl">{t("notifications")}</h1>
      <ul className="space-y-2">
        {items.map((n) => (
          <li key={n.id}>
            <Card className={`p-3 ${n.read_at ? "opacity-60" : ""}`}>
              <p className="text-sm font-medium">{n.title}</p>
              <p className="text-sm text-fg-muted">{n.body}</p>
              <p className="mt-1 data text-[11px] text-fg-muted">{n.created_at.slice(0, 16)} · {n.kind}
                {n.change_id && <> · <Link className="underline" href={`/changes/${n.change_id}`}>open</Link></>}
                {!n.read_at && <> · <button className="underline" onClick={() => api(`/notifications/${n.id}/read`, { method: "POST" }).then(load)}>mark read</button></>}
              </p>
            </Card>
          </li>
        ))}
        {items.length === 0 && <li className="text-sm text-fg-muted">—</li>}
      </ul>
    </div>
  );
}

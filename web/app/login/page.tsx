"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Suspense, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { Button, Card, Label } from "@/components/ui/primitives";

function LoginForm() {
  const t = useTranslations("login");
  const router = useRouter();
  const params = useSearchParams();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/auth/login", { method: "POST", body: JSON.stringify({ username, password }) });
      router.push(params.get("next") ?? "/queue");
      router.refresh();
    } catch (err) {
      setError(err instanceof ApiError && err.status === 401 ? t("failed") : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4" aria-describedby="login-note">
      <h1 className="font-display text-3xl">{t("title")}</h1>
      <div>
        <label htmlFor="username"><Label>{t("username")}</Label></label>
        <input id="username" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} required
          className="mt-1 w-full rounded border hairline bg-ground px-3 py-2 font-mono text-sm" />
      </div>
      <div>
        <label htmlFor="password"><Label>{t("password")}</Label></label>
        <input id="password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required
          className="mt-1 w-full rounded border hairline bg-ground px-3 py-2 font-mono text-sm" />
      </div>
      {error && <p role="alert" className="text-sm text-alarm">{error}</p>}
      <Button type="submit" variant="primary" disabled={busy} data-testid="login-submit">{t("submit")}</Button>
      <p id="login-note" className="text-xs text-fg-muted">{t("note")}</p>
    </form>
  );
}

export default function LoginPage() {
  return (
    <div className="mx-auto max-w-md px-4 py-16">
      <Card className="p-6">
        <Suspense><LoginForm /></Suspense>
      </Card>
    </div>
  );
}

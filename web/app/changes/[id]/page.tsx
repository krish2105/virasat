import { notFound, redirect } from "next/navigation";
import { ChangeReview } from "@/components/queue/change-review";
import { serverApi } from "@/lib/server-api";
import type { ChangeDetail } from "@/lib/types";

export default async function ChangePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let detail: ChangeDetail | null;
  try { detail = await serverApi<ChangeDetail>(`/changes/${id}`); } catch { notFound(); }
  if (!detail) redirect(`/login?next=/changes/${id}`);
  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <p className="mb-3 data text-fg-muted">change {detail.id}</p>
      <ChangeReview initial={detail} />
    </div>
  );
}

import { Suspense } from "react";
import { QueueList } from "@/components/queue/queue-list";

export default function QueuePage() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <Suspense><QueueList /></Suspense>
    </div>
  );
}

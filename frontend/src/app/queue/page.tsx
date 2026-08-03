"use client";

import { useEffect, useState } from "react";
import { fetchTeamQueue, type QueueResponse } from "@/lib/api";
import { useApiToken } from "@/hooks/useApiToken";
import { QueueList } from "@/components/QueueList";

export default function TeamQueuePage() {
  const { getToken, isLoaded, isSignedIn } = useApiToken();
  const [data, setData] = useState<QueueResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    (async () => {
      try {
        const token = await getToken();
        setData(await fetchTeamQueue(token));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load");
      }
    })();
  }, [getToken, isLoaded, isSignedIn]);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl tracking-tight">Team Queue</h1>
        <p className="mt-2 max-w-xl text-[var(--muted)]">
          Everyone’s shared pipeline, ranked by the firm score. Use Settings to
          tune what shows up in My Queue for you.
        </p>
      </div>

      {error && (
        <pre className="overflow-x-auto border border-[var(--border)] bg-[var(--panel)] p-4 text-xs text-[var(--muted)]">
          {error}
        </pre>
      )}

      <QueueList
        items={data?.items ?? []}
        emptyText="No scored companies yet. Add tracking areas in Settings — the pipeline fills this automatically."
      />
    </div>
  );
}

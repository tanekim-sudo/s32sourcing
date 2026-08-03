"use client";

import { useEffect, useState } from "react";
import { fetchMyQueue, type QueueResponse } from "@/lib/api";
import { useApiToken } from "@/hooks/useApiToken";
import { QueueList } from "@/components/QueueList";

export function MyQueue() {
  const { getToken, isLoaded, isSignedIn } = useApiToken();
  const [data, setData] = useState<QueueResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) {
      setLoading(false);
      return;
    }

    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        const token = await getToken();
        const queue = await fetchMyQueue(token);
        if (!cancelled) {
          setData(queue);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load queue");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [getToken, isLoaded, isSignedIn]);

  if (!isLoaded || loading) {
    return <p className="text-[var(--muted)]">Loading your queue…</p>;
  }

  if (error) {
    return (
      <div className="space-y-3">
        <p className="text-[var(--muted)]">
          Couldn’t reach the API at{" "}
          <code>{process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}</code>.
        </p>
        <p className="text-sm text-[var(--muted)]">
          On Vercel, localhost will not work. Deploy the backend with the Render
          blueprint (<code>render.yaml</code>), set{" "}
          <code>NEXT_PUBLIC_API_URL</code> to that HTTPS URL, then redeploy.
        </p>
        <pre className="overflow-x-auto border border-[var(--border)] bg-[var(--panel)] p-4 text-xs text-[var(--muted)]">
          {error}
        </pre>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl tracking-tight">My Queue</h1>
        <p className="mt-2 max-w-xl text-[var(--muted)]">
          Companies matching what you track, ranked for your priorities. Update
          those anytime in Settings.
        </p>
        {data?.partner && (
          <p className="mt-3 text-sm text-[var(--muted)]">
            Signed in as {data.partner.name} ({data.partner.email})
          </p>
        )}
      </div>
      <QueueList
        items={data?.items ?? []}
        showOverlay
        emptyText="No companies in your queue yet. Add thesis configs / watchlist entries, then run the shared sourcing pipeline."
      />
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { fetchMyQueue, type QueueResponse } from "@/lib/api";
import { useApiToken } from "@/hooks/useApiToken";
import { QueueList } from "@/components/QueueList";
import { SetupGate } from "@/components/SetupGate";

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
    return <p className="text-[var(--muted)]">Loading…</p>;
  }

  if (error) {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    return (
      <div className="space-y-3">
        <p className="text-[var(--muted)]">
          Couldn’t reach the API at <code>{apiUrl}</code>.
        </p>
        <pre className="overflow-x-auto border border-[var(--border)] bg-[var(--panel)] p-4 text-xs text-[var(--muted)]">
          {error}
        </pre>
      </div>
    );
  }

  if (data?.setup_required) {
    return <SetupGate title="My Queue" />;
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl tracking-tight">My Queue</h1>
        <p className="mt-2 max-w-xl text-[var(--muted)]">
          Only companies matching what you track, ranked for your priorities.
        </p>
      </div>
      <QueueList
        items={data?.items ?? []}
        showOverlay
        emptyText="No matches yet for your tracking areas. The pipeline will fill this as signals arrive."
      />
    </div>
  );
}

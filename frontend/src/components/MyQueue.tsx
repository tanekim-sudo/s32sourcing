"use client";

import { useEffect, useState } from "react";
import {
  fetchMyQueue,
  refreshResearch,
  type QueueResponse,
} from "@/lib/api";
import { useApiToken } from "@/hooks/useApiToken";
import { QueueList } from "@/components/QueueList";
import { SetupGate } from "@/components/SetupGate";

export function MyQueue() {
  const { getToken, isLoaded, isSignedIn } = useApiToken();
  const [data, setData] = useState<QueueResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshMsg, setRefreshMsg] = useState<string | null>(null);

  const load = async () => {
    const token = await getToken();
    setData(await fetchMyQueue(token));
  };

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
        await load();
        if (!cancelled) setError(null);
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [getToken, isLoaded, isSignedIn]);

  const onRefresh = async () => {
    setRefreshing(true);
    setRefreshMsg(null);
    try {
      const token = await getToken();
      const res = await refreshResearch(token);
      const pulled = Object.values(res.report.adapters || {}).reduce(
        (sum: number, a) => {
          const n = (a as { pulled?: number })?.pulled || 0;
          return sum + n;
        },
        0
      );
      setRefreshMsg(
        `Research complete — ${pulled} signals pulled, ${(res.report.scored as unknown[])?.length ?? 0} scored.`
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Refresh failed");
    } finally {
      setRefreshing(false);
    }
  };

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
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl tracking-tight">My Queue</h1>
          <p className="mt-2 max-w-xl text-[var(--muted)]">
            Ranked with your priority weights. Refresh runs full research on your
            tracking areas.
          </p>
        </div>
        <button
          type="button"
          disabled={refreshing}
          onClick={onRefresh}
          className="border border-[var(--border)] bg-[var(--panel)] px-4 py-2 text-sm disabled:opacity-50"
        >
          {refreshing ? "Researching…" : "Refresh research"}
        </button>
      </div>

      {refreshMsg && (
        <p className="text-sm text-[var(--accent)]">{refreshMsg}</p>
      )}

      <QueueList
        items={data?.items ?? []}
        showOverlay
        emptyText="No matches yet. Hit Refresh research after saving tracking areas."
      />
    </div>
  );
}

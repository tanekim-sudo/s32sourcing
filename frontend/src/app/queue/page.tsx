"use client";

import { useEffect, useState } from "react";
import { fetchTeamQueue, runPipeline, type QueueResponse } from "@/lib/api";
import { useApiToken } from "@/hooks/useApiToken";
import { QueueList } from "@/components/QueueList";

export default function TeamQueuePage() {
  const { getToken, isLoaded, isSignedIn } = useApiToken();
  const [data, setData] = useState<QueueResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [pipelineMsg, setPipelineMsg] = useState<string | null>(null);

  const load = async () => {
    const token = await getToken();
    const queue = await fetchTeamQueue(token);
    setData(queue);
    setError(null);
  };

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    load().catch((err) =>
      setError(err instanceof Error ? err.message : "Failed to load")
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoaded, isSignedIn]);

  const onRunPipeline = async () => {
    setBusy(true);
    setPipelineMsg(null);
    try {
      const token = await getToken();
      const res = await runPipeline(token);
      setPipelineMsg(JSON.stringify(res.report, null, 2));
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Pipeline failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl tracking-tight">Team Queue</h1>
          <p className="mt-2 max-w-xl text-[var(--muted)]">
            All scored companies ranked by the shared firm base rubric.
          </p>
        </div>
        <button
          type="button"
          onClick={onRunPipeline}
          disabled={busy}
          className="border border-[var(--border)] bg-[var(--panel)] px-4 py-2 text-sm hover:border-[var(--accent)] disabled:opacity-50"
        >
          {busy ? "Running…" : "Run pipeline"}
        </button>
      </div>

      {error && (
        <pre className="overflow-x-auto border border-[var(--border)] bg-[var(--panel)] p-4 text-xs text-[var(--muted)]">
          {error}
        </pre>
      )}

      <QueueList
        items={data?.items ?? []}
        emptyText="No scored companies yet. Seed demo data or run the pipeline."
      />

      {pipelineMsg && (
        <pre className="overflow-x-auto border border-[var(--border)] bg-[var(--panel)] p-4 text-xs text-[var(--muted)]">
          {pipelineMsg}
        </pre>
      )}
    </div>
  );
}

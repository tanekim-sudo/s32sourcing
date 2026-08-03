"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import {
  addWatchlist,
  clearFlag,
  fetchCompany,
  setFlag,
  shareToTeam,
  unshareFromTeam,
  type CompanyDetail,
} from "@/lib/api";
import { useApiToken } from "@/hooks/useApiToken";

function subscoreValue(raw: unknown): number | null {
  if (typeof raw === "number") return raw;
  if (raw && typeof raw === "object" && "score" in raw) {
    const n = Number((raw as { score: unknown }).score);
    return Number.isFinite(n) ? n : null;
  }
  return null;
}

export default function CompanyPage() {
  const params = useParams();
  const id = Number(params.id);
  const { getToken, isLoaded, isSignedIn } = useApiToken();
  const [data, setData] = useState<CompanyDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const load = async () => {
    const token = await getToken();
    setData(await fetchCompany(token, id));
  };

  useEffect(() => {
    if (!isLoaded || !isSignedIn || !Number.isFinite(id)) return;
    load().catch((err) =>
      setError(err instanceof Error ? err.message : "Failed to load")
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoaded, isSignedIn, id]);

  const onFlag = async (flag: string) => {
    const token = await getToken();
    if (data?.my_flag === flag) {
      await clearFlag(token, id);
      setMsg("Flag cleared");
    } else {
      await setFlag(token, id, { flag });
      setMsg(`Flagged: ${flag.replace("_", " ")}`);
    }
    await load();
  };

  const onShare = async () => {
    const token = await getToken();
    if (data?.shared_to_team) {
      await unshareFromTeam(token, id);
      setMsg("Removed from Team Queue");
    } else {
      await shareToTeam(token, id);
      setMsg("Shared to Team Queue — others can adopt it");
    }
    await load();
  };

  const onWatchlist = async () => {
    const token = await getToken();
    await addWatchlist(token, { company_id: id });
    setMsg("Added to your watchlist");
    await load();
  };

  if (error) {
    return (
      <pre className="overflow-x-auto border border-[var(--border)] bg-[var(--panel)] p-4 text-xs">
        {error}
      </pre>
    );
  }

  if (!data) {
    return <p className="text-[var(--muted)]">Loading company…</p>;
  }

  return (
    <div className="space-y-10">
      <div className="flex flex-wrap items-start justify-between gap-6">
        <div>
          <h1 className="text-3xl tracking-tight">{data.name}</h1>
          {data.domain && (
            <p className="mt-1 text-[var(--muted)]">{data.domain}</p>
          )}
          {data.description && (
            <p className="mt-4 max-w-2xl text-[var(--muted)]">{data.description}</p>
          )}
          {data.shared_by && data.shared_by.length > 0 && (
            <p className="mt-2 text-sm text-[var(--muted)]">
              On Team Queue via: {data.shared_by.join(", ")}
            </p>
          )}
        </div>
        <div className="text-right">
          <div className="text-sm text-[var(--muted)]">Your score (weights applied)</div>
          <div className="text-3xl tabular-nums">
            {data.overlay_score?.toFixed(1) ?? "—"}
          </div>
          <div className="mt-1 text-sm text-[var(--muted)]">
            Firm {data.base_score?.toFixed(1) ?? "—"}
          </div>
        </div>
      </div>

      {msg && <p className="text-sm text-[var(--accent)]">{msg}</p>}

      <div className="flex flex-wrap gap-2">
        {!data.on_my_watchlist && (
          <button
            type="button"
            onClick={onWatchlist}
            className="border border-[var(--border)] px-3 py-2 text-sm"
          >
            Add to watchlist
          </button>
        )}
        <button
          type="button"
          onClick={onShare}
          className="border border-[var(--border)] bg-[var(--panel)] px-3 py-2 text-sm"
        >
          {data.shared_to_team ? "Remove from Team Queue" : "Share with team"}
        </button>
        {(
          [
            ["interesting", "Interesting"],
            ["follow_up", "Follow up"],
            ["pass", "Pass"],
          ] as const
        ).map(([value, label]) => (
          <button
            key={value}
            type="button"
            onClick={() => onFlag(value)}
            className={
              data.my_flag === value
                ? "border border-[var(--accent)] px-3 py-2 text-sm text-[var(--accent)]"
                : "border border-[var(--border)] px-3 py-2 text-sm"
            }
          >
            {label}
          </button>
        ))}
      </div>

      {data.why_note && (
        <section>
          <h2 className="text-xl">Why this matters</h2>
          <p className="mt-2 max-w-3xl text-[var(--muted)]">{data.why_note}</p>
          {data.partner_lines.map((line) => (
            <p key={line} className="mt-2 text-sm text-[var(--accent)]">
              {line}
            </p>
          ))}
        </section>
      )}

      <section>
        <h2 className="text-xl">Score breakdown</h2>
        <ul className="mt-4 divide-y divide-[var(--border)] border-y border-[var(--border)]">
          {Object.entries(data.subscores || {}).map(([dim, raw]) => {
            const score = subscoreValue(raw);
            const ev = (data.evidence?.[dim] || {}) as { citations?: string[] };
            return (
              <li key={dim} className="py-3">
                <div className="flex justify-between gap-4">
                  <span className="font-medium">{dim.replace(/_/g, " ")}</span>
                  <span className="tabular-nums">{score?.toFixed(1) ?? "—"}</span>
                </div>
                {ev.citations && ev.citations.length > 0 && (
                  <p className="mt-1 text-sm text-[var(--muted)]">
                    {ev.citations.join(" · ")}
                  </p>
                )}
              </li>
            );
          })}
        </ul>
      </section>

      <section>
        <h2 className="text-xl">Signals</h2>
        <ul className="mt-4 space-y-3">
          {data.signals.map((s) => (
            <li key={s.id} className="border-l-2 border-[var(--border)] pl-4">
              <div className="text-xs uppercase tracking-wide text-[var(--muted)]">
                {s.source}
              </div>
              <div>{s.title}</div>
              {s.summary && (
                <p className="mt-1 text-sm text-[var(--muted)]">{s.summary}</p>
              )}
            </li>
          ))}
          {data.signals.length === 0 && (
            <p className="text-[var(--muted)]">No signals yet — run research.</p>
          )}
        </ul>
      </section>
    </div>
  );
}

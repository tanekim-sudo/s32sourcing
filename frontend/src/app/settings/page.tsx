"use client";

import { useEffect, useState } from "react";
import {
  createCompany,
  createThesis,
  deleteThesis,
  fetchMyThesis,
  fetchOverlay,
  fetchSharedThesis,
  fetchWatchlist,
  removeWatchlist,
  saveOverlay,
  updateThesis,
  type ThesisConfig,
  type WatchlistEntry,
} from "@/lib/api";
import { useApiToken } from "@/hooks/useApiToken";

/** Partner-facing labels — no pipeline jargon. */
const PRIORITIES = [
  {
    key: "founder_quality",
    label: "Founder quality",
    help: "Background, domain expertise, team",
  },
  {
    key: "market_timing_fit",
    label: "Market timing",
    help: "Category inflection and timing",
  },
  {
    key: "vc_attention",
    label: "Prefer quieter deals",
    help: "Higher = penalize crowded / overhyped more",
    // UI slider maps to more-negative weight (care more about low attention)
    invertDisplay: true,
  },
  {
    key: "traction_signal",
    label: "Traction",
    help: "Users, revenue, hiring, GitHub activity",
  },
  {
    key: "network_proximity",
    label: "Warm path / network",
    help: "Affinity relationships and intros",
  },
] as const;

function parseTopics(text: string): string[] {
  return text
    .split(/[\n,]/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function topicsToText(topics: string[]): string {
  return topics.join(", ");
}

/** Map UI slider (-2..+2) ↔ weight delta. */
function sliderToDelta(v: number, invert?: boolean): number {
  const n = Number(v);
  return (invert ? -n : n) * 0.05;
}

function deltaToSlider(delta: number, invert?: boolean): number {
  const raw = delta / 0.05;
  return Math.round(invert ? -raw : raw);
}

export default function SettingsPage() {
  const { getToken, isLoaded, isSignedIn } = useApiToken();
  const [areas, setAreas] = useState<ThesisConfig[]>([]);
  const [shared, setShared] = useState<ThesisConfig[]>([]);
  const [watchlist, setWatchlist] = useState<WatchlistEntry[]>([]);
  const [priorities, setPriorities] = useState<Record<string, number>>({
    founder_quality: 0,
    market_timing_fit: 0,
    vc_attention: 0,
    traction_signal: 0,
    network_proximity: 0,
  });
  const [error, setError] = useState<string | null>(null);
  const [savedMsg, setSavedMsg] = useState<string | null>(null);

  const [areaName, setAreaName] = useState("");
  const [areaTopics, setAreaTopics] = useState("");
  const [coName, setCoName] = useState("");
  const [coDomain, setCoDomain] = useState("");
  const [coNote, setCoNote] = useState("");

  const load = async () => {
    const token = await getToken();
    const [t, s, w, o] = await Promise.all([
      fetchMyThesis(token),
      fetchSharedThesis(token),
      fetchWatchlist(token),
      fetchOverlay(token),
    ]);
    setAreas(t);
    setShared(s);
    setWatchlist(w);
    const next: Record<string, number> = {
      founder_quality: 0,
      market_timing_fit: 0,
      vc_attention: 0,
      traction_signal: 0,
      network_proximity: 0,
    };
    const adj = o?.weight_adjustments || {};
    for (const p of PRIORITIES) {
      next[p.key] = deltaToSlider(Number(adj[p.key] || 0), "invertDisplay" in p && p.invertDisplay);
    }
    setPriorities(next);
  };

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    load().catch((err) =>
      setError(err instanceof Error ? err.message : "Failed to load settings")
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoaded, isSignedIn]);

  const flash = (msg: string) => {
    setSavedMsg(msg);
    setTimeout(() => setSavedMsg(null), 2500);
  };

  const addArea = async (e: React.FormEvent) => {
    e.preventDefault();
    const topics = parseTopics(areaTopics);
    if (!areaName.trim() || topics.length === 0) return;
    const token = await getToken();
    await createThesis(token, {
      name: areaName.trim(),
      topics,
      is_active: true,
      is_shared: false,
    });
    setAreaName("");
    setAreaTopics("");
    await load();
    flash("Tracking area saved");
  };

  const savePriorities = async () => {
    const token = await getToken();
    const weight_adjustments: Record<string, number> = {};
    for (const p of PRIORITIES) {
      weight_adjustments[p.key] = sliderToDelta(
        priorities[p.key] ?? 0,
        "invertDisplay" in p && p.invertDisplay
      );
    }
    await saveOverlay(token, {
      base_rubric_version: "1.0.0",
      weight_adjustments,
      added_dimensions: [],
    });
    flash("Priorities saved — your queue will re-rank");
  };

  const addCompany = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!coName.trim()) return;
    const token = await getToken();
    const company = await createCompany(token, {
      name: coName.trim(),
      domain: coDomain.trim() || undefined,
    });
    const { addWatchlist } = await import("@/lib/api");
    await addWatchlist(token, {
      company_id: company.id,
      note: coNote.trim() || undefined,
    });
    setCoName("");
    setCoDomain("");
    setCoNote("");
    await load();
    flash("Added to your watchlist");
  };

  return (
    <div className="space-y-14">
      <div>
        <h1 className="text-3xl tracking-tight">Settings</h1>
        <p className="mt-2 max-w-xl text-[var(--muted)]">
          Tell us what you care about. We handle search, scoring, and CRM wiring
          in the background.
        </p>
        {savedMsg && (
          <p className="mt-3 text-sm text-[var(--accent)]">{savedMsg}</p>
        )}
        {error && (
          <pre className="mt-3 overflow-x-auto border border-[var(--border)] bg-[var(--panel)] p-3 text-xs">
            {error}
          </pre>
        )}
      </div>

      {/* ── Areas ─────────────────────────────────────────────── */}
      <section id="areas" className="space-y-5">
        <div>
          <h2 className="text-xl">Areas I track</h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Name an area and list topics in plain English. Example topics:
            “AI infrastructure”, “specialty clinic software”.
          </p>
        </div>

        <ul className="divide-y divide-[var(--border)] border-y border-[var(--border)]">
          {areas.map((a) => (
            <li key={a.id} className="flex items-start justify-between gap-4 py-4">
              <div>
                <div className="font-medium">
                  {a.name}
                  {!a.is_active && (
                    <span className="ml-2 text-sm text-[var(--muted)]">paused</span>
                  )}
                </div>
                <p className="mt-1 text-sm text-[var(--muted)]">
                  {topicsToText((a.keywords as string[]) || []) || "—"}
                </p>
              </div>
              <div className="flex gap-2 text-sm">
                <button
                  type="button"
                  className="border border-[var(--border)] px-2 py-1"
                  onClick={async () => {
                    const token = await getToken();
                    await updateThesis(token, a.id, { is_active: !a.is_active });
                    await load();
                  }}
                >
                  {a.is_active ? "Pause" : "Resume"}
                </button>
                <button
                  type="button"
                  className="border border-[var(--border)] px-2 py-1"
                  onClick={async () => {
                    const token = await getToken();
                    await deleteThesis(token, a.id);
                    await load();
                  }}
                >
                  Remove
                </button>
              </div>
            </li>
          ))}
          {areas.length === 0 && (
            <li className="py-4 text-[var(--muted)]">
              No personal areas yet — add one below.
            </li>
          )}
        </ul>

        {shared.length > 0 && (
          <div className="text-sm text-[var(--muted)]">
            <span className="font-medium text-[var(--fg)]">Firm-wide also tracking: </span>
            {shared.map((s) => s.name).join(" · ")}
          </div>
        )}

        <form
          onSubmit={addArea}
          className="grid gap-3 border border-[var(--border)] p-4"
        >
          <label className="grid gap-1 text-sm">
            <span>Area name</span>
            <input
              required
              value={areaName}
              onChange={(e) => setAreaName(e.target.value)}
              placeholder="e.g. Healthcare workflows"
              className="border border-[var(--border)] bg-transparent px-3 py-2"
            />
          </label>
          <label className="grid gap-1 text-sm">
            <span>Topics to track (comma-separated)</span>
            <textarea
              required
              value={areaTopics}
              onChange={(e) => setAreaTopics(e.target.value)}
              placeholder="healthcare, clinic software, workflow automation"
              rows={2}
              className="border border-[var(--border)] bg-transparent px-3 py-2"
            />
          </label>
          <button
            type="submit"
            className="w-fit border border-[var(--border)] bg-[var(--panel)] px-4 py-2 text-sm"
          >
            Save area
          </button>
        </form>
      </section>

      {/* ── Watchlist ─────────────────────────────────────────── */}
      <section id="watchlist" className="space-y-5">
        <div>
          <h2 className="text-xl">Companies I watch</h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Always show these in My Queue, even if they don’t match a topic yet.
          </p>
        </div>

        <ul className="divide-y divide-[var(--border)] border-y border-[var(--border)]">
          {watchlist.map((w) => (
            <li key={w.id} className="flex items-center justify-between gap-4 py-3">
              <div>
                <a href={`/company/${w.company_id}`} className="hover:underline">
                  {w.company_name || `Company #${w.company_id}`}
                </a>
                {w.note && (
                  <p className="text-sm text-[var(--muted)]">{w.note}</p>
                )}
              </div>
              <button
                type="button"
                className="border border-[var(--border)] px-2 py-1 text-sm"
                onClick={async () => {
                  const token = await getToken();
                  await removeWatchlist(token, w.id);
                  await load();
                }}
              >
                Remove
              </button>
            </li>
          ))}
          {watchlist.length === 0 && (
            <li className="py-4 text-[var(--muted)]">Watchlist is empty.</li>
          )}
        </ul>

        <form
          onSubmit={addCompany}
          className="grid gap-3 border border-[var(--border)] p-4 sm:grid-cols-2"
        >
          <label className="grid gap-1 text-sm sm:col-span-1">
            <span>Company name</span>
            <input
              required
              value={coName}
              onChange={(e) => setCoName(e.target.value)}
              placeholder="Acme AI"
              className="border border-[var(--border)] bg-transparent px-3 py-2"
            />
          </label>
          <label className="grid gap-1 text-sm">
            <span>Website (optional)</span>
            <input
              value={coDomain}
              onChange={(e) => setCoDomain(e.target.value)}
              placeholder="acme.ai"
              className="border border-[var(--border)] bg-transparent px-3 py-2"
            />
          </label>
          <label className="grid gap-1 text-sm sm:col-span-2">
            <span>Note (optional)</span>
            <input
              value={coNote}
              onChange={(e) => setCoNote(e.target.value)}
              placeholder="Warm intro via…"
              className="border border-[var(--border)] bg-transparent px-3 py-2"
            />
          </label>
          <button
            type="submit"
            className="w-fit border border-[var(--border)] bg-[var(--panel)] px-4 py-2 text-sm"
          >
            Add to watchlist
          </button>
        </form>
      </section>

      {/* ── Priorities ────────────────────────────────────────── */}
      <section id="priorities" className="space-y-5">
        <div>
          <h2 className="text-xl">What matters more to me</h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Adjust how My Queue ranks companies for you. The firm score stays
            shared; this only changes your personal view.
          </p>
        </div>

        <div className="space-y-6 border border-[var(--border)] p-4">
          {PRIORITIES.map((p) => (
            <label key={p.key} className="grid gap-2">
              <div className="flex items-baseline justify-between gap-4">
                <div>
                  <div className="font-medium">{p.label}</div>
                  <div className="text-sm text-[var(--muted)]">{p.help}</div>
                </div>
                <span className="shrink-0 text-sm tabular-nums text-[var(--muted)]">
                  {(priorities[p.key] ?? 0) > 0
                    ? `+${priorities[p.key]}`
                    : priorities[p.key] ?? 0}
                </span>
              </div>
              <input
                type="range"
                min={-2}
                max={2}
                step={1}
                value={priorities[p.key] ?? 0}
                onChange={(e) =>
                  setPriorities((prev) => ({
                    ...prev,
                    [p.key]: Number(e.target.value),
                  }))
                }
              />
              <div className="flex justify-between text-xs text-[var(--muted)]">
                <span>Less</span>
                <span>Default</span>
                <span>More</span>
              </div>
            </label>
          ))}
          <button
            type="button"
            onClick={savePriorities}
            className="border border-[var(--border)] bg-[var(--panel)] px-4 py-2 text-sm"
          >
            Save priorities
          </button>
        </div>
      </section>
    </div>
  );
}

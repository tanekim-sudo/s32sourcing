"use client";

import { useEffect, useMemo, useState } from "react";
import {
  fetchBaseRubrics,
  fetchOverlay,
  saveOverlay,
  type RubricBase,
  type RubricOverlay,
} from "@/lib/api";
import { useApiToken } from "@/hooks/useApiToken";

const BASE_DIMS = [
  "founder_quality",
  "market_timing_fit",
  "vc_attention",
  "traction_signal",
  "network_proximity",
];

export default function MyRubricPage() {
  const { getToken, isLoaded, isSignedIn } = useApiToken();
  const [overlay, setOverlay] = useState<RubricOverlay | null>(null);
  const [bases, setBases] = useState<RubricBase[]>([]);
  const [adjustments, setAdjustments] = useState<Record<string, number>>({});
  const [customName, setCustomName] = useState("");
  const [customWeight, setCustomWeight] = useState(0.1);
  const [customReuse, setCustomReuse] = useState("founder_quality");
  const [added, setAdded] = useState<Array<Record<string, unknown>>>([]);
  const [saved, setSaved] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const activeBase = useMemo(
    () => bases.find((b) => b.is_active) || bases[0],
    [bases]
  );

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    (async () => {
      try {
        const token = await getToken();
        const [o, b] = await Promise.all([
          fetchOverlay(token),
          fetchBaseRubrics(token),
        ]);
        setOverlay(o);
        setBases(b);
        setAdjustments(o?.weight_adjustments || {});
        setAdded(o?.added_dimensions || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load");
      }
    })();
  }, [getToken, isLoaded, isSignedIn]);

  const onSave = async () => {
    const token = await getToken();
    const row = await saveOverlay(token, {
      version: String((Number(overlay?.version) || 0) + 1),
      base_rubric_version: activeBase?.version || "1.0.0",
      weight_adjustments: adjustments,
      added_dimensions: added,
    });
    setOverlay(row);
    setSaved(`Saved overlay v${row.version}`);
  };

  const addDimension = () => {
    if (!customName.trim()) return;
    setAdded((prev) => [
      ...prev,
      {
        name: customName.trim(),
        weight: customWeight,
        reuse_base_dimension: customReuse,
        signals: [],
      },
    ]);
    setCustomName("");
  };

  return (
    <div className="space-y-10">
      <div>
        <h1 className="text-3xl tracking-tight">My Rubric</h1>
        <p className="mt-2 max-w-xl text-[var(--muted)]">
          Adjust weights on top of the firm base rubric. Overlay re-ranking is
          arithmetic on read — no extra LLM cost in the common case.
        </p>
      </div>

      {error && (
        <pre className="overflow-x-auto border border-[var(--border)] bg-[var(--panel)] p-4 text-xs">
          {error}
        </pre>
      )}

      <section className="space-y-3">
        <h2 className="text-xl">Firm base (read-only)</h2>
        <p className="text-sm text-[var(--muted)]">
          Active version: {activeBase?.version || "—"}
          {activeBase?.changelog ? ` — ${activeBase.changelog}` : ""}
        </p>
        {activeBase && (
          <pre className="max-h-64 overflow-auto border border-[var(--border)] bg-[var(--panel)] p-4 text-xs">
            {activeBase.yaml_content}
          </pre>
        )}
      </section>

      <section className="space-y-4">
        <h2 className="text-xl">Weight adjustments (deltas)</h2>
        <p className="text-sm text-[var(--muted)]">
          Example: +0.10 on founder_quality. Negative weights (e.g. vc_attention)
          are supported generically.
        </p>
        <div className="space-y-3">
          {BASE_DIMS.map((dim) => (
            <label key={dim} className="grid grid-cols-[1fr_120px] items-center gap-4">
              <span>{dim.replace(/_/g, " ")}</span>
              <input
                type="number"
                step="0.05"
                value={adjustments[dim] ?? 0}
                onChange={(e) =>
                  setAdjustments((prev) => ({
                    ...prev,
                    [dim]: Number(e.target.value),
                  }))
                }
                className="border border-[var(--border)] bg-transparent px-3 py-2 text-sm tabular-nums"
              />
            </label>
          ))}
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl">Custom dimensions</h2>
        <ul className="divide-y divide-[var(--border)] border-y border-[var(--border)]">
          {added.map((d, i) => (
            <li key={i} className="flex justify-between py-2 text-sm">
              <span>
                {String(d.name)} (w={String(d.weight)}, reuse{" "}
                {String(d.reuse_base_dimension)})
              </span>
              <button
                type="button"
                onClick={() => setAdded((prev) => prev.filter((_, j) => j !== i))}
                className="border border-[var(--border)] px-2 py-0.5"
              >
                Remove
              </button>
            </li>
          ))}
          {added.length === 0 && (
            <li className="py-3 text-[var(--muted)]">None yet.</li>
          )}
        </ul>
        <div className="grid gap-3 sm:grid-cols-4">
          <input
            value={customName}
            onChange={(e) => setCustomName(e.target.value)}
            placeholder="Dimension name"
            className="border border-[var(--border)] bg-transparent px-3 py-2 text-sm"
          />
          <input
            type="number"
            step="0.05"
            value={customWeight}
            onChange={(e) => setCustomWeight(Number(e.target.value))}
            className="border border-[var(--border)] bg-transparent px-3 py-2 text-sm"
          />
          <select
            value={customReuse}
            onChange={(e) => setCustomReuse(e.target.value)}
            className="border border-[var(--border)] bg-transparent px-3 py-2 text-sm"
          >
            {BASE_DIMS.map((d) => (
              <option key={d} value={d}>
                reuse {d}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={addDimension}
            className="border border-[var(--border)] bg-[var(--panel)] px-3 py-2 text-sm"
          >
            Add dimension
          </button>
        </div>
      </section>

      <div className="flex items-center gap-4">
        <button
          type="button"
          onClick={onSave}
          className="border border-[var(--border)] bg-[var(--panel)] px-4 py-2 text-sm"
        >
          Save overlay
        </button>
        {saved && <span className="text-sm text-[var(--accent)]">{saved}</span>}
      </div>
    </div>
  );
}

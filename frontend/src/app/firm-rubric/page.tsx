"use client";

import { useEffect, useState } from "react";
import {
  createBaseRubric,
  fetchBaseRubrics,
  type RubricBase,
} from "@/lib/api";
import { useApiToken } from "@/hooks/useApiToken";

export default function FirmRubricPage() {
  const { getToken, isLoaded, isSignedIn } = useApiToken();
  const [rows, setRows] = useState<RubricBase[]>([]);
  const [version, setVersion] = useState("");
  const [yaml, setYaml] = useState("");
  const [changelog, setChangelog] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const load = async () => {
    const token = await getToken();
    const data = await fetchBaseRubrics(token);
    setRows(data);
    const active = data.find((r) => r.is_active) || data[0];
    if (active && !yaml) {
      setYaml(active.yaml_content);
      setVersion(active.version);
    }
  };

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    load().catch((err) =>
      setError(err instanceof Error ? err.message : "Failed to load")
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoaded, isSignedIn]);

  const onSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setMsg(null);
    setError(null);
    try {
      const token = await getToken();
      await createBaseRubric(token, {
        version,
        yaml_content: yaml,
        changelog,
        activate: true,
      });
      setMsg(`Activated rubric v${version}`);
      await load();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Save failed (admin role required)"
      );
    }
  };

  return (
    <div className="space-y-10">
      <div>
        <h1 className="text-3xl tracking-tight">Firm Rubric</h1>
        <p className="mt-2 max-w-xl text-[var(--muted)]">
          Admin-only writes. Version history is visible to all partners. Scoring
          uses the active version once per company.
        </p>
      </div>

      {error && (
        <pre className="overflow-x-auto border border-[var(--border)] bg-[var(--panel)] p-4 text-xs">
          {error}
        </pre>
      )}

      <section>
        <h2 className="text-xl">Version history</h2>
        <ul className="mt-4 divide-y divide-[var(--border)] border-y border-[var(--border)]">
          {rows.map((r) => (
            <li key={`${r.id}-${r.version}`} className="py-3 text-sm">
              <span className="font-medium">v{r.version}</span>
              {r.is_active && (
                <span className="ml-2 text-[var(--accent)]">active</span>
              )}
              {r.changelog && (
                <span className="text-[var(--muted)]"> — {r.changelog}</span>
              )}
            </li>
          ))}
        </ul>
      </section>

      <form onSubmit={onSave} className="space-y-3 border border-[var(--border)] p-4">
        <h2 className="text-xl">Publish new version</h2>
        <input
          required
          value={version}
          onChange={(e) => setVersion(e.target.value)}
          placeholder="Version e.g. 1.1.0"
          className="w-full border border-[var(--border)] bg-transparent px-3 py-2 text-sm"
        />
        <input
          value={changelog}
          onChange={(e) => setChangelog(e.target.value)}
          placeholder="Changelog"
          className="w-full border border-[var(--border)] bg-transparent px-3 py-2 text-sm"
        />
        <textarea
          required
          value={yaml}
          onChange={(e) => setYaml(e.target.value)}
          rows={18}
          className="w-full border border-[var(--border)] bg-transparent px-3 py-2 font-mono text-xs"
        />
        <button
          type="submit"
          className="border border-[var(--border)] bg-[var(--panel)] px-4 py-2 text-sm"
        >
          Activate version
        </button>
        {msg && <p className="text-sm text-[var(--accent)]">{msg}</p>}
      </form>
    </div>
  );
}

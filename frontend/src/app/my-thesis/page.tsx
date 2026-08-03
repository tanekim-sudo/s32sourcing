"use client";

import { useEffect, useState } from "react";
import {
  createCompany,
  createThesis,
  deleteThesis,
  fetchMyThesis,
  fetchSharedThesis,
  fetchWatchlist,
  removeWatchlist,
  updateThesis,
  type ThesisConfig,
  type WatchlistEntry,
} from "@/lib/api";
import { useApiToken } from "@/hooks/useApiToken";

function linesToList(text: string): string[] {
  return text
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);
}

export default function MyThesisPage() {
  const { getToken, isLoaded, isSignedIn } = useApiToken();
  const [mine, setMine] = useState<ThesisConfig[]>([]);
  const [shared, setShared] = useState<ThesisConfig[]>([]);
  const [watchlist, setWatchlist] = useState<WatchlistEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [keywords, setKeywords] = useState("");
  const [exa, setExa] = useState("");
  const [github, setGithub] = useState("");

  const [coName, setCoName] = useState("");
  const [coDomain, setCoDomain] = useState("");

  const load = async () => {
    const token = await getToken();
    const [t, s, w] = await Promise.all([
      fetchMyThesis(token),
      fetchSharedThesis(token),
      fetchWatchlist(token),
    ]);
    setMine(t);
    setShared(s);
    setWatchlist(w);
  };

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    load().catch((err) =>
      setError(err instanceof Error ? err.message : "Failed to load")
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoaded, isSignedIn]);

  const onCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = await getToken();
    await createThesis(token, {
      name,
      keywords: linesToList(keywords),
      exa_queries: linesToList(exa),
      github_topics: linesToList(github),
      is_active: true,
      is_shared: false,
    });
    setName("");
    setKeywords("");
    setExa("");
    setGithub("");
    await load();
  };

  const onToggleActive = async (t: ThesisConfig) => {
    const token = await getToken();
    await updateThesis(token, t.id, { is_active: !t.is_active });
    await load();
  };

  const onDelete = async (id: number) => {
    const token = await getToken();
    await deleteThesis(token, id);
    await load();
  };

  const onAddCompany = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = await getToken();
    const company = await createCompany(token, {
      name: coName,
      domain: coDomain || undefined,
    });
    // createCompany scores; add to watchlist via separate call after create
    const { addWatchlist } = await import("@/lib/api");
    await addWatchlist(token, { company_id: company.id });
    setCoName("");
    setCoDomain("");
    await load();
  };

  return (
    <div className="space-y-12">
      <div>
        <h1 className="text-3xl tracking-tight">My Thesis & Watchlist</h1>
        <p className="mt-2 max-w-xl text-[var(--muted)]">
          Your thesis areas feed the shared search union. Watchlist companies
          always appear in My Queue.
        </p>
      </div>

      {error && (
        <pre className="overflow-x-auto border border-[var(--border)] bg-[var(--panel)] p-4 text-xs">
          {error}
        </pre>
      )}

      <section className="space-y-4">
        <h2 className="text-xl">My thesis configs</h2>
        <ul className="divide-y divide-[var(--border)] border-y border-[var(--border)]">
          {mine.map((t) => (
            <li key={t.id} className="flex items-start justify-between gap-4 py-3">
              <div>
                <div className="font-medium">
                  {t.name}{" "}
                  {!t.is_active && (
                    <span className="text-sm text-[var(--muted)]">(paused)</span>
                  )}
                </div>
                <p className="mt-1 text-sm text-[var(--muted)]">
                  keywords: {(t.keywords || []).join(", ") || "—"}
                </p>
              </div>
              <div className="flex gap-2 text-sm">
                <button
                  type="button"
                  onClick={() => onToggleActive(t)}
                  className="border border-[var(--border)] px-2 py-1"
                >
                  {t.is_active ? "Pause" : "Resume"}
                </button>
                <button
                  type="button"
                  onClick={() => onDelete(t.id)}
                  className="border border-[var(--border)] px-2 py-1"
                >
                  Delete
                </button>
              </div>
            </li>
          ))}
          {mine.length === 0 && (
            <li className="py-4 text-[var(--muted)]">No personal thesis yet.</li>
          )}
        </ul>

        <form onSubmit={onCreate} className="grid gap-3 border border-[var(--border)] p-4">
          <h3 className="font-medium">Add thesis</h3>
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Name"
            className="border border-[var(--border)] bg-transparent px-3 py-2 text-sm"
          />
          <textarea
            value={keywords}
            onChange={(e) => setKeywords(e.target.value)}
            placeholder="Keywords (one per line)"
            rows={3}
            className="border border-[var(--border)] bg-transparent px-3 py-2 text-sm"
          />
          <textarea
            value={exa}
            onChange={(e) => setExa(e.target.value)}
            placeholder="Exa queries (one per line)"
            rows={2}
            className="border border-[var(--border)] bg-transparent px-3 py-2 text-sm"
          />
          <textarea
            value={github}
            onChange={(e) => setGithub(e.target.value)}
            placeholder="GitHub topics (one per line)"
            rows={2}
            className="border border-[var(--border)] bg-transparent px-3 py-2 text-sm"
          />
          <button
            type="submit"
            className="w-fit border border-[var(--border)] bg-[var(--panel)] px-4 py-2 text-sm"
          >
            Create
          </button>
        </form>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl">Firm-wide / shared thesis</h2>
        <ul className="divide-y divide-[var(--border)] border-y border-[var(--border)]">
          {shared.map((t) => (
            <li key={t.id} className="py-3">
              <div className="font-medium">{t.name}</div>
              <p className="mt-1 text-sm text-[var(--muted)]">
                {(t.keywords || []).join(", ") || "—"}
              </p>
            </li>
          ))}
          {shared.length === 0 && (
            <li className="py-4 text-[var(--muted)]">No shared thesis configs.</li>
          )}
        </ul>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl">Watchlist</h2>
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
                onClick={async () => {
                  const token = await getToken();
                  await removeWatchlist(token, w.id);
                  await load();
                }}
                className="border border-[var(--border)] px-2 py-1 text-sm"
              >
                Remove
              </button>
            </li>
          ))}
          {watchlist.length === 0 && (
            <li className="py-4 text-[var(--muted)]">Watchlist is empty.</li>
          )}
        </ul>

        <form onSubmit={onAddCompany} className="grid gap-3 border border-[var(--border)] p-4 sm:grid-cols-3">
          <input
            required
            value={coName}
            onChange={(e) => setCoName(e.target.value)}
            placeholder="Company name"
            className="border border-[var(--border)] bg-transparent px-3 py-2 text-sm sm:col-span-1"
          />
          <input
            value={coDomain}
            onChange={(e) => setCoDomain(e.target.value)}
            placeholder="domain.com"
            className="border border-[var(--border)] bg-transparent px-3 py-2 text-sm"
          />
          <button
            type="submit"
            className="border border-[var(--border)] bg-[var(--panel)] px-4 py-2 text-sm"
          >
            Add & watch
          </button>
        </form>
      </section>
    </div>
  );
}

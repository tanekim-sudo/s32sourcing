"use client";

import Link from "next/link";
import type { QueueCompany } from "@/lib/api";

export function QueueList({
  items,
  emptyText,
  showOverlay,
}: {
  items: QueueCompany[];
  emptyText: string;
  showOverlay?: boolean;
}) {
  if (items.length === 0) {
    return (
      <div className="border border-dashed border-[var(--border)] px-6 py-12 text-[var(--muted)]">
        {emptyText}
      </div>
    );
  }

  return (
    <ul className="divide-y divide-[var(--border)] border-y border-[var(--border)]">
      {items.map((item) => (
        <li
          key={item.company_id}
          className="flex items-start justify-between gap-6 py-4"
        >
          <div>
            <Link
              href={`/company/${item.company_id}`}
              className="text-lg hover:underline"
            >
              {item.name}
            </Link>
            {item.domain && (
              <p className="text-sm text-[var(--muted)]">{item.domain}</p>
            )}
            {item.why_note && (
              <p className="mt-2 max-w-2xl text-sm text-[var(--muted)]">
                {item.why_note}
              </p>
            )}
            {item.on_my_watchlist && (
              <p className="mt-1 text-xs text-[var(--accent)]">On your watchlist</p>
            )}
          </div>
          <div className="shrink-0 text-right text-sm tabular-nums">
            {showOverlay && (
              <div>
                <span className="text-[var(--muted)]">You </span>
                {item.overlay_score?.toFixed(1) ?? "—"}
              </div>
            )}
            <div className={showOverlay ? "text-[var(--muted)]" : ""}>
              {showOverlay ? "Base " : ""}
              {item.base_score?.toFixed(1) ?? "—"}
            </div>
          </div>
        </li>
      ))}
    </ul>
  );
}

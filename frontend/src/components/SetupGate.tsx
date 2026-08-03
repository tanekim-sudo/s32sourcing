import Link from "next/link";

export function SetupGate({ title }: { title: string }) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl tracking-tight">{title}</h1>
        <p className="mt-2 max-w-xl text-[var(--muted)]">
          Nothing shows here until you choose what to track.
        </p>
      </div>
      <div className="border border-dashed border-[var(--border)] px-6 py-12">
        <p className="text-[var(--muted)]">
          Add at least one tracking area or watchlist company in Settings.
        </p>
        <Link
          href="/settings"
          className="mt-4 inline-block border border-[var(--border)] bg-[var(--panel)] px-4 py-2 text-sm"
        >
          Go to Settings
        </Link>
      </div>
    </div>
  );
}

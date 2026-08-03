"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/", label: "My Queue" },
  { href: "/queue", label: "Team Queue" },
  { href: "/my-thesis", label: "My Thesis" },
  { href: "/my-rubric", label: "My Rubric" },
  { href: "/firm-rubric", label: "Firm Rubric" },
];

const clerkConfigured = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);

function AuthControls() {
  if (!clerkConfigured) {
    return (
      <span className="text-xs text-[var(--muted)]">Dev mode (no Clerk)</span>
    );
  }
  // Lazy require so builds without ClerkProvider stay clean
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { UserButton } = require("@clerk/nextjs");
  return <UserButton />;
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const hideNav =
    pathname?.startsWith("/sign-in") || pathname?.startsWith("/sign-up");

  if (hideNav) {
    return <>{children}</>;
  }

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--fg)]">
      <header className="border-b border-[var(--border)]">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-6 px-6 py-4">
          <div className="flex items-baseline gap-6">
            <Link href="/" className="text-lg tracking-tight">
              S32 <span className="text-[var(--muted)]">Sourcing</span>
            </Link>
            <nav className="hidden items-center gap-4 text-sm sm:flex">
              {NAV.map((item) => {
                const active =
                  item.href === "/"
                    ? pathname === "/"
                    : pathname?.startsWith(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={
                      active
                        ? "text-[var(--fg)]"
                        : "text-[var(--muted)] hover:text-[var(--fg)]"
                    }
                  >
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </div>
          <AuthControls />
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-10">{children}</main>
    </div>
  );
}

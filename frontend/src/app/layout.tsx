import type { Metadata } from "next";
import { Source_Serif_4, IBM_Plex_Sans } from "next/font/google";
import { AppShell } from "@/components/AppShell";
import { ClerkProviderWrapper } from "@/components/ClerkProviderWrapper";
import "./globals.css";

const display = Source_Serif_4({
  variable: "--font-display",
  subsets: ["latin"],
});

const sans = IBM_Plex_Sans({
  variable: "--font-sans",
  weight: ["400", "500", "600"],
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "S32 Sourcing",
  description: "Shared sourcing pipeline with partner-scoped queues and rubric overlays.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProviderWrapper>
      <html lang="en">
        <body className={`${display.variable} ${sans.variable} antialiased`}>
          <AppShell>{children}</AppShell>
        </body>
      </html>
    </ClerkProviderWrapper>
  );
}

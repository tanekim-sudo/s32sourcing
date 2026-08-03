import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Standalone only for Docker image builds — not for Vercel.
  ...(process.env.NEXT_OUTPUT_STANDALONE === "1"
    ? ({ output: "standalone" } as const)
    : {}),
  poweredByHeader: false,
  // Keep tooling rooted at the Next app (Vercel Root Directory = frontend)
  turbopack: {
    root: process.cwd(),
  },
};

export default nextConfig;

"use client";

/**
 * Select the auth hook implementation at module load time so only one
 * set of React hooks runs (Rules of Hooks). Without a Clerk publishable
 * key we use the dev bypass path.
 */
import { useApiToken as useDevToken } from "./useApiToken.dev";

const clerkConfigured = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);

let useApiTokenImpl = useDevToken;

if (clerkConfigured) {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  useApiTokenImpl = require("./useApiToken.clerk").useApiToken;
}

export const useApiToken = useApiTokenImpl;

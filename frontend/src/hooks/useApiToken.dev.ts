"use client";

import { useCallback } from "react";

/** Local scaffold without Clerk — backend AUTH_DEV_BYPASS handles identity. */
export function useApiToken() {
  const getToken = useCallback(async () => null as string | null, []);
  return { getToken, isLoaded: true, isSignedIn: true };
}

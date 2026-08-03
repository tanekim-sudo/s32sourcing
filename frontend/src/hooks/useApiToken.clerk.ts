"use client";

import { useAuth } from "@clerk/nextjs";
import { useCallback } from "react";

export function useApiToken() {
  const { getToken, isLoaded, isSignedIn } = useAuth();

  const tokenFn = useCallback(async () => {
    if (!isSignedIn) return null;
    return getToken();
  }, [getToken, isSignedIn]);

  return { getToken: tokenFn, isLoaded, isSignedIn: Boolean(isSignedIn) };
}

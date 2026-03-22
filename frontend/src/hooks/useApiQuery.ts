"use client";

import { useEffect, useRef, useState } from "react";

function extractErrorMessage(err: unknown): string {
  if (err instanceof Error) return err.message;
  return "An unexpected error occurred.";
}

export interface UseApiQueryOptions {
  /** When false, the fetch is skipped and the hook stays in loading state. Defaults to true. */
  enabled?: boolean;
}

export interface UseApiQueryResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

/**
 * Fetches data on mount and when `deps` change.
 * Returns typed `{ data, loading, error }`.
 *
 * The fetcher is stored in a ref so it does not need to be stable.
 * Only `deps` (and `options.enabled`) control when a re-fetch happens.
 */
export function useApiQuery<T>(
  fetcher: () => Promise<T>,
  deps: unknown[],
  options: UseApiQueryOptions = {},
): UseApiQueryResult<T> {
  const enabled = options.enabled ?? true;
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  useEffect(() => {
    if (!enabled) return;

    let cancelled = false;
    setData(null);
    setError(null);
    setLoading(true);

    fetcherRef
      .current()
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(extractErrorMessage(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, enabled]);

  return { data, loading, error };
}

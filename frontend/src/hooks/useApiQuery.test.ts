import { describe, it, expect, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useApiQuery } from "./useApiQuery";

describe("useApiQuery", () => {
  it("starts in loading state", () => {
    const fetcher = vi.fn().mockReturnValue(new Promise(() => {})); // never resolves
    const { result } = renderHook(() => useApiQuery(fetcher, []));

    expect(result.current.loading).toBe(true);
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it("transitions to data on success", async () => {
    const fetcher = vi.fn().mockResolvedValue({ items: [1, 2, 3] });
    const { result } = renderHook(() => useApiQuery(fetcher, []));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toEqual({ items: [1, 2, 3] });
    expect(result.current.error).toBeNull();
  });

  it("transitions to error on failure", async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error("Network down"));
    const { result } = renderHook(() => useApiQuery(fetcher, []));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toBeNull();
    expect(result.current.error).toBe("Network down");
  });

  it("extracts message from non-Error rejections", async () => {
    const fetcher = vi.fn().mockRejectedValue("string error");
    const { result } = renderHook(() => useApiQuery(fetcher, []));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBe("An unexpected error occurred.");
  });

  it("re-fetches when deps change", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce({ v: 1 })
      .mockResolvedValueOnce({ v: 2 });

    let dep = "a";
    const { result, rerender } = renderHook(() =>
      useApiQuery(fetcher, [dep]),
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    expect(result.current.data).toEqual({ v: 1 });

    dep = "b";
    rerender();

    await waitFor(() => {
      expect(result.current.data).toEqual({ v: 2 });
    });

    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it("does not fetch when enabled is false", async () => {
    const fetcher = vi.fn().mockResolvedValue({ ok: true });
    const { result } = renderHook(() =>
      useApiQuery(fetcher, [], { enabled: false }),
    );

    // Flush microtasks
    await new Promise((r) => setTimeout(r, 20));

    expect(fetcher).not.toHaveBeenCalled();
    expect(result.current.loading).toBe(true);
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it("fetches when enabled transitions from false to true", async () => {
    const fetcher = vi.fn().mockResolvedValue({ items: [1] });

    let enabled = false;
    const { result, rerender } = renderHook(() =>
      useApiQuery(fetcher, [], { enabled }),
    );

    // Not called while disabled
    await new Promise((r) => setTimeout(r, 20));
    expect(fetcher).not.toHaveBeenCalled();
    expect(result.current.loading).toBe(true);

    // Enable and re-render
    enabled = true;
    rerender();

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(result.current.data).toEqual({ items: [1] });
  });

  it("does not update state after unmount", async () => {
    let resolvePromise: (v: { done: boolean }) => void;
    const fetcher = vi.fn().mockReturnValue(
      new Promise<{ done: boolean }>((resolve) => {
        resolvePromise = resolve;
      }),
    );

    const { result, unmount } = renderHook(() =>
      useApiQuery<{ done: boolean }>(fetcher, []),
    );

    // Capture state before unmount
    expect(result.current.loading).toBe(true);
    expect(result.current.data).toBeNull();

    unmount();
    resolvePromise!({ done: true });

    // Flush microtasks so the .then callback fires
    await new Promise((r) => setTimeout(r, 20));

    // State should remain at loading=true, data=null because the
    // cancelled flag prevented setData/setLoading from being called
    expect(result.current.data).toBeNull();
    expect(result.current.loading).toBe(true);
  });
});

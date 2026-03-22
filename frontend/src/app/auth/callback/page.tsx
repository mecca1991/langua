"use client";

import { Suspense } from "react";
import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { sanitizeReturnTo } from "@/lib/auth-routing";
import { supabase } from "@/lib/supabase";

function getHashParams(hash: string) {
  const params = new URLSearchParams(hash.startsWith("#") ? hash.slice(1) : hash);
  return {
    accessToken: params.get("access_token"),
    refreshToken: params.get("refresh_token"),
  };
}

function AuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    let cancelled = false;

    async function completeAuth() {
      const returnTo = sanitizeReturnTo(searchParams.get("returnTo"));
      const code = searchParams.get("code");

      try {
        if (code) {
          const { error } = await supabase.auth.exchangeCodeForSession(code);
          if (error) throw error;
        } else {
          const { accessToken, refreshToken } = getHashParams(
            window.location.hash,
          );
          if (accessToken && refreshToken) {
            const { error } = await supabase.auth.setSession({
              access_token: accessToken,
              refresh_token: refreshToken,
            });
            if (error) throw error;
          } else {
            throw new Error("Missing authentication parameters");
          }
        }

        if (!cancelled) {
          router.replace(returnTo);
        }
      } catch {
        if (!cancelled) {
          const failUrl = new URL("/sign-in", window.location.origin);
          failUrl.searchParams.set("error", "auth_callback_failed");
          if (returnTo !== "/") failUrl.searchParams.set("returnTo", returnTo);
          router.replace(failUrl.pathname + failUrl.search);
        }
      }
    }

    void completeAuth();

    return () => {
      cancelled = true;
    };
  }, [router, searchParams]);

  return (
    <main className="flex min-h-screen items-center justify-center p-8">
      <p className="text-gray-500">Completing sign-in...</p>
    </main>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <main className="flex min-h-screen items-center justify-center p-8">
          <p className="text-gray-500">Completing sign-in...</p>
        </main>
      }
    >
      <AuthCallbackContent />
    </Suspense>
  );
}

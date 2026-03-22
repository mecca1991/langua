"use client";

import { Suspense } from "react";
import { useAuth } from "@/hooks/useAuth";
import { sanitizeReturnTo } from "@/lib/auth-routing";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect } from "react";

function SignInContent() {
  const { user, loading, signInWithGoogle, signInWithGithub } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const authError = searchParams.get("error");
  const returnTo = sanitizeReturnTo(searchParams.get("returnTo"));

  useEffect(() => {
    if (!loading && user) {
      router.replace(returnTo);
    }
  }, [user, loading, router, returnTo]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-gray-500">Loading...</p>
      </div>
    );
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 p-8">
      <h1 className="text-4xl font-bold">Langua</h1>
      <p className="text-lg text-gray-600">Sign in to start learning</p>
      {authError ? (
        <p className="rounded-md bg-red-50 px-4 py-2 text-sm text-red-700">
          Sign-in could not be completed. Please try again.
        </p>
      ) : null}
      <div className="flex flex-col gap-3">
        <button
          onClick={() => signInWithGoogle(returnTo)}
          className="rounded-lg bg-white px-6 py-3 text-sm font-medium text-gray-700 shadow-md ring-1 ring-gray-200 hover:bg-gray-50"
        >
          Continue with Google
        </button>
        <button
          onClick={() => signInWithGithub(returnTo)}
          className="rounded-lg bg-gray-900 px-6 py-3 text-sm font-medium text-white shadow-md hover:bg-gray-800"
        >
          Continue with GitHub
        </button>
      </div>
    </main>
  );
}

export default function SignIn() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <p className="text-gray-500">Loading...</p>
        </div>
      }
    >
      <SignInContent />
    </Suspense>
  );
}

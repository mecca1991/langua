"use client";

import { useAuth } from "@/hooks/useAuth";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function SignIn() {
  const { user, loading, signInWithGoogle, signInWithGithub } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user) {
      router.replace("/");
    }
  }, [user, loading, router]);

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
      <div className="flex flex-col gap-3">
        <button
          onClick={signInWithGoogle}
          className="rounded-lg bg-white px-6 py-3 text-sm font-medium text-gray-700 shadow-md ring-1 ring-gray-200 hover:bg-gray-50"
        >
          Continue with Google
        </button>
        <button
          onClick={signInWithGithub}
          className="rounded-lg bg-gray-900 px-6 py-3 text-sm font-medium text-white shadow-md hover:bg-gray-800"
        >
          Continue with GitHub
        </button>
      </div>
    </main>
  );
}

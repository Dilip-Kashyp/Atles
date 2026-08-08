"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { ROUTES, STORAGE_KEYS } from "@/constants";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    if (typeof window !== "undefined") {
      const hash = window.location.hash;
      if (hash && (hash.includes("access_token=") || hash.includes("token="))) {
        const tokenMatch = hash.match(/(?:access_token|token)=([^&]+)/);
        if (tokenMatch && tokenMatch[1]) {
          const token = tokenMatch[1];
          localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, token);
          document.cookie = `${STORAGE_KEYS.ACCESS_TOKEN}=${token}; path=/; max-age=31536000; SameSite=Lax`;
          router.replace(ROUTES.DASHBOARD);
          return;
        }
      }

      const existingToken = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
      if (existingToken) {
        router.replace(ROUTES.DASHBOARD);
      } else {
        router.replace(ROUTES.LOGIN);
      }
    }
  }, [router]);

  return (
    <div className="min-h-screen bg-[#080b14] flex items-center justify-center">
      <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
    </div>
  );
}

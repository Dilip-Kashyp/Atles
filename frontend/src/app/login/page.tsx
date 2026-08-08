"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CONSTANTS, ROUTES, STORAGE_KEYS } from "@/constants";
import {
  Button,
  Card,
  GitHubIcon,
  GoogleIcon,
  SlackIcon,
  SparklesIcon,
  Stack,
  Typography,
} from "@/components";

export default function LoginPage() {
  const router = useRouter();
  const [loadingProvider, setLoadingProvider] = useState<string | null>(null);

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
      }
    }
  }, [router]);

  const handleOAuthLogin = (provider: string) => {
    setLoadingProvider(provider);
    window.location.href = `${CONSTANTS.BASE_URL}/auth/${provider}/login`;
  };

  const features = [
    "Modular Monolith Enterprise Identity Architecture",
    "Unified Request Context & Granular RBAC Permissions",
    "M2M Service Accounts & Bound API Key Automation",
    "Enterprise Multi-Tenancy (Organizations & Workspaces)",
  ];

  return (
    <div className="min-h-screen bg-[#080b14] flex items-center justify-center p-4 relative overflow-hidden">
      {/* Glow Backdrops */}
      <div className="absolute w-[450px] h-[450px] rounded-full bg-blue-600/10 blur-[120px] top-[-10%] right-[15%] pointer-events-none" />
      <div className="absolute w-[400px] h-[400px] rounded-full bg-indigo-600/10 blur-[120px] bottom-[-10%] left-[15%] pointer-events-none" />

      <div className="w-full max-w-md z-10">
        <Card className="!p-8 border-white/10 shadow-2xl backdrop-blur-2xl bg-slate-950/60">
          <Stack gap={6} align="center">
            {/* Header Icon */}
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center shadow-xl shadow-blue-500/25">
              <SparklesIcon className="w-7 h-7 text-white" />
            </div>

            <div className="text-center space-y-1">
              <Typography variant="h1" className="!text-2xl">
                Welcome to Atlas
              </Typography>
              <Typography variant="subtitle">
                Conversation Intelligence & Identity Platform
              </Typography>
            </div>

            {/* Login Options */}
            <div className="w-full space-y-3">
              <Button
                variant="secondary"
                size="lg"
                className="w-full !bg-white !text-slate-950 hover:!bg-slate-100 font-bold"
                startIcon={<GoogleIcon />}
                loading={loadingProvider === "google"}
                onClick={() => handleOAuthLogin("google")}
              >
                Continue with Google
              </Button>

              <Button
                variant="secondary"
                size="lg"
                className="w-full !bg-[#161b22] !text-white border-white/10 hover:!bg-[#21262d] font-bold"
                startIcon={<GitHubIcon />}
                loading={loadingProvider === "github"}
                onClick={() => handleOAuthLogin("github")}
              >
                Continue with GitHub
              </Button>

              <Button
                variant="secondary"
                size="lg"
                className="w-full !bg-[#1b1d21] !text-white border-white/10 hover:!bg-[#282b30] font-bold"
                startIcon={<SlackIcon />}
                loading={loadingProvider === "slack"}
                onClick={() => handleOAuthLogin("slack")}
              >
                Continue with Slack
              </Button>
            </div>

            <div className="w-full h-px bg-white/10" />

            {/* Features list */}
            <Stack gap={2.5} className="w-full">
              {features.map((feat, i) => (
                <div key={i} className="flex items-center gap-2.5">
                  <SparklesIcon className="w-4 h-4 text-blue-400 shrink-0" />
                  <Typography variant="body2">{feat}</Typography>
                </div>
              ))}
            </Stack>
          </Stack>
        </Card>
      </div>
    </div>
  );
}

"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ROUTES } from "@/constants";
import {
  BotIcon,
  Card,
  Chip,
  RefreshIcon,
  SparklesIcon,
  Stack,
  Typography,
  UsersIcon,
  Button,
} from "@/components";
import {
  CurrentIdentity,
  fetchCurrentIdentity,
} from "@/services/api";

export default function DashboardPage() {
  const router = useRouter();
  const [identity, setIdentity] = useState<CurrentIdentity | null>(null);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    setLoading(true);
    try {
      const idRes = await fetchCurrentIdentity();
      setIdentity(idRes);
    } catch (err) {
      console.error(err);
      router.push(ROUTES.LOGIN);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#080b14] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <Typography variant="subtitle">Resolving Identity Context...</Typography>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#080b14] pl-28 pr-8 py-8">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <Typography variant="h1">Atlas Intelligence Dashboard</Typography>
            <Typography variant="subtitle">
              Enterprise Identity & Operations Platform
            </Typography>
          </div>

          <Button
            variant="secondary"
            size="sm"
            startIcon={<RefreshIcon className="w-4 h-4" />}
            onClick={loadData}
          >
            Refresh Context
          </Button>
        </div>

        {/* Identity Context Banner */}
        <Card className="!bg-gradient-to-r from-blue-950/40 via-indigo-950/30 to-slate-950/60 border-blue-500/30">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-2xl bg-blue-600/20 border border-blue-500/40 flex items-center justify-center shrink-0">
                {identity?.service_account ? (
                  <BotIcon className="w-7 h-7 text-blue-400" />
                ) : (
                  <SparklesIcon className="w-7 h-7 text-blue-400" />
                )}
              </div>
              <div>
                <div className="flex items-center gap-2.5">
                  <Typography variant="h2">
                    {identity?.user?.display_name ||
                      identity?.service_account?.name ||
                      identity?.user?.email ||
                      "Anonymous Actor"}
                  </Typography>
                  <Chip
                    label={identity?.auth_type || "Anonymous"}
                    variant={identity?.auth_type === "jwt" ? "success" : "info"}
                    size="sm"
                  />
                </div>
                <Typography variant="body2" className="mt-1">
                  {identity?.user?.email || "Service Account Automation Identity"}
                </Typography>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="text-right hidden md:block">
                <Typography variant="caption">Correlation ID</Typography>
                <div className="font-mono text-xs text-blue-300">
                  {identity?.correlation_id?.substring(0, 18)}...
                </div>
              </div>
            </div>
          </div>
        </Card>

        {/* Metric Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <Stack gap={2}>
              <div className="flex items-center justify-between">
                <Typography variant="caption">Total Users</Typography>
                <UsersIcon className="w-5 h-5 text-blue-400" />
              </div>
              <Typography variant="h2">1,245</Typography>
              <Typography variant="body2">Active Across System</Typography>
            </Stack>
          </Card>
        </div>

      </div>
    </div>
  );
}

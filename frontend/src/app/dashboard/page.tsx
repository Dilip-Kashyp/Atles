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
  SlackIcon,
  GitHubIcon,
  GoogleIcon,
} from "@/components";
import {
  CurrentIdentity,
  fetchCurrentIdentity,
  fetchMyIntegrations,
  fetchAllIntegrationUsers,
  ConnectedIntegration,
} from "@/services/api";

export default function DashboardPage() {
  const router = useRouter();
  const [identity, setIdentity] = useState<CurrentIdentity | null>(null);
  const [totalUsers, setTotalUsers] = useState<number>(0);
  const [totalApps, setTotalApps] = useState<number>(0);
  const [integrations, setIntegrations] = useState<ConnectedIntegration[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    setLoading(true);
    try {
      const [idRes, usersRes, appsRes] = await Promise.all([
        fetchCurrentIdentity(),
        fetchAllIntegrationUsers(),
        fetchMyIntegrations()
      ]);
      setIdentity(idRes);
      setTotalUsers(usersRes.length);
      setTotalApps(appsRes.length);
      setIntegrations(appsRes);
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

  const getProviderIcon = (provider: string) => {
    if (provider.toLowerCase() === "slack") return <SlackIcon className="w-6 h-6" />;
    if (provider.toLowerCase() === "github") return <GitHubIcon className="w-6 h-6" />;
    if (provider.toLowerCase() === "google") return <GoogleIcon className="w-6 h-6" />;
    return <SparklesIcon className="w-6 h-6 text-purple-400" />;
  };

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
              <Typography variant="h2">{totalUsers.toLocaleString()}</Typography>
              <Typography variant="body2">Active Across System</Typography>
            </Stack>
          </Card>

          <Card>
            <Stack gap={2}>
              <div className="flex items-center justify-between">
                <Typography variant="caption">Connected Apps</Typography>
                <SparklesIcon className="w-5 h-5 text-purple-400" />
              </div>
              <Typography variant="h2">{totalApps.toLocaleString()}</Typography>
              <Typography variant="body2">Active Integrations</Typography>
            </Stack>
          </Card>
        </div>

        {/* Integration Status List */}
        <div className="space-y-4">
          <Typography variant="h3">Integration Status</Typography>
          {integrations.length === 0 ? (
            <Card className="flex items-center justify-center py-10">
              <Typography variant="body2" className="text-slate-400">
                No integrations connected. Go to the Integrations tab to connect apps.
              </Typography>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {integrations.map((integration) => (
                <Card key={integration.id} className="hover:border-white/20 transition-colors">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center">
                        {getProviderIcon(integration.provider_type)}
                      </div>
                      <div>
                        <Typography variant="body1" className="capitalize font-medium">
                          {integration.provider_type}
                        </Typography>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="w-2 h-2 rounded-full bg-green-500" />
                          <Typography variant="caption" className="text-green-400">
                            {integration.status}
                          </Typography>
                        </div>
                      </div>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>

      </div>
    </div>
  );
}

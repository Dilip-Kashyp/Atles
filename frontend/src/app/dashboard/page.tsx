"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ActivityIcon,
  BotIcon,
  BuildingIcon,
  Card,
  Chip,
  ClockIcon,
  CopyIcon,
  FolderIcon,
  KeyIcon,
  RefreshIcon,
  ShieldIcon,
  SparklesIcon,
  Stack,
  TerminalIcon,
  Typography,
  UsersIcon,
  Button,
} from "@/components";
import {
  CurrentIdentity,
  Workspace,
  fetchCurrentIdentity,
  fetchWorkspaces,
  switchWorkspace,
} from "@/services/api";

export default function DashboardPage() {
  const router = useRouter();
  const [identity, setIdentity] = useState<CurrentIdentity | null>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [switching, setSwitching] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [idRes, wsRes] = await Promise.all([
        fetchCurrentIdentity(),
        fetchWorkspaces(),
      ]);
      setIdentity(idRes);
      setWorkspaces(wsRes);
      if (wsRes.length > 0 && !localStorage.getItem("atlas_workspace_id")) {
        localStorage.setItem("atlas_workspace_id", wsRes[0].id);
      }
    } catch (err) {
      console.error(err);
      router.push("/login");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleWorkspaceSwitch = async (wsId: string) => {
    setSwitching(true);
    try {
      await switchWorkspace(wsId);
      await loadData();
    } catch (err) {
      console.error(err);
    } finally {
      setSwitching(false);
    }
  };

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

  const activeWs = identity?.workspace || (workspaces.length > 0 ? workspaces[0] : null);

  return (
    <div className="min-h-screen bg-[#080b14] pl-28 pr-8 py-8">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <Typography variant="h1">Atlas Intelligence Dashboard</Typography>
            <Typography variant="subtitle">
              Enterprise Identity & Multi-Tenant Operations Platform
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
                <Typography variant="caption">Active Workspace</Typography>
                <FolderIcon className="w-5 h-5 text-blue-400" />
              </div>
              <Typography variant="h2">{activeWs?.name || "None"}</Typography>
              <Chip label={activeWs?.status || "Active"} variant="success" size="sm" />
            </Stack>
          </Card>

          <Card>
            <Stack gap={2}>
              <div className="flex items-center justify-between">
                <Typography variant="caption">Total Workspaces</Typography>
                <BuildingIcon className="w-5 h-5 text-indigo-400" />
              </div>
              <Typography variant="h2">{workspaces.length}</Typography>
              <Typography variant="body2">Available in Org</Typography>
            </Stack>
          </Card>

          <Card>
            <Stack gap={2}>
              <div className="flex items-center justify-between">
                <Typography variant="caption">Permissions</Typography>
                <ShieldIcon className="w-5 h-5 text-emerald-400" />
              </div>
              <Typography variant="h2">{identity?.permissions?.length || 0}</Typography>
              <Typography variant="body2">Assigned via RBAC</Typography>
            </Stack>
          </Card>

          <Card>
            <Stack gap={2}>
              <div className="flex items-center justify-between">
                <Typography variant="caption">Auth Mode</Typography>
                <KeyIcon className="w-5 h-5 text-amber-400" />
              </div>
              <Typography variant="h2">{identity?.auth_type?.toUpperCase()}</Typography>
              <Typography variant="body2">Secured Token Handoff</Typography>
            </Stack>
          </Card>
        </div>

        {/* Workspace Switcher */}
        <Card>
          <Stack gap={4}>
            <div className="flex items-center justify-between">
              <div>
                <Typography variant="h3">Switch Active Workspace</Typography>
                <Typography variant="subtitle">
                  Operational isolation boundary for conversations & automation
                </Typography>
              </div>
              <Button variant="outline" size="sm" onClick={() => router.push("/workspaces")}>
                Manage Workspaces
              </Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {workspaces.map((ws) => {
                const isActive = activeWs?.id === ws.id;
                return (
                  <div
                    key={ws.id}
                    onClick={() => !isActive && handleWorkspaceSwitch(ws.id)}
                    className={`p-4 rounded-xl border transition-all cursor-pointer ${
                      isActive
                        ? "bg-blue-600/15 border-blue-500/50 shadow-lg shadow-blue-500/10"
                        : "bg-white/5 border-white/10 hover:border-white/20 hover:bg-white/10"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <Typography variant="h4">{ws.name}</Typography>
                      {isActive && <Chip label="Current" variant="success" size="sm" />}
                    </div>
                    <Typography variant="body2" className="font-mono">
                      {ws.slug}
                    </Typography>
                  </div>
                );
              })}
            </div>
          </Stack>
        </Card>

        {/* Quick Links */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card
            className="cursor-pointer hover:border-blue-500/40"
            onClick={() => router.push("/workspaces")}
          >
            <Stack gap={3}>
              <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center text-blue-400">
                <ShieldIcon className="w-5 h-5" />
              </div>
              <div>
                <Typography variant="h4">Workspace Security Policies</Typography>
                <Typography variant="body2" className="mt-1">
                  Configure MFA enforcement, guest access rules, data retention periods, and allowed integrations.
                </Typography>
              </div>
            </Stack>
          </Card>

          <Card
            className="cursor-pointer hover:border-indigo-500/40"
            onClick={() => router.push("/service-accounts")}
          >
            <Stack gap={3}>
              <div className="w-10 h-10 rounded-xl bg-indigo-500/10 flex items-center justify-center text-indigo-400">
                <BotIcon className="w-5 h-5" />
              </div>
              <div>
                <Typography variant="h4">M2M Service Accounts & Keys</Typography>
                <Typography variant="body2" className="mt-1">
                  Provision bot service accounts and generate scoped API keys (`atls_...`) for automated pipelines.
                </Typography>
              </div>
            </Stack>
          </Card>

          <Card
            className="cursor-pointer hover:border-emerald-500/40"
            onClick={() => router.push("/profile")}
          >
            <Stack gap={3}>
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center text-emerald-400">
                <UsersIcon className="w-5 h-5" />
              </div>
              <div>
                <Typography variant="h4">OAuth Account Linking & Sessions</Typography>
                <Typography variant="body2" className="mt-1">
                  Link/Unlink Google & GitHub accounts, execute account merges, and manage active device sessions.
                </Typography>
              </div>
            </Stack>
          </Card>
        </div>
      </div>
    </div>
  );
}

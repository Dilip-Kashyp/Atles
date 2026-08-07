"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Button,
  Card,
  Chip,
  FolderIcon,
  Input,
  PlusIcon,
  Select,
  ShieldIcon,
  SlidersIcon,
  SparklesIcon,
  Stack,
  Typography,
} from "@/components";
import {
  Workspace,
  WorkspaceConfiguration,
  WorkspacePolicy,
  createWorkspace,
  fetchCurrentWorkspace,
  fetchWorkspaceConfig,
  fetchWorkspacePolicies,
  fetchWorkspaces,
  updateWorkspaceConfig,
  updateWorkspacePolicies,
} from "@/services/api";

export default function WorkspacesPage() {
  const router = useRouter();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [currentWs, setCurrentWs] = useState<Workspace | null>(null);
  const [policy, setPolicy] = useState<WorkspacePolicy | null>(null);
  const [config, setConfig] = useState<WorkspaceConfiguration | null>(null);
  const [loading, setLoading] = useState(true);
  const [savingPolicy, setSavingPolicy] = useState(false);

  const [newWsName, setNewWsName] = useState("");
  const [creating, setCreating] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [allWs, active] = await Promise.all([
        fetchWorkspaces(),
        fetchCurrentWorkspace(),
      ]);
      setWorkspaces(allWs);
      setCurrentWs(active);

      if (active) {
        const [polRes, cfgRes] = await Promise.all([
          fetchWorkspacePolicies(active.id),
          fetchWorkspaceConfig(active.id),
        ]);
        setPolicy(polRes);
        setConfig(cfgRes);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateWorkspace = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWsName.trim()) return;
    setCreating(true);
    try {
      await createWorkspace(newWsName.trim());
      setNewWsName("");
      await loadData();
    } catch (err) {
      console.error(err);
    } finally {
      setCreating(false);
    }
  };

  const handleSavePolicy = async () => {
    if (!currentWs || !policy) return;
    setSavingPolicy(true);
    try {
      const updated = await updateWorkspacePolicies(currentWs.id, {
        require_mfa: policy.require_mfa,
        allow_guests: policy.allow_guests,
        retention_days: policy.retention_days,
        default_ai_provider: policy.default_ai_provider,
      });
      setPolicy(updated);
      window.dispatchEvent(
        new CustomEvent("atlas-notification", {
          detail: { message: "Workspace security policies updated successfully!", type: "success" },
        })
      );
    } catch (err) {
      console.error(err);
    } finally {
      setSavingPolicy(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#080b14] flex items-center justify-center">
        <Typography variant="subtitle">Loading Workspaces & Security Policies...</Typography>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#080b14] pl-28 pr-8 py-8">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <Typography variant="h1">Workspaces & Governance</Typography>
            <Typography variant="subtitle">
              Manage multi-tenant operational boundaries and enterprise security rules
            </Typography>
          </div>
        </div>

        {/* Create New Workspace */}
        <Card>
          <form onSubmit={handleCreateWorkspace} className="flex flex-col md:flex-row items-end gap-4">
            <div className="flex-1">
              <Input
                label="Create New Workspace"
                placeholder="e.g., Core Engineering, Security Ops"
                value={newWsName}
                onChange={(e) => setNewWsName(e.target.value)}
                startIcon={<FolderIcon className="w-4 h-4" />}
              />
            </div>
            <Button
              type="submit"
              loading={creating}
              startIcon={<PlusIcon className="w-4 h-4" />}
            >
              Create Workspace
            </Button>
          </form>
        </Card>

        {/* Active Workspace List */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {workspaces.map((ws) => {
            const isActive = currentWs?.id === ws.id;
            return (
              <Card key={ws.id} className={isActive ? "!border-blue-500/50 bg-blue-600/10" : ""}>
                <Stack gap={3}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <FolderIcon className="w-5 h-5 text-blue-400" />
                      <Typography variant="h3">{ws.name}</Typography>
                    </div>
                    {isActive && <Chip label="Active Context" variant="success" size="sm" />}
                  </div>

                  <Typography variant="body2" className="font-mono text-xs">
                    Slug: {ws.slug}
                  </Typography>

                  <div className="flex items-center justify-between pt-2 border-t border-white/10 text-xs text-slate-400">
                    <span>Created: {new Date(ws.created_at).toLocaleDateString()}</span>
                    <span>Status: {ws.status}</span>
                  </div>
                </Stack>
              </Card>
            );
          })}
        </div>

        {/* Security Policies Management */}
        {currentWs && policy && (
          <Card>
            <Stack gap={6}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center text-emerald-400">
                    <ShieldIcon className="w-5 h-5" />
                  </div>
                  <div>
                    <Typography variant="h2">
                      Security Policies ({currentWs.name})
                    </Typography>
                    <Typography variant="subtitle">
                      Enterprise compliance controls enforced per workspace
                    </Typography>
                  </div>
                </div>

                <Button
                  variant="primary"
                  loading={savingPolicy}
                  onClick={handleSavePolicy}
                >
                  Save Policy Changes
                </Button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* MFA Toggle */}
                <div className="p-4 rounded-xl bg-white/5 border border-white/10 flex items-center justify-between">
                  <div>
                    <Typography variant="h4">Enforce Multi-Factor Auth (MFA)</Typography>
                    <Typography variant="body2">
                      Require all members to authenticate with MFA to access workspace
                    </Typography>
                  </div>
                  <input
                    type="checkbox"
                    className="w-5 h-5 accent-blue-600 rounded cursor-pointer"
                    checked={policy.require_mfa}
                    onChange={(e) => setPolicy({ ...policy, require_mfa: e.target.checked })}
                  />
                </div>

                {/* Guest Access Toggle */}
                <div className="p-4 rounded-xl bg-white/5 border border-white/10 flex items-center justify-between">
                  <div>
                    <Typography variant="h4">Allow Guest Invitations</Typography>
                    <Typography variant="body2">
                      Permit external guest users to join specific workspace threads
                    </Typography>
                  </div>
                  <input
                    type="checkbox"
                    className="w-5 h-5 accent-blue-600 rounded cursor-pointer"
                    checked={policy.allow_guests}
                    onChange={(e) => setPolicy({ ...policy, allow_guests: e.target.checked })}
                  />
                </div>

                {/* Retention Period */}
                <div className="p-4 rounded-xl bg-white/5 border border-white/10 space-y-2">
                  <Typography variant="h4">Data Retention Period (Days)</Typography>
                  <Input
                    type="number"
                    value={policy.retention_days}
                    onChange={(e) =>
                      setPolicy({ ...policy, retention_days: parseInt(e.target.value) || 365 })
                    }
                  />
                </div>

                {/* Default AI Provider */}
                <div className="p-4 rounded-xl bg-white/5 border border-white/10 space-y-2">
                  <Typography variant="h4">Default AI Provider</Typography>
                  <Select
                    options={[
                      { value: "gemini", label: "Google Gemini 1.5 Pro" },
                      { value: "openai", label: "OpenAI GPT-4o" },
                      { value: "anthropic", label: "Anthropic Claude 3.5 Sonnet" },
                    ]}
                    value={policy.default_ai_provider}
                    onChange={(e) => setPolicy({ ...policy, default_ai_provider: e.target.value })}
                  />
                </div>
              </div>
            </Stack>
          </Card>
        )}
      </div>
    </div>
  );
}

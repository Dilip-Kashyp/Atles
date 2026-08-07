"use client";

import React, { useEffect, useState } from "react";
import {
  ApiKey,
  ApiKeyCreateResponse,
  ServiceAccount,
  Workspace,
  createApiKey,
  createServiceAccount,
  deleteServiceAccount,
  fetchApiKeys,
  fetchCurrentWorkspace,
  fetchServiceAccounts,
  revokeApiKey,
} from "@/services/api";
import {
  BotIcon,
  Button,
  Card,
  Chip,
  CopyIcon,
  Input,
  KeyIcon,
  PlusIcon,
  Select,
  Stack,
  TrashIcon,
  Typography,
} from "@/components";

export default function ServiceAccountsPage() {
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [serviceAccounts, setServiceAccounts] = useState<ServiceAccount[]>([]);
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);

  // New SA Form State
  const [saName, setSaName] = useState("");
  const [saDesc, setSaDesc] = useState("");
  const [saRole, setSaRole] = useState("Developer");
  const [creatingSa, setCreatingSa] = useState(false);

  // New API Key Form State
  const [keyName, setKeyName] = useState("");
  const [targetSaId, setTargetSaId] = useState<string>("");
  const [creatingKey, setCreatingKey] = useState(false);
  const [rawKeyDisplay, setRawKeyDisplay] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const ws = await fetchCurrentWorkspace();
      setWorkspace(ws);
      if (ws) {
        const [saRes, keysRes] = await Promise.all([
          fetchServiceAccounts(ws.id),
          fetchApiKeys(ws.id),
        ]);
        setServiceAccounts(saRes);
        setApiKeys(keysRes);
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

  const handleCreateSa = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspace || !saName.trim()) return;
    setCreatingSa(true);
    try {
      await createServiceAccount(workspace.id, {
        name: saName.trim(),
        description: saDesc.trim() || undefined,
        role_name: saRole,
      });
      setSaName("");
      setSaDesc("");
      await loadData();
    } catch (err) {
      console.error(err);
    } finally {
      setCreatingSa(false);
    }
  };

  const handleDeleteSa = async (saId: string) => {
    if (!workspace) return;
    try {
      await deleteServiceAccount(workspace.id, saId);
      await loadData();
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreateApiKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspace || !keyName.trim()) return;
    setCreatingKey(true);
    try {
      const res: ApiKeyCreateResponse = await createApiKey(workspace.id, {
        name: keyName.trim(),
        service_account_id: targetSaId || undefined,
      });
      setRawKeyDisplay(res.raw_key);
      setKeyName("");
      await loadData();
    } catch (err) {
      console.error(err);
    } finally {
      setCreatingKey(false);
    }
  };

  const handleRevokeKey = async (keyId: string) => {
    if (!workspace) return;
    try {
      await revokeApiKey(workspace.id, keyId);
      await loadData();
    } catch (err) {
      console.error(err);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    window.dispatchEvent(
      new CustomEvent("atlas-notification", {
        detail: { message: "Copied API key to clipboard!", type: "success" },
      })
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#080b14] flex items-center justify-center">
        <Typography variant="subtitle">Loading Service Accounts & API Keys...</Typography>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#080b14] pl-28 pr-8 py-8">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Header */}
        <div>
          <Typography variant="h1">M2M Service Accounts & API Keys</Typography>
          <Typography variant="subtitle">
            Provision bot automation identities and workspace-bound access keys (`atls_...`)
          </Typography>
        </div>

        {/* Display newly created raw key */}
        {rawKeyDisplay && (
          <Card className="!bg-emerald-950/40 border-emerald-500/50">
            <Stack gap={3}>
              <div className="flex items-center justify-between">
                <Typography variant="h3" className="text-emerald-300">
                  API Key Created Successfully
                </Typography>
                <Button variant="ghost" size="sm" onClick={() => setRawKeyDisplay(null)}>
                  Dismiss
                </Button>
              </div>

              <Typography variant="body2" className="text-emerald-200">
                Please copy this raw API key now. You will not be able to view it again!
              </Typography>

              <div className="p-3 bg-black/60 rounded-xl font-mono text-sm text-emerald-400 flex items-center justify-between">
                <span>{rawKeyDisplay}</span>
                <Button
                  variant="secondary"
                  size="sm"
                  startIcon={<CopyIcon className="w-4 h-4" />}
                  onClick={() => copyToClipboard(rawKeyDisplay)}
                >
                  Copy Key
                </Button>
              </div>
            </Stack>
          </Card>
        )}

        {/* Create Service Account & Create API Key Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Create Service Account */}
          <Card>
            <form onSubmit={handleCreateSa} className="space-y-4">
              <div className="flex items-center gap-2">
                <BotIcon className="w-5 h-5 text-blue-400" />
                <Typography variant="h3">Provision Service Account</Typography>
              </div>

              <Input
                label="Bot / Pipeline Name"
                placeholder="e.g., GitHub Deployment Bot"
                value={saName}
                onChange={(e) => setSaName(e.target.value)}
              />

              <Input
                label="Description"
                placeholder="e.g., Handles automated production triggers"
                value={saDesc}
                onChange={(e) => setSaDesc(e.target.value)}
              />

              <Select
                label="Assigned Role"
                options={[
                  { value: "Developer", label: "Developer Role" },
                  { value: "Admin", label: "Admin Role" },
                  { value: "Viewer", label: "Viewer Role" },
                ]}
                value={saRole}
                onChange={(e) => setSaRole(e.target.value)}
              />

              <Button
                type="submit"
                loading={creatingSa}
                startIcon={<PlusIcon className="w-4 h-4" />}
                className="w-full"
              >
                Create Service Account
              </Button>
            </form>
          </Card>

          {/* Create API Key */}
          <Card>
            <form onSubmit={handleCreateApiKey} className="space-y-4">
              <div className="flex items-center gap-2">
                <KeyIcon className="w-5 h-5 text-indigo-400" />
                <Typography variant="h3">Generate Scoped API Key</Typography>
              </div>

              <Input
                label="API Key Label"
                placeholder="e.g., CI/CD Pipeline Secret Key"
                value={keyName}
                onChange={(e) => setKeyName(e.target.value)}
              />

              <Select
                label="Key Owner Identity"
                options={[
                  { value: "", label: "Bind to Current User Identity" },
                  ...serviceAccounts.map((sa) => ({
                    value: sa.id,
                    label: `Service Account: ${sa.name}`,
                  })),
                ]}
                value={targetSaId}
                onChange={(e) => setTargetSaId(e.target.value)}
              />

              <Button
                type="submit"
                variant="outline"
                loading={creatingKey}
                startIcon={<PlusIcon className="w-4 h-4" />}
                className="w-full"
              >
                Generate API Key
              </Button>
            </form>
          </Card>
        </div>

        {/* Service Accounts List */}
        <Card>
          <Stack gap={4}>
            <Typography variant="h2">Workspace Service Accounts</Typography>

            {serviceAccounts.length === 0 ? (
              <Typography variant="body2">No service accounts provisioned yet.</Typography>
            ) : (
              <div className="space-y-3">
                {serviceAccounts.map((sa) => (
                  <div
                    key={sa.id}
                    className="p-4 rounded-xl bg-white/5 border border-white/10 flex items-center justify-between"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center text-blue-400">
                        <BotIcon className="w-5 h-5" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <Typography variant="h4">{sa.name}</Typography>
                          <Chip label={sa.status} variant="success" size="sm" />
                        </div>
                        <Typography variant="body2">{sa.description || "No description"}</Typography>
                      </div>
                    </div>

                    <Button
                      variant="danger"
                      size="sm"
                      startIcon={<TrashIcon className="w-4 h-4" />}
                      onClick={() => handleDeleteSa(sa.id)}
                    >
                      Delete
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </Stack>
        </Card>

        {/* Active API Keys List */}
        <Card>
          <Stack gap={4}>
            <Typography variant="h2">Active API Keys</Typography>

            {apiKeys.length === 0 ? (
              <Typography variant="body2">No active API keys found for this workspace.</Typography>
            ) : (
              <div className="space-y-3">
                {apiKeys.map((key) => (
                  <div
                    key={key.id}
                    className="p-4 rounded-xl bg-white/5 border border-white/10 flex items-center justify-between"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-amber-500/10 flex items-center justify-center text-amber-400">
                        <KeyIcon className="w-5 h-5" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <Typography variant="h4">{key.name}</Typography>
                          <span className="font-mono text-xs text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20">
                            {key.key_prefix}_***
                          </span>
                        </div>
                        <Typography variant="body2">
                          Owner: {key.service_account_id ? "Service Account" : "User Identity"} | Created:{" "}
                          {new Date(key.created_at).toLocaleDateString()}
                        </Typography>
                      </div>
                    </div>

                    <Button
                      variant="danger"
                      size="sm"
                      startIcon={<TrashIcon className="w-4 h-4" />}
                      onClick={() => handleRevokeKey(key.id)}
                    >
                      Revoke Key
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </Stack>
        </Card>
      </div>
    </div>
  );
}

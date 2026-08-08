"use client";

import React, { useEffect, useState } from "react";
import {
  Button,
  Card,
  GitHubIcon,
  SlackIcon,
  Stack,
  Typography,
} from "@/components";
import {
  AvailableIntegration,
  ConnectedIntegration,
  fetchAvailableIntegrations,
  fetchMyIntegrations,
  disconnectIntegration,
  syncIntegrationUsers,
  fetchIntegrationUsers,
  IntegrationUser,
} from "@/services/api";
import { navigateAuthenticated } from "@/utils/apiClient";
import { EVENTS } from "@/constants";

export default function IntegrationsPage() {
  const [loading, setLoading] = useState(true);
  const [available, setAvailable] = useState<AvailableIntegration[]>([]);
  const [connected, setConnected] = useState<ConnectedIntegration[]>([]);
  const [integrationUsers, setIntegrationUsers] = useState<Record<string, IntegrationUser[]>>({});
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const loadData = async () => {
    try {
      const [avail, myIntegrations] = await Promise.all([
        fetchAvailableIntegrations(),
        fetchMyIntegrations(),
      ]);
      setAvailable(avail);
      setConnected(myIntegrations);

      // Load users for connected integrations
      const usersMap: Record<string, IntegrationUser[]> = {};
      await Promise.all(
        myIntegrations.map(async (integration) => {
          try {
            const users = await fetchIntegrationUsers(integration.id);
            usersMap[integration.id] = users;
          } catch (e) {
            console.error(`Failed to load users for integration ${integration.id}`, e);
          }
        })
      );
      setIntegrationUsers(usersMap);
    } catch (err: any) {
      console.error("Failed to load integrations", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSyncUsers = async (integrationId: string) => {
    setActionLoading(`sync-${integrationId}`);
    try {
      const result = await syncIntegrationUsers(integrationId);
      window.dispatchEvent(
        new CustomEvent(EVENTS.NOTIFICATION, {
          detail: { message: `Successfully synced ${result.synced_users} users.`, type: "success" },
        })
      );
      // Reload to get the latest users
      await loadData();
    } catch (err: any) {
      window.dispatchEvent(
        new CustomEvent(EVENTS.NOTIFICATION, {
          detail: { message: err.message || "Failed to sync users", type: "error" },
        })
      );
    } finally {
      setActionLoading(null);
    }
  };

  const handleConnect = (provider: string) => {
    navigateAuthenticated(`/integrations/me/${provider}/connect`);
  };

  const handleDisconnect = async (integrationId: string) => {
    setActionLoading(integrationId);
    try {
      await disconnectIntegration(integrationId);
      await loadData();
      window.dispatchEvent(
        new CustomEvent(EVENTS.NOTIFICATION, {
          detail: { message: "Integration disconnected successfully", type: "success" },
        })
      );
    } catch (err: any) {
      window.dispatchEvent(
        new CustomEvent(EVENTS.NOTIFICATION, {
          detail: { message: err.message || "Failed to disconnect", type: "error" },
        })
      );
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#080b14] flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const getIcon = (iconName: string) => {
    switch (iconName) {
      case "github":
        return <GitHubIcon />;
      case "slack":
        return <SlackIcon />;
      default:
        return null;
    }
  };

  const getDescription = (iconName: string) => {
    switch (iconName) {
      case "github":
        return "Connect GitHub to allow Atlas to read repositories, create issues, and manage PRs.";
      case "slack":
        return "Connect Slack to allow Atlas to send messages, read channels, and respond to mentions.";
      default:
        return "Connect this integration to enable more capabilities.";
    }
  };

  return (
    <div className="min-h-screen bg-[#080b14] pl-28 pr-8 py-8">
      <div className="max-w-4xl mx-auto space-y-8">
        <div>
          <Typography variant="h1">Integrations</Typography>
          <Typography variant="subtitle">
            Connect external services to allow Atlas agents to perform tasks on your behalf.
          </Typography>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {available.map((tool) => {
            // Find if this tool is connected by checking provider_type
            const connectedInstance = connected.find((c) => c.provider_type === tool.id);
            const isConnected = !!connectedInstance;

            return (
              <Card key={tool.id} className="hover:border-white/20 transition-all">
                <Stack gap={4}>
                  <div className="w-12 h-12 rounded-xl bg-slate-800 flex items-center justify-center">
                    {getIcon(tool.icon)}
                  </div>
                  <div>
                    <Typography variant="h3">{tool.name}</Typography>
                    <Typography variant="body2" className="mt-1">
                      {getDescription(tool.icon)}
                    </Typography>
                  </div>

                  {isConnected ? (
                    <Stack gap={2} className="mt-2">
                      <Button
                        variant="secondary"
                        className="w-full text-rose-400 hover:text-rose-300"
                        loading={actionLoading === connectedInstance.id}
                        onClick={() => handleDisconnect(connectedInstance.id)}
                      >
                        Disconnect {tool.name}
                      </Button>
                      
                      {tool.id === "slack" && (
                        <div className="pt-2 border-t border-white/10 mt-2">
                          <Stack direction="row" align="center" justify="between" className="mb-2">
                            <Typography variant="body2" className="text-slate-400">
                              Synced Users: {integrationUsers[connectedInstance.id]?.length || 0}
                            </Typography>
                            <Button
                              variant="secondary"
                              size="sm"
                              loading={actionLoading === `sync-${connectedInstance.id}`}
                              onClick={() => handleSyncUsers(connectedInstance.id)}
                            >
                              Sync Users
                            </Button>
                          </Stack>
                          {integrationUsers[connectedInstance.id] && integrationUsers[connectedInstance.id].length > 0 && (
                            <div className="max-h-40 overflow-y-auto space-y-1 bg-slate-900 rounded p-2 border border-white/5">
                              {integrationUsers[connectedInstance.id].map(u => (
                                <div key={u.id} className="flex items-center gap-2 text-sm text-slate-300">
                                  {u.avatar_url && (
                                    <img src={u.avatar_url} alt="avatar" className="w-5 h-5 rounded-full" />
                                  )}
                                  <span className="truncate">{u.name || u.username || u.provider_user_id}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </Stack>
                  ) : (
                    <Button
                      className="w-full mt-2"
                      onClick={() => handleConnect(tool.id)}
                    >
                      Connect {tool.name}
                    </Button>
                  )}
                </Stack>
              </Card>
            );
          })}
        </div>
      </div>
    </div>
  );
}

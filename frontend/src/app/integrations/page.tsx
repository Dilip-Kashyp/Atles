"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiClient, navigateAuthenticated } from "@/helper/apiClient";
import {
  Button,
  Card,
  GitHubIcon,
  SlackIcon,
  Stack,
  Typography,
} from "@/components";

interface Integration {
  id: string;
  provider_type: string;
  status: string;
}

export default function IntegrationsPage() {
  const router = useRouter();
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(true);
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);

  useEffect(() => {
    const wsId = localStorage.getItem("atlas_workspace_id");
    if (!wsId) {
      router.push("/dashboard");
      return;
    }
    setWorkspaceId(wsId);
    
    const fetchIntegrations = async () => {
      try {
        const data = await apiClient<Integration[]>({
          url: `/workspaces/${wsId}/integrations`,
        });
        setIntegrations(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchIntegrations();
  }, [router]);

  const handleConnect = (provider: string) => {
    if (!workspaceId) return;
    // Uses the new centralized helper to auto-append ?token=
    navigateAuthenticated(`/workspaces/${workspaceId}/integrations/${provider}/connect`);
  };

  const handleDisconnect = async (id: string) => {
    if (!workspaceId) return;
    try {
      await apiClient({
        url: `/workspaces/${workspaceId}/integrations/${id}`,
        method: "DELETE",
      });
      setIntegrations((prev) => prev.filter((i) => i.id !== id));
    } catch (err) {
      console.error(err);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#080b14] flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const isConnected = (provider: string) => integrations.find((i) => i.provider_type === provider);

  return (
    <div className="min-h-screen bg-[#080b14] pl-28 pr-8 py-8">
      <div className="max-w-4xl mx-auto space-y-8">
        <div>
          <Typography variant="h1">Workspace Integrations</Typography>
          <Typography variant="subtitle">
            Connect external services to allow Atlas agents to perform tasks on your behalf.
          </Typography>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* GitHub Card */}
          <Card className="hover:border-white/20 transition-all">
            <Stack gap={4}>
              <div className="w-12 h-12 rounded-xl bg-slate-800 flex items-center justify-center">
                <GitHubIcon />
              </div>
              <div>
                <Typography variant="h3">GitHub</Typography>
                <Typography variant="body2" className="mt-1">
                  Connect GitHub to allow Atlas to read repositories, create issues, and manage PRs.
                </Typography>
              </div>
              
              {isConnected("github") ? (
                <div className="flex items-center justify-between mt-2">
                  <span className="text-emerald-400 text-sm font-semibold">Connected</span>
                  <Button variant="outline" size="sm" onClick={() => handleDisconnect(isConnected("github")!.id)}>
                    Disconnect
                  </Button>
                </div>
              ) : (
                <Button className="w-full mt-2" onClick={() => handleConnect("github")}>
                  Connect GitHub
                </Button>
              )}
            </Stack>
          </Card>

          {/* Slack Card */}
          <Card className="hover:border-white/20 transition-all">
            <Stack gap={4}>
              <div className="w-12 h-12 rounded-xl bg-slate-800 flex items-center justify-center">
                <SlackIcon />
              </div>
              <div>
                <Typography variant="h3">Slack</Typography>
                <Typography variant="body2" className="mt-1">
                  Connect Slack to allow Atlas to send messages, read channels, and respond to mentions.
                </Typography>
              </div>
              
              {isConnected("slack") ? (
                <div className="flex items-center justify-between mt-2">
                  <span className="text-emerald-400 text-sm font-semibold">Connected</span>
                  <Button variant="outline" size="sm" onClick={() => handleDisconnect(isConnected("slack")!.id)}>
                    Disconnect
                  </Button>
                </div>
              ) : (
                <Button className="w-full mt-2" onClick={() => handleConnect("slack")}>
                  Connect Slack
                </Button>
              )}
            </Stack>
          </Card>
        </div>
      </div>
    </div>
  );
}

"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Button,
  Card,
  Chip,
  GitHubIcon,
  GlobeIcon,
  GoogleIcon,
  Input,
  LogoutIcon,
  ShieldIcon,
  SlackIcon,
  SparklesIcon,
  Stack,
  Typography,
  UsersIcon,
} from "@/components";
import {
  CurrentIdentity,
  UserProfile,
  fetchCurrentIdentity,
  fetchCurrentUser,
  mergeUserAccounts,
  unlinkOAuthProvider,
} from "@/services/api";

export default function ProfilePage() {
  const router = useRouter();
  const [identity, setIdentity] = useState<CurrentIdentity | null>(null);
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  const [secondaryUserId, setSecondaryUserId] = useState("");
  const [merging, setMerging] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [idRes, uRes] = await Promise.all([
        fetchCurrentIdentity(),
        fetchCurrentUser(),
      ]);
      setIdentity(idRes);
      setUser(uRes);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleLinkProvider = (provider: string) => {
    window.location.href = `http://localhost:8000/api/v1/auth/${provider}/login`;
  };

  const handleUnlinkProvider = async (provider: string) => {
    try {
      await unlinkOAuthProvider(provider);
      window.dispatchEvent(
        new CustomEvent("atlas-notification", {
          detail: { message: `Unlinked ${provider} account successfully`, type: "success" },
        })
      );
      await loadData();
    } catch (err) {
      console.error(err);
    }
  };

  const handleMergeAccounts = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!secondaryUserId.trim()) return;
    setMerging(true);
    try {
      await mergeUserAccounts(secondaryUserId.trim());
      setSecondaryUserId("");
      window.dispatchEvent(
        new CustomEvent("atlas-notification", {
          detail: { message: "Account merged successfully!", type: "success" },
        })
      );
      await loadData();
    } catch (err) {
      console.error(err);
    } finally {
      setMerging(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#080b14] flex items-center justify-center">
        <Typography variant="subtitle">Loading User Profile & Security Settings...</Typography>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#080b14] pl-28 pr-8 py-8">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Header */}
        <div>
          <Typography variant="h1">Security & Identity Governance</Typography>
          <Typography variant="subtitle">
            Manage multi-provider OAuth account linking, account merging, and session revocation
          </Typography>
        </div>

        {/* Profile Details */}
        <Card>
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-full bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white text-2xl font-bold border-2 border-white/20">
              {user?.display_name?.[0] || user?.email?.[0] || "U"}
            </div>
            <div className="space-y-1">
              <Typography variant="h2">{user?.display_name || "User Account"}</Typography>
              <Typography variant="subtitle">{user?.email}</Typography>
              <div className="flex items-center gap-2 pt-1">
                <Chip label={`Status: ${user?.status}`} variant="success" size="sm" />
                <Chip label={`Locale: ${user?.locale}`} variant="info" size="sm" />
                <Chip label={`Timezone: ${user?.timezone}`} variant="neutral" size="sm" />
              </div>
            </div>
          </div>
        </Card>

        {/* OAuth Provider Account Linking */}
        <Card>
          <Stack gap={4}>
            <div>
              <Typography variant="h2">Linked OAuth Login Providers</Typography>
              <Typography variant="subtitle">
                Link multiple identity assertion providers to your canonical Atlas account
              </Typography>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Google */}
              <div className="p-4 rounded-xl bg-white/5 border border-white/10 flex flex-col justify-between gap-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <GoogleIcon className="w-6 h-6" />
                    <Typography variant="h4">Google</Typography>
                  </div>
                  <Chip label="Supported" variant="success" size="sm" />
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full"
                    onClick={() => handleLinkProvider("google")}
                  >
                    Link Google
                  </Button>
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={() => handleUnlinkProvider("google")}
                  >
                    Unlink
                  </Button>
                </div>
              </div>

              {/* GitHub */}
              <div className="p-4 rounded-xl bg-white/5 border border-white/10 flex flex-col justify-between gap-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <GitHubIcon className="w-6 h-6" />
                    <Typography variant="h4">GitHub</Typography>
                  </div>
                  <Chip label="Supported" variant="success" size="sm" />
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full"
                    onClick={() => handleLinkProvider("github")}
                  >
                    Link GitHub
                  </Button>
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={() => handleUnlinkProvider("github")}
                  >
                    Unlink
                  </Button>
                </div>
              </div>

              {/* Slack */}
              <div className="p-4 rounded-xl bg-white/5 border border-white/10 flex flex-col justify-between gap-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <SlackIcon className="w-6 h-6" />
                    <Typography variant="h4">Slack</Typography>
                  </div>
                  <Chip label="Supported" variant="info" size="sm" />
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full"
                    onClick={() => handleLinkProvider("slack")}
                  >
                    Link Slack
                  </Button>
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={() => handleUnlinkProvider("slack")}
                  >
                    Unlink
                  </Button>
                </div>
              </div>
            </div>
          </Stack>
        </Card>

        {/* Multi-Account Merge Service */}
        <Card>
          <form onSubmit={handleMergeAccounts} className="space-y-4">
            <div>
              <Typography variant="h2">Account Merge Service</Typography>
              <Typography variant="subtitle">
                Merge a duplicate secondary account ID into your primary identity
              </Typography>
            </div>

            <div className="flex flex-col md:flex-row gap-4 items-end">
              <div className="flex-1">
                <Input
                  label="Secondary Account UUID"
                  placeholder="e.g., 8f8d3f07-e44c-4287-80a5-427f68b06a85"
                  value={secondaryUserId}
                  onChange={(e) => setSecondaryUserId(e.target.value)}
                />
              </div>
              <Button type="submit" loading={merging} variant="outline">
                Execute Merge
              </Button>
            </div>
          </form>
        </Card>
      </div>
    </div>
  );
}

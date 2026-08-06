"use client";

import { useCallback, useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000/api";
const FRONTEND_ORIGIN = process.env.NEXT_PUBLIC_FRONTEND_ORIGIN || "http://localhost:3000";

// ─── Types ────────────────────────────────────────────────────────────────────
interface Integration {
  id: string;
  provider_type: string;
  provider_variant: string;
  type: string;
  status: "CONNECTED" | "DISCONNECTED";
  connected_by: string;
}

interface Workspace {
  id: string;
  name: string;
  role: string;
}

interface Toast {
  message: string;
  type: "success" | "error";
}

interface LoginOption {
  id: string;
  label: string;
  description: string;
  icon: string;
  accent: string;
  href: string;
}

// ─── Provider Metadata ────────────────────────────────────────────────────────
const PROVIDERS = [
  {
    id: "github",
    name: "GitHub",
    description: "Create and manage GitHub Issues directly from Slack threads.",
    icon: "🐙",
    iconBg: "rgba(36,41,47,0.8)",
    accentColor: "#f0f6ff",
    capabilities: ["create_issue", "search_issues"],
    phase: 1,
  },
  {
    id: "slack",
    name: "Slack",
    description: "Receive summaries, notifications, and action items in Slack.",
    icon: "💬",
    iconBg: "rgba(78,26,103,0.6)",
    accentColor: "#e879f9",
    capabilities: ["send_message", "read_thread"],
    phase: 1,
  },
  {
    id: "jira",
    name: "Jira",
    description: "Auto-create Jira tickets from conversation summaries.",
    icon: "🎯",
    iconBg: "rgba(0,82,204,0.2)",
    accentColor: "#60a5fa",
    capabilities: ["create_issue", "update_issue"],
    phase: 2,
  },
  {
    id: "notion",
    name: "Notion",
    description: "Generate and update Notion pages from engineering discussions.",
    icon: "📄",
    iconBg: "rgba(255,255,255,0.06)",
    accentColor: "#f0f6ff",
    capabilities: ["create_page", "update_page"],
    phase: 2,
  },
];

// ─── Sub-Components ────────────────────────────────────────────────────────────

function Sidebar({
  activeSection,
  onNavigate,
}: {
  activeSection: string;
  onNavigate: (s: string) => void;
}) {
  const navItems = [
    { id: "integrations", label: "Integrations", icon: "🔌" },
    { id: "activity", label: "Activity", icon: "📊" },
    { id: "settings", label: "Settings", icon: "⚙️" },
  ];

  return (
    <aside className="sidebar">
      {/* Logo */}
      <div style={{ padding: "8px 14px 24px", borderBottom: "1px solid var(--border)", marginBottom: "16px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div style={{
            width: "34px", height: "34px", borderRadius: "10px",
            background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: "16px", fontWeight: "700", color: "white",
          }}>A</div>
          <div>
            <div style={{ fontSize: "15px", fontWeight: "700", color: "var(--text-primary)" }}>Atlas</div>
            <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>Conversation Intelligence</div>
          </div>
        </div>
      </div>

      {navItems.map((item) => (
        <div
          key={item.id}
          className={`sidebar-item ${activeSection === item.id ? "active" : ""}`}
          onClick={() => onNavigate(item.id)}
        >
          <span>{item.icon}</span>
          <span>{item.label}</span>
        </div>
      ))}

      {/* Bottom info */}
      <div style={{ marginTop: "auto", padding: "14px", borderTop: "1px solid var(--border)" }}>
        <div style={{ fontSize: "12px", color: "var(--text-muted)", lineHeight: 1.5 }}>
          Atlas Platform<br />
          <span style={{ color: "var(--accent-green)", fontSize: "11px" }}>● Online</span>
        </div>
      </div>
    </aside>
  );
}

function StatCard({ label, value, icon, color }: { label: string; value: string | number; icon: string; color: string }) {
  return (
    <div className="stat-card animate-fade-in-up">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ fontSize: "22px" }}>{icon}</span>
        <span style={{ fontSize: "22px", fontWeight: "700", color }}>{value}</span>
      </div>
      <div style={{ fontSize: "13px", color: "var(--text-secondary)", marginTop: "4px" }}>{label}</div>
    </div>
  );
}

function IntegrationCard({
  provider,
  integration,
  onConnect,
  onDisconnect,
}: {
  provider: typeof PROVIDERS[0];
  integration?: Integration;
  onConnect: (provider: string) => void;
  onDisconnect: (integrationId: string, providerName: string) => void;
}) {
  const isConnected = integration?.status === "CONNECTED";
  const isPhase2 = provider.phase === 2;

  return (
    <div
      className="glass-card animate-fade-in-up"
      style={{ padding: "24px", position: "relative", overflow: "hidden" }}
    >
      {/* Accent glow */}
      <div style={{
        position: "absolute", top: 0, right: 0,
        width: "80px", height: "80px",
        background: `radial-gradient(circle, ${provider.accentColor}18, transparent 70%)`,
        borderRadius: "50%", transform: "translate(20px, -20px)",
        pointerEvents: "none",
      }} />

      {/* Phase badge */}
      {isPhase2 && (
        <div style={{
          position: "absolute", top: "16px", right: "16px",
          background: "rgba(245, 158, 11, 0.12)",
          border: "1px solid rgba(245, 158, 11, 0.3)",
          color: "#f59e0b", fontSize: "11px", fontWeight: "600",
          padding: "3px 8px", borderRadius: "20px",
        }}>
          Phase 2
        </div>
      )}

      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", gap: "14px", marginBottom: "16px" }}>
        <div className="provider-icon" style={{ background: provider.iconBg, border: "1px solid var(--border)" }}>
          {provider.icon}
        </div>
        <div>
          <h3 style={{ fontSize: "16px", fontWeight: "600", color: "var(--text-primary)" }}>
            {provider.name}
          </h3>
          <span className={`status-badge-${isConnected ? "connected" : "disconnected"}`}
            style={{ fontSize: "11px", fontWeight: "600", padding: "2px 8px", borderRadius: "20px", display: "inline-block", marginTop: "4px" }}>
            {isConnected ? "● Connected" : "○ Not Connected"}
          </span>
        </div>
      </div>

      {/* Description */}
      <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: "1.6", marginBottom: "16px" }}>
        {provider.description}
      </p>

      {/* Capabilities */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginBottom: "20px" }}>
        {provider.capabilities.map((cap) => (
          <span key={cap} style={{
            background: "rgba(255,255,255,0.05)", border: "1px solid var(--border)",
            color: "var(--text-secondary)", fontSize: "11px", fontWeight: "500",
            padding: "3px 10px", borderRadius: "20px",
          }}>
            {cap.replace(/_/g, " ")}
          </span>
        ))}
      </div>

      {/* Meta (if connected) */}
      {isConnected && integration && (
        <div style={{
          background: "rgba(16, 185, 129, 0.06)", border: "1px solid rgba(16, 185, 129, 0.15)",
          borderRadius: "10px", padding: "12px 14px", marginBottom: "16px",
          fontSize: "12px", color: "var(--text-secondary)",
        }}>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span>Type</span>
            <span style={{ color: "var(--text-primary)" }}>{integration.type}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", marginTop: "6px" }}>
            <span>Connected by</span>
            <span style={{ color: "var(--text-primary)" }}>{integration.connected_by}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", marginTop: "6px" }}>
            <span>Variant</span>
            <span style={{ color: "var(--text-primary)" }}>{integration.provider_variant}</span>
          </div>
        </div>
      )}

      {/* Action */}
      <div style={{ display: "flex", gap: "10px" }}>
        {!isConnected ? (
          <button
            className="btn-primary"
            style={{ width: "100%", opacity: isPhase2 ? 0.5 : 1 }}
            disabled={isPhase2}
            onClick={() => !isPhase2 && onConnect(provider.id)}
          >
            {isPhase2 ? "Coming Soon" : `Connect ${provider.name}`}
          </button>
        ) : (
          <>
            <div style={{ flex: 1, display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ color: "var(--accent-green)", fontSize: "12px" }}>✓</span>
              <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Active & ready</span>
            </div>
            <button
              className="btn-danger"
              onClick={() => onDisconnect(integration!.id, provider.name)}
            >
              Disconnect
            </button>
          </>
        )}
      </div>
    </div>
  );
}

// ─── Login Screen ──────────────────────────────────────────────────────────────
function LoginScreen({ onLogin }: { onLogin: () => void }) {
  const loginOptions: LoginOption[] = [
    {
      id: "github",
      label: "Continue with GitHub",
      description: "Connect repositories and create issues from conversations.",
      icon: "🐙",
      accent: "#f0f6ff",
      href: `${API_BASE}/auth/github/login`,
    },
    {
      id: "google",
      label: "Continue with Google",
      description: "Sign in with your work account and keep access simple.",
      icon: "🔑",
      accent: "#e0f2fe",
      href: `${API_BASE}/auth/google/login`,
    },
    {
      id: "slack",
      label: "Continue with Slack",
      description: "Bring channel context and action items into Atlas instantly.",
      icon: "💬",
      accent: "#ede9fe",
      href: `${API_BASE}/auth/slack/login`,
    },
  ];

  return (
    <div style={{
      minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center",
      background: "radial-gradient(ellipse at 50% 0%, rgba(59,130,246,0.1) 0%, transparent 60%)",
      padding: "24px",
    }}>
      <div className="animate-fade-in-up" style={{ width: "100%", maxWidth: "520px", padding: "32px", borderRadius: "24px", background: "rgba(10, 15, 25, 0.72)", border: "1px solid var(--border)", boxShadow: "0 24px 80px rgba(0,0,0,0.35)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "20px" }}>
          <div style={{
            width: "48px", height: "48px", borderRadius: "16px",
            background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: "22px", fontWeight: "700", color: "white",
          }}>A</div>
          <div>
            <h1 style={{ fontSize: "24px", fontWeight: "700", margin: 0 }}>Atlas</h1>
            <p style={{ fontSize: "13px", color: "var(--text-muted)", margin: "2px 0 0" }}>Conversation intelligence for modern teams</p>
          </div>
        </div>

        <p style={{ fontSize: "15px", color: "var(--text-secondary)", lineHeight: "1.7", marginBottom: "24px" }}>
          Turn Slack threads, product discussions, and engineering context into decisions, action items, and connected work.
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginBottom: "18px" }}>
          {loginOptions.map((option) => (
            <button
              key={option.id}
              style={{
                width: "100%", padding: "14px 16px", borderRadius: "14px",
                background: "rgba(255,255,255,0.05)", border: "1px solid var(--border)",
                color: "var(--text-primary)", cursor: "pointer", transition: "all 0.2s",
                fontWeight: "600", textAlign: "left",
                display: "flex", alignItems: "center", justifyContent: "space-between",
              }}
              onClick={() => {
                window.location.href = option.href;
              }}
            >
              <span style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <span style={{ fontSize: "18px" }}>{option.icon}</span>
                <span>
                  <div>{option.label}</div>
                  <div style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: "500", marginTop: "2px" }}>{option.description}</div>
                </span>
              </span>
              <span style={{ color: "var(--accent-blue)", fontSize: "14px" }}>→</span>
            </button>
          ))}
        </div>

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px", marginTop: "10px" }}>
          <button
            style={{ background: "none", border: "none", color: "var(--text-muted)", fontSize: "13px", cursor: "pointer", textDecoration: "underline" }}
            onClick={onLogin}
          >
            Enter demo mode (dev only)
          </button>
          <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
            Secure sign-in • OAuth ready
          </span>
        </div>
      </div>
    </div>
  );
}

// ─── Main Dashboard ────────────────────────────────────────────────────────────
function Dashboard({
  token,
  onLogout,
}: {
  token: string;
  onLogout: () => void;
}) {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [activeWorkspace, setActiveWorkspace] = useState<Workspace | null>(null);
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeSection, setActiveSection] = useState("integrations");
  const [toast, setToast] = useState<Toast | null>(null);

  const showToast = useCallback((message: string, type: "success" | "error") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3500);
  }, []);

  const fetchWorkspaces = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/dashboard/workspaces`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Unauthorized");
      const data: Workspace[] = await res.json();
      setWorkspaces(data);
      if (data.length > 0) {
        setActiveWorkspace((current) => current ?? data[0]);
      }
    } catch {
      showToast("Could not load workspaces.", "error");
    }
  }, [showToast, token]);

  const fetchIntegrations = useCallback(async (workspaceId: string) => {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/dashboard/workspaces/${workspaceId}/integrations`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed");
      const data: Integration[] = await res.json();
      setIntegrations(data);
    } catch {
      showToast("Could not load integrations.", "error");
    } finally {
      setLoading(false);
    }
  }, [showToast, token]);

  useEffect(() => {
    let isActive = true;

    const load = async () => {
      await fetchWorkspaces();
      if (!isActive) return;
    };

    void load();

    return () => {
      isActive = false;
    };
  }, [fetchWorkspaces]);

  useEffect(() => {
    if (!activeWorkspace) {
      return;
    }

    let isActive = true;

    const load = async () => {
      await fetchIntegrations(activeWorkspace.id);
      if (!isActive) return;
    };

    void load();

    return () => {
      isActive = false;
    };
  }, [activeWorkspace, fetchIntegrations]);

  const handleConnect = (provider: string) => {
    if (!activeWorkspace) return;
    window.location.href = `${API_BASE}/integrations/${provider}/connect?workspace_id=${activeWorkspace.id}&token=${token}`;
  };

  const handleDisconnect = async (integrationId: string, providerName: string) => {
    if (!activeWorkspace || !confirm(`Disconnect ${providerName}? This cannot be undone.`)) return;
    try {
      const res = await fetch(
        `${API_BASE}/dashboard/workspaces/${activeWorkspace.id}/integrations/${integrationId}`,
        { method: "DELETE", headers: { Authorization: `Bearer ${token}` } }
      );
      if (!res.ok) throw new Error("Failed");
      showToast(`${providerName} disconnected successfully.`, "success");
      fetchIntegrations(activeWorkspace.id);
    } catch {
      showToast(`Failed to disconnect ${providerName}.`, "error");
    }
  };

  const connectedCount = integrations.filter((i) => i.status === "CONNECTED").length;

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar activeSection={activeSection} onNavigate={setActiveSection} />

      {/* Main Content */}
      <main style={{ marginLeft: "240px", flex: 1, padding: "32px", maxWidth: "calc(100vw - 240px)" }}>
        {/* Header */}
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          marginBottom: "32px",
        }}>
          <div>
            <h1 style={{ fontSize: "24px", fontWeight: "700", color: "var(--text-primary)" }}>
              Integration Center
            </h1>
            <p style={{ fontSize: "14px", color: "var(--text-secondary)", marginTop: "4px" }}>
              Connect your tools. Atlas will do the rest.
            </p>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            {/* Workspace switcher */}
            {workspaces.length > 0 && (
              <select
                value={activeWorkspace?.id || ""}
                onChange={(e) => {
                  const ws = workspaces.find((w) => w.id === e.target.value);
                  if (ws) setActiveWorkspace(ws);
                }}
                style={{
                  background: "var(--bg-card)", border: "1px solid var(--border)",
                  color: "var(--text-primary)", padding: "8px 14px", borderRadius: "10px",
                  fontSize: "13px", cursor: "pointer",
                }}
              >
                {workspaces.map((ws) => (
                  <option key={ws.id} value={ws.id}>{ws.name}</option>
                ))}
              </select>
            )}
            <button
              onClick={onLogout}
              style={{
                background: "rgba(255,255,255,0.05)", border: "1px solid var(--border)",
                color: "var(--text-secondary)", padding: "8px 16px", borderRadius: "10px",
                fontSize: "13px", cursor: "pointer",
              }}
            >
              Sign out
            </button>
          </div>
        </div>

        {/* Stats */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px", marginBottom: "32px" }}>
          <StatCard label="Connected Tools" value={connectedCount} icon="🔌" color="var(--accent-green)" />
          <StatCard label="Available Providers" value={PROVIDERS.length} icon="🧩" color="var(--accent-blue)" />
          <StatCard label="Active Workspace" value={activeWorkspace?.name || "—"} icon="🏢" color="var(--accent-purple)" />
        </div>

        {/* Section: Integrations */}
        {activeSection === "integrations" && (
          <>
            <div style={{ marginBottom: "20px" }}>
              <h2 style={{ fontSize: "16px", fontWeight: "600", color: "var(--text-primary)" }}>Phase 1 — Available Now</h2>
              <p style={{ fontSize: "13px", color: "var(--text-muted)", marginTop: "4px" }}>
                Connect these tools to start creating issues and tracking discussions from Slack.
              </p>
            </div>

            {loading ? (
              <div style={{ textAlign: "center", padding: "60px", color: "var(--text-muted)", fontSize: "14px" }}>
                Loading integrations...
              </div>
            ) : !activeWorkspace ? (
              <div className="glass-card" style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)" }}>
                <p style={{ fontSize: "32px", marginBottom: "12px" }}>🏢</p>
                <p>No workspace found. Sign in to create your organization.</p>
              </div>
            ) : (
              <div className="integration-grid">
                {PROVIDERS.map((provider, i) => (
                  <div key={provider.id} className={`delay-${(i + 1) * 100}`}>
                    <IntegrationCard
                      provider={provider}
                      integration={integrations.find(
                        (int) => int.provider_type === provider.id
                      )}
                      onConnect={handleConnect}
                      onDisconnect={handleDisconnect}
                    />
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {/* Section: Activity (Placeholder) */}
        {activeSection === "activity" && (
          <div className="glass-card animate-fade-in-up" style={{ padding: "40px", textAlign: "center" }}>
            <p style={{ fontSize: "36px", marginBottom: "16px" }}>📊</p>
            <h2 style={{ fontSize: "18px", fontWeight: "600", marginBottom: "8px" }}>Activity Log</h2>
            <p style={{ color: "var(--text-secondary)", fontSize: "14px" }}>
              Full activity analytics coming in Phase 3. This will display all conversations processed, issues created, and decisions extracted.
            </p>
          </div>
        )}

        {/* Section: Settings (Placeholder) */}
        {activeSection === "settings" && (
          <div className="glass-card animate-fade-in-up" style={{ padding: "40px", textAlign: "center" }}>
            <p style={{ fontSize: "36px", marginBottom: "16px" }}>⚙️</p>
            <h2 style={{ fontSize: "18px", fontWeight: "600", marginBottom: "8px" }}>Workspace Settings</h2>
            <p style={{ color: "var(--text-secondary)", fontSize: "14px" }}>
              Organization management, member invitations, RBAC configuration, and billing settings coming soon.
            </p>
          </div>
        )}
      </main>

      {/* Toast Notification */}
      {toast && (
        <div className={`toast toast-${toast.type}`}>
          {toast.type === "success" ? "✓" : "✕"}&nbsp;&nbsp;{toast.message}
        </div>
      )}
    </div>
  );
}

// ─── Root Page ─────────────────────────────────────────────────────────────────
export default function Home() {
  const [token, setToken] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const initializeAuth = () => {
      setMounted(true);
      const params = new URLSearchParams(window.location.search);
      const queryToken = params.get("access_token");
      if (queryToken) {
        localStorage.setItem("atlas_token", queryToken);
        setToken(queryToken);
        window.history.replaceState({}, "", "/");
      } else {
        const stored = localStorage.getItem("atlas_token");
        if (stored) setToken(stored);
      }
    };

    initializeAuth();
  }, []);

  const handleLogin = () => {
    // Dev demo mode — in production this would be the OAuth callback
    const demoToken = "demo_token_replace_with_real_jwt";
    localStorage.setItem("atlas_token", demoToken);
    setToken(demoToken);
  };

  const handleLogout = () => {
    localStorage.removeItem("atlas_token");
    setToken(null);
  };

  if (!mounted) return null;

  if (!token) return <LoginScreen onLogin={handleLogin} />;

  return <Dashboard token={token} onLogout={handleLogout} />;
}

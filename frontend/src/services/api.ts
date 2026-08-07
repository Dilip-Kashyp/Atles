import { apiClient } from "@/helper/apiClient";

export interface UserProfile {
  id: string;
  email: string;
  display_name?: string;
  avatar_url?: string;
  email_verified: boolean;
  status: string;
  locale: string;
  timezone: string;
  created_at: string;
}

export interface ServiceAccount {
  id: string;
  workspace_id: string;
  name: string;
  description?: string;
  role_id: string;
  status: string;
  created_at: string;
}

export interface CurrentIdentity {
  auth_type: string;
  request_id: string;
  correlation_id: string;
  user?: UserProfile;
  service_account?: ServiceAccount;
  workspace?: Workspace;
  permissions: string[];
}

export interface Workspace {
  id: string;
  org_id: string;
  name: string;
  slug: string;
  icon_url?: string;
  is_default: boolean;
  status: string;
  created_at: string;
}

export interface WorkspacePolicy {
  id: string;
  workspace_id: string;
  require_mfa: boolean;
  allow_guests: boolean;
  allowed_integrations: string[];
  retention_days: number;
  default_ai_provider: string;
  api_restrictions: Record<string, any>;
  updated_at: string;
}

export interface WorkspaceConfiguration {
  id: string;
  workspace_id: string;
  timezone: string;
  branding: Record<string, any>;
  default_provider?: string;
  ai_preferences: Record<string, any>;
  notification_preferences: Record<string, any>;
}

export interface ApiKey {
  id: string;
  workspace_id: string;
  user_id?: string;
  service_account_id?: string;
  name: string;
  description?: string;
  key_prefix: string;
  scopes: string[];
  last_used_at?: string;
  expires_at?: string;
  is_active: boolean;
  created_at: string;
}

export interface ApiKeyCreateResponse extends ApiKey {
  raw_key: string;
}

// API Service Methods
export async function fetchCurrentIdentity(): Promise<CurrentIdentity> {
  return apiClient({ url: "/auth/context" });
}

export async function fetchCurrentUser(): Promise<UserProfile> {
  return apiClient({ url: "/auth/me" });
}

export async function fetchWorkspaces(): Promise<Workspace[]> {
  return apiClient({ url: "/workspaces" });
}

export async function fetchCurrentWorkspace(): Promise<Workspace> {
  return apiClient({ url: "/workspaces/current" });
}

export async function createWorkspace(name: string): Promise<Workspace> {
  return apiClient({ url: "/workspaces", method: "POST", body: { name } });
}

export async function switchWorkspace(workspaceId: string): Promise<Workspace> {
  const ws = await apiClient<Workspace>({
    url: "/workspaces/switch",
    method: "POST",
    body: { workspace_id: workspaceId },
  });
  if (typeof window !== "undefined") {
    localStorage.setItem("atlas_workspace_id", ws.id);
  }
  return ws;
}

export async function fetchWorkspacePolicies(workspaceId: string): Promise<WorkspacePolicy> {
  return apiClient({ url: `/workspaces/${workspaceId}/policies` });
}

export async function updateWorkspacePolicies(
  workspaceId: string,
  payload: Partial<WorkspacePolicy>
): Promise<WorkspacePolicy> {
  return apiClient({ url: `/workspaces/${workspaceId}/policies`, method: "PATCH", body: payload });
}

export async function fetchWorkspaceConfig(workspaceId: string): Promise<WorkspaceConfiguration> {
  return apiClient({ url: `/workspaces/${workspaceId}/configuration` });
}

export async function updateWorkspaceConfig(
  workspaceId: string,
  payload: Partial<WorkspaceConfiguration>
): Promise<WorkspaceConfiguration> {
  return apiClient({ url: `/workspaces/${workspaceId}/configuration`, method: "PATCH", body: payload });
}

export async function fetchServiceAccounts(workspaceId: string): Promise<ServiceAccount[]> {
  return apiClient({ url: `/workspaces/${workspaceId}/service-accounts` });
}

export async function createServiceAccount(
  workspaceId: string,
  payload: { name: string; description?: string; role_name?: string }
): Promise<ServiceAccount> {
  return apiClient({ url: `/workspaces/${workspaceId}/service-accounts`, method: "POST", body: payload });
}

export async function deleteServiceAccount(workspaceId: string, saId: string): Promise<void> {
  return apiClient({ url: `/workspaces/${workspaceId}/service-accounts/${saId}`, method: "DELETE" });
}

export async function fetchApiKeys(workspaceId: string): Promise<ApiKey[]> {
  return apiClient({ url: `/workspaces/${workspaceId}/api-keys` });
}

export async function createApiKey(
  workspaceId: string,
  payload: { name: string; description?: string; service_account_id?: string; scopes?: string[] }
): Promise<ApiKeyCreateResponse> {
  return apiClient({ url: `/workspaces/${workspaceId}/api-keys`, method: "POST", body: payload });
}

export async function revokeApiKey(workspaceId: string, keyId: string): Promise<void> {
  return apiClient({ url: `/workspaces/${workspaceId}/api-keys/${keyId}`, method: "DELETE" });
}

export async function unlinkOAuthProvider(provider: string): Promise<{ message: string }> {
  return apiClient({ url: `/auth/unlink/${provider}`, method: "DELETE" });
}

export async function mergeUserAccounts(secondaryUserId: string): Promise<UserProfile> {
  return apiClient({ url: "/auth/merge", method: "POST", body: { secondary_user_id: secondaryUserId } });
}

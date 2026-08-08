import { apiClient } from "@/utils/apiClient";
import { API_ROUTES } from "@/constants";

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

export interface CurrentIdentity {
  auth_type: string;
  request_id: string;
  correlation_id: string;
  user?: UserProfile;
  permissions: string[];
}

// API Service Methods
export async function fetchCurrentIdentity(): Promise<CurrentIdentity> {
  return apiClient({ url: API_ROUTES.AUTH_CONTEXT });
}

export async function fetchCurrentUser(): Promise<UserProfile> {
  return apiClient({ url: API_ROUTES.AUTH_ME });
}

export async function unlinkOAuthProvider(provider: string): Promise<{ message: string }> {
  return apiClient({ url: API_ROUTES.AUTH_UNLINK(provider), method: "DELETE" });
}

export async function mergeUserAccounts(secondaryUserId: string): Promise<UserProfile> {
  return apiClient({ url: API_ROUTES.AUTH_MERGE, method: "POST", body: { secondary_user_id: secondaryUserId } });
}

export interface WorkspaceCapability {
  id: string;
  capability: string;
}

export interface IntegrationUser {
  id: string;
  integration_id: string;
  provider_user_id: string;
  username: string | null;
  name: string | null;
  email: string | null;
  avatar_url: string | null;
  is_bot: string | null;
  is_active: boolean;
  can_read: boolean;
  can_write: boolean;
  can_delete: boolean;
  raw_profile: Record<string, any> | null;
  created_at: string;
}

export interface AvailableIntegration {
  id: string;
  name: string;
  icon: string;
}

export interface ConnectedIntegration {
  id: string;
  workspace_id: string;
  provider_type: string;
  status: string;
  created_at: string;
}

export async function fetchAvailableIntegrations(): Promise<AvailableIntegration[]> {
  return apiClient({ url: API_ROUTES.INTEGRATIONS_AVAILABLE });
}

export async function fetchMyIntegrations(): Promise<ConnectedIntegration[]> {
  return apiClient({ url: API_ROUTES.INTEGRATIONS_ME });
}

export async function disconnectIntegration(integrationId: string): Promise<void> {
  return apiClient({ url: API_ROUTES.INTEGRATION_DISCONNECT(integrationId), method: "DELETE" });
}

export async function syncIntegrationUsers(integrationId: string): Promise<{ status: string; synced_users: number }> {
  return apiClient({ url: API_ROUTES.INTEGRATION_USERS_SYNC(integrationId), method: "POST" });
}

export async function fetchIntegrationUsers(integrationId: string): Promise<IntegrationUser[]> {
  return apiClient({ url: API_ROUTES.INTEGRATION_USERS(integrationId) });
}

export async function fetchAllIntegrationUsers(): Promise<IntegrationUser[]> {
  return apiClient({ url: API_ROUTES.INTEGRATION_USERS_ALL });
}

export async function updateIntegrationUserPermissions(userId: string, payload: Partial<IntegrationUser>): Promise<IntegrationUser> {
  return apiClient({ url: API_ROUTES.INTEGRATION_USER_PERMISSIONS(userId), method: "PATCH", body: payload });
}

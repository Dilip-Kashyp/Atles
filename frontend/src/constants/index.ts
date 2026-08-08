export const ROUTES = {
  HOME: "/",
  LOGIN: "/login",
  DASHBOARD: "/dashboard",
  USERS: "/users",
  INTEGRATIONS: "/integrations",
};

export const API_ROUTES = {
  AUTH_CONTEXT: "/auth/context",
  AUTH_ME: "/auth/me",
  AUTH_UNLINK: (provider: string) => `/auth/unlink/${provider}`,
  AUTH_MERGE: "/auth/merge",
  AUTH_REFRESH: "/auth/refresh",
  INTEGRATIONS_AVAILABLE: "/integrations/available",
  INTEGRATIONS_ME: "/integrations/me",
  INTEGRATION_CONNECT: (provider: string) => `/integrations/me/${provider}/connect`,
  INTEGRATION_DISCONNECT: (integrationId: string) => `/integrations/me/${integrationId}`,
  INTEGRATION_USERS_SYNC: (integrationId: string) => `/integrations/me/${integrationId}/sync-users`,
  INTEGRATION_USERS: (integrationId: string) => `/integrations/me/${integrationId}/users`,
  INTEGRATION_USERS_ALL: "/integrations/me/all-users",
  INTEGRATION_USER_PERMISSIONS: (userId: string) => `/integrations/me/users/${userId}/permissions`,
};

export const STORAGE_KEYS = {
  ACCESS_TOKEN: "atlas_access_token",
};

export const EVENTS = {
  NOTIFICATION: "atlas-notification",
};

export const CONSTANTS = {
  BASE_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1",
};

import { API_ROUTES, CONSTANTS, EVENTS, ROUTES, STORAGE_KEYS } from "@/constants";

export interface ApiClientOptions {
  url: string;
  method?: "GET" | "POST" | "PATCH" | "DELETE" | "PUT";
  body?: any;
  headers?: Record<string, string>;
}

let isRefreshing = false;
let refreshSubscribers: ((token: string) => void)[] = [];

const onRefreshed = (token: string) => {
  refreshSubscribers.forEach((callback) => callback(token));
  refreshSubscribers = [];
};

const addRefreshSubscriber = (callback: (token: string) => void) => {
  refreshSubscribers.push(callback);
};

export async function apiClient<T = any>({
  url,
  method = "GET",
  body = null,
  headers = {},
}: ApiClientOptions): Promise<T> {
  const isAbsoluteUrl = url.startsWith("http://") || url.startsWith("https://");
  const fetchUrl = isAbsoluteUrl ? url : `${CONSTANTS.BASE_URL}${url}`;

  const getAuthHeaders = () => {
    const token = typeof window !== "undefined" ? localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN) : null;

    const authHeaders: Record<string, string> = {};
    if (token) authHeaders["Authorization"] = `Bearer ${token}`;
    return authHeaders;
  };

  const executeRequest = async (authHeaders: Record<string, string>) => {
    return fetch(fetchUrl, {
      method,
      headers: {
        "Content-Type": "application/json",
        ...authHeaders,
        ...headers,
      },
      body: body ? JSON.stringify(body) : null,
    });
  };

  try {
    let response = await executeRequest(getAuthHeaders());

    if (response.status === 401 && typeof window !== "undefined") {
      if (!isRefreshing) {
        isRefreshing = true;
        try {
          // Attempt to refresh the token
          const refreshResponse = await fetch(`${CONSTANTS.BASE_URL}${API_ROUTES.AUTH_REFRESH}`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({}),
            // Credentials 'include' ensures the HTTP-only refresh cookie is sent
            credentials: "include", 
          });

          if (refreshResponse.ok) {
            const data = await refreshResponse.json();
            const newAccessToken = data.access_token;
            localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, newAccessToken);
            document.cookie = `${STORAGE_KEYS.ACCESS_TOKEN}=${newAccessToken}; path=/; max-age=31536000; SameSite=Lax`;
            isRefreshing = false;
            onRefreshed(newAccessToken);
            
            // Retry the original request
            response = await executeRequest(getAuthHeaders());
          } else {
            throw new Error("Session expired");
          }
        } catch {
          isRefreshing = false;
          refreshSubscribers = [];
          localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
          document.cookie = `${STORAGE_KEYS.ACCESS_TOKEN}=; path=/; max-age=0; SameSite=Lax`;
          
          if (window.location.pathname !== ROUTES.LOGIN) {
            window.dispatchEvent(
              new CustomEvent(EVENTS.NOTIFICATION, {
                detail: { message: "Session expired. Please log in again.", type: "error" },
              })
            );
            window.location.href = ROUTES.LOGIN;
          }
          throw new Error("Session expired. Please log in again.");
        }
      } else {
        // Wait for the token to be refreshed by another request
        return new Promise<T>((resolve, reject) => {
          addRefreshSubscriber(async () => {
            try {
              const retryResponse = await executeRequest(getAuthHeaders());
              const isJson = retryResponse.headers.get("content-type")?.includes("application/json");
              const data = isJson ? await retryResponse.json() : null;
              if (!retryResponse.ok) reject(data);
              else resolve(data as T);
            } catch (err) {
              reject(err);
            }
          });
        });
      }
    }

    const isJson = response.headers.get("content-type")?.includes("application/json");
    const data = isJson ? await response.json() : null;

    if (!response.ok) {
      const errorMsg = data?.detail || data?.message || data?.error || `HTTP error! status: ${response.status}`;
      if (typeof window !== "undefined") {
        window.dispatchEvent(
          new CustomEvent(EVENTS.NOTIFICATION, {
            detail: { message: errorMsg, type: "error" },
          })
        );
      }
      throw new Error(errorMsg);
    }

    return data as T;
  } catch (error: any) {
    console.error("API Client Error:", error.message);
    throw error;
  }
}

/**
 * Navigate to a backend URL by appending the access token as a query parameter.
 * This is useful for OAuth redirects where headers cannot be sent natively by the browser.
 */
export function navigateAuthenticated(path: string) {
  if (typeof window === "undefined") return;
  const token = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
  
  const isAbsoluteUrl = path.startsWith("http://") || path.startsWith("https://");
  const fullUrl = isAbsoluteUrl ? path : `${CONSTANTS.BASE_URL}${path}`;
  
  const urlObj = new URL(fullUrl);
  if (token) {
    urlObj.searchParams.set("token", token);
  }
  
  window.location.href = urlObj.toString();
}

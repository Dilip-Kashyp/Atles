export interface Integration {
  id: string;
  provider_type: string;
  provider_variant: string;
  type: string;
  status: "CONNECTED" | "DISCONNECTED";
  connected_by: string;
}

export interface Workspace {
  id: string;
  name: string;
  role: string;
}

export interface Toast {
  message: string;
  type: "success" | "error";
}

export interface LoginOption {
  id: string;
  label: string;
  description: string;
  icon: string;
  accent: string;
  href: string;
}

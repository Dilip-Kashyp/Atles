"use client";

import React from "react";
import {
  Shield,
  Key,
  Bot,
  Building2,
  FolderGit2,
  Users,
  Lock,
  LogOut,
  Sparkles,
  LayoutDashboard,
  Search,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Clock,
  ArrowRight,
  ArrowLeft,
  ChevronRight,
  ExternalLink,
  RefreshCw,
  Copy,
  Plus,
  Trash2,
  Settings,
  Globe,
  Sliders,
  Activity,
  Layers,
  Terminal,
} from "lucide-react";

export const ShieldIcon = (props: any) => <Shield className="w-5 h-5" {...props} />;
export const KeyIcon = (props: any) => <Key className="w-5 h-5" {...props} />;
export const BotIcon = (props: any) => <Bot className="w-5 h-5" {...props} />;
export const BuildingIcon = (props: any) => <Building2 className="w-5 h-5" {...props} />;
export const FolderIcon = (props: any) => <FolderGit2 className="w-5 h-5" {...props} />;
export const UsersIcon = (props: any) => <Users className="w-5 h-5" {...props} />;
export const LockIcon = (props: any) => <Lock className="w-5 h-5" {...props} />;
export const LogoutIcon = (props: any) => <LogOut className="w-5 h-5" {...props} />;
export const SparklesIcon = (props: any) => <Sparkles className="w-5 h-5" {...props} />;
export const DashboardIcon = (props: any) => <LayoutDashboard className="w-5 h-5" {...props} />;
export const SearchIcon = (props: any) => <Search className="w-5 h-5" {...props} />;
export const CheckCircleIcon = (props: any) => <CheckCircle2 className="w-5 h-5 text-emerald-400" {...props} />;
export const ErrorIcon = (props: any) => <XCircle className="w-5 h-5 text-rose-400" {...props} />;
export const CloseIcon = (props: any) => <XCircle className="w-4 h-4 text-slate-400" {...props} />;
export const WarningIcon = (props: any) => <AlertCircle className="w-5 h-5 text-amber-400" {...props} />;
export const ClockIcon = (props: any) => <Clock className="w-5 h-5" {...props} />;
export const ArrowRightIcon = (props: any) => <ArrowRight className="w-5 h-5" {...props} />;
export const ArrowLeftIcon = (props: any) => <ArrowLeft className="w-5 h-5" {...props} />;
export const ChevronRightIcon = (props: any) => <ChevronRight className="w-5 h-5" {...props} />;
export const ExternalLinkIcon = (props: any) => <ExternalLink className="w-5 h-5" {...props} />;
export const RefreshIcon = (props: any) => <RefreshCw className="w-5 h-5" {...props} />;
export const CopyIcon = (props: any) => <Copy className="w-5 h-5" {...props} />;
export const PlusIcon = (props: any) => <Plus className="w-5 h-5" {...props} />;
export const TrashIcon = (props: any) => <Trash2 className="w-5 h-5 text-rose-400" {...props} />;
export const SettingsIcon = (props: any) => <Settings className="w-5 h-5" {...props} />;
export const GlobeIcon = (props: any) => <Globe className="w-5 h-5" {...props} />;
export const SlidersIcon = (props: any) => <Sliders className="w-5 h-5" {...props} />;
export const ActivityIcon = (props: any) => <Activity className="w-5 h-5" {...props} />;
export const LayersIcon = (props: any) => <Layers className="w-5 h-5" {...props} />;
export const TerminalIcon = (props: any) => <Terminal className="w-5 h-5" {...props} />;

// SVG Provider Icons
export const GoogleIcon = (props: any) => (
  <svg className="w-5 h-5" viewBox="0 0 24 24" {...props}>
    <path
      fill="#4285F4"
      d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17z"
    />
    <path
      fill="#34A853"
      d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.29v3.15C3.26 21.3 7.31 24 12 24z"
    />
    <path
      fill="#FBBC05"
      d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.29C.47 8.21 0 10.05 0 12s.47 3.79 1.29 5.42l3.99-3.15z"
    />
    <path
      fill="#EA4335"
      d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.31 0 3.26 2.7 1.29 6.58l3.99 3.15c.95-2.83 3.6-4.98 6.72-4.98z"
    />
  </svg>
);

export const GitHubIcon = (props: any) => (
  <svg className="w-5 h-5 fill-current" viewBox="0 0 24 24" {...props}>
    <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
  </svg>
);

export const SlackIcon = (props: any) => (
  <svg className="w-5 h-5" viewBox="0 0 24 24" {...props}>
    <path fill="#E01E5A" d="M6 15a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5zm0-2.5a2.5 2.5 0 0 0 2.5-2.5V5a2.5 2.5 0 1 0-5 0v5A2.5 2.5 0 0 0 6 12.5z" />
    <path fill="#36C5F0" d="M9 6a2.5 2.5 0 1 0-5 0 2.5 2.5 0 0 0 5 0zm2.5 0a2.5 2.5 0 0 0 2.5 2.5h5a2.5 2.5 0 1 0 0-5h-5A2.5 2.5 0 0 0 11.5 6z" />
    <path fill="#2EB67D" d="M18 9a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5zm0 2.5a2.5 2.5 0 0 0-2.5 2.5v5a2.5 2.5 0 1 0 5 0v-5a2.5 2.5 0 0 0-2.5-2.5z" />
    <path fill="#ECB22E" d="M15 18a2.5 2.5 0 1 0 5 0 2.5 2.5 0 0 0-5 0zm-2.5 0a2.5 2.5 0 0 0-2.5-2.5h-5a2.5 2.5 0 1 0 0 5h5a2.5 2.5 0 0 0 2.5-2.5z" />
  </svg>
);

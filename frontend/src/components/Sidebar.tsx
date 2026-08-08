"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ROUTES, STORAGE_KEYS } from "@/constants";
import {
  DashboardIcon,
  LogoutIcon,
  SparklesIcon,
  UsersIcon,
} from "./Icons";

export interface NavItem {
  id: string;
  label: string;
  path: string;
  icon: React.ReactNode;
}

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    const t = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
    if (t) setToken(t);
  }, [pathname]);

  const navItems: NavItem[] = [
    { id: "dashboard", label: "Dashboard", path: ROUTES.DASHBOARD, icon: <DashboardIcon className="w-5 h-5" /> },
    { id: "users", label: "User Management", path: ROUTES.USERS, icon: <UsersIcon className="w-5 h-5" /> },
    { id: "integrations", label: "Integrations", path: ROUTES.INTEGRATIONS, icon: <SparklesIcon className="w-5 h-5" /> },
  ];

  const handleLogout = () => {
    localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
    document.cookie = `${STORAGE_KEYS.ACCESS_TOKEN}=; path=/; max-age=0`;
    router.push(ROUTES.LOGIN);
  };

  return (
    <>
      <style jsx global>{`
        .sidebar-capsule {
          display: flex;
          flex-direction: column;
          gap: 8px;
          position: fixed;
          left: max(20px, calc((100vw - 1400px) / 2 + 20px));
          top: 30px;
          height: fit-content;
          width: 76px;
          padding: 14px 8px;
          background: rgba(13, 17, 23, 0.7);
          backdrop-filter: blur(24px);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 36px;
          box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
          z-index: 1000;
          transition: all 0.3s ease;
        }

        .nav-btn {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 4px;
          padding: 10px 4px;
          border-radius: 22px;
          border: 1px solid transparent;
          background: transparent;
          color: #8b949e;
          cursor: pointer;
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
          width: 100%;
        }

        .nav-btn.active {
          background: rgba(59, 130, 246, 0.15);
          border-color: rgba(59, 130, 246, 0.3);
          color: #60a5fa;
          box-shadow: 0 4px 16px rgba(59, 130, 246, 0.2);
        }

        .nav-btn:hover:not(.active) {
          background: rgba(255, 255, 255, 0.05);
          color: #f1f5f9;
          transform: translateY(-2px);
        }

        @media (max-width: 900px) {
          .sidebar-capsule {
            position: fixed;
            top: auto;
            bottom: 16px;
            left: 50%;
            transform: translateX(-50%);
            width: 92%;
            max-width: 440px;
            height: auto;
            flex-direction: row;
            justify-content: space-around;
            padding: 8px 12px;
            border-radius: 28px;
          }
          .nav-btn {
            padding: 6px;
            gap: 2px;
          }
          .hide-on-mobile {
            display: none !important;
          }
        }
      `}</style>

      <div className="sidebar-capsule">
        {/* LOGO */}
        <Link href={ROUTES.DASHBOARD} className="hide-on-mobile">
          <div
            className="w-12 h-12 rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center cursor-pointer mx-auto mb-3 transition-transform hover:scale-105 border border-white/10 shadow-lg shadow-blue-500/20"
          >
            <SparklesIcon className="w-6 h-6 text-white" />
          </div>
        </Link>

        {navItems.map((item) => {
          const isActive = pathname === item.path || (item.path !== "/" && pathname.startsWith(item.path));
          return (
            <button
              key={item.id}
              className={`nav-btn ${isActive ? "active" : ""}`}
              onClick={() => router.push(item.path)}
            >
              {item.icon}
              <span className="hide-on-mobile text-[9px] font-bold uppercase tracking-wider">
                {item.label}
              </span>
            </button>
          );
        })}

        <div className="hide-on-mobile h-px bg-white/10 my-2 mx-2" />

        {/* LOGOUT / LOGIN */}
        {token ? (
          <button className="nav-btn text-rose-400 hover:text-rose-300" onClick={handleLogout}>
            <LogoutIcon className="w-5 h-5" />
            <span className="hide-on-mobile text-[9px] font-bold uppercase tracking-wider">Logout</span>
          </button>
        ) : (
          <button
            className="nav-btn text-blue-400 border-blue-500/20 bg-blue-500/10"
            onClick={() => router.push(ROUTES.LOGIN)}
          >
            <SparklesIcon className="w-5 h-5" />
            <span className="hide-on-mobile text-[9px] font-bold uppercase tracking-wider">Login</span>
          </button>
        )}
      </div>
    </>
  );
}

export default Sidebar;

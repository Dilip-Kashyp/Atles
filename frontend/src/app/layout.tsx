"use client";

import "./globals.css";
import React, { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { EVENTS, ROUTES } from "@/constants";
import Notification from "@/components/Notification";
import Sidebar from "@/components/Sidebar";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [notification, setNotification] = useState<{ message: string; type: any } | null>(null);

  useEffect(() => {
    const handleNotification = (e: CustomEvent) => {
      if (e.detail?.message) {
        setNotification({
          message: e.detail.message,
          type: e.detail.type || "error",
        });
      }
    };

    window.addEventListener(EVENTS.NOTIFICATION as any, handleNotification);
    return () => {
      window.removeEventListener(EVENTS.NOTIFICATION as any, handleNotification);
    };
  }, []);

  const isLoginPage = pathname === ROUTES.LOGIN || pathname === ROUTES.HOME;

  return (
    <html lang="en">
      <body className="bg-[#080b14] text-slate-100 min-h-screen selection:bg-blue-500/30">
        {!isLoginPage && <Sidebar />}

        <main>{children}</main>

        {notification && (
          <Notification
            message={notification.message}
            type={notification.type}
            onClose={() => setNotification(null)}
          />
        )}
      </body>
    </html>
  );
}

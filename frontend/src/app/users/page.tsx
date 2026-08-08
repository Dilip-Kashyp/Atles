"use client";

import React, { useState, useEffect } from "react";
import {
  Card,
  Chip,
  RefreshIcon,
  Stack,
  Typography,
  UsersIcon,
  Button,
} from "@/components";
import { fetchAllIntegrationUsers, updateIntegrationUserPermissions, IntegrationUser } from "@/services/api";
import { EVENTS } from "@/constants";

export default function UsersPage() {
  const [users, setUsers] = useState<IntegrationUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [managingUser, setManagingUser] = useState<IntegrationUser | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await fetchAllIntegrationUsers();
      setUsers(data);
    } catch (err: any) {
      console.error("Failed to load users", err);
      window.dispatchEvent(
        new CustomEvent(EVENTS.NOTIFICATION, {
          detail: { message: "Failed to load users", type: "error" },
        })
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleUpdatePermission = async (field: keyof IntegrationUser, value: boolean) => {
    if (!managingUser) return;
    try {
      const updatedUser = await updateIntegrationUserPermissions(managingUser.id, { [field]: value });
      setManagingUser(updatedUser);
      setUsers(prev => prev.map(u => (u.id === updatedUser.id ? updatedUser : u)));
    } catch (err: any) {
      console.error("Failed to update permission", err);
      window.dispatchEvent(
        new CustomEvent(EVENTS.NOTIFICATION, {
          detail: { message: "Failed to update permission", type: "error" },
        })
      );
    }
  };

  return (
    <div className="min-h-screen bg-[#080b14] pl-28 pr-8 py-8">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <Typography variant="h1">User Management</Typography>
            <Typography variant="subtitle">
              Administer system access and view all users
            </Typography>
          </div>

          <Button
            variant="secondary"
            size="sm"
            startIcon={<RefreshIcon className="w-4 h-4" />}
            onClick={loadData}
            disabled={loading}
          >
            {loading ? "Refreshing..." : "Refresh"}
          </Button>
        </div>

        {/* Users Table / List */}
        <Card>
          <Stack gap={4}>
            <div className="flex items-center gap-2 mb-4">
              <UsersIcon className="w-5 h-5 text-blue-400" />
              <Typography variant="h3">System Users</Typography>
            </div>
            
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-white/10">
                    <th className="p-3 text-sm font-semibold text-slate-300">User</th>
                    <th className="p-3 text-sm font-semibold text-slate-300">Status</th>
                    <th className="p-3 text-sm font-semibold text-slate-300">Created At</th>
                    <th className="p-3 text-sm font-semibold text-slate-300 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.length === 0 && !loading && (
                    <tr>
                      <td colSpan={4} className="p-4 text-center text-slate-400">
                        No users found. Try connecting and syncing an integration first!
                      </td>
                    </tr>
                  )}
                  {users.map((user) => (
                    <React.Fragment key={user.id}>
                      <tr className="border-b border-white/5 hover:bg-white/5 transition-colors">
                        <td className="p-3">
                          <div className="flex items-center gap-3">
                            {user.avatar_url ? (
                                <img src={user.avatar_url} className="w-8 h-8 rounded-full" alt="" />
                            ) : (
                                <div className="w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center text-blue-400 font-bold text-xs uppercase">
                                  {(user.name || user.username || "?").charAt(0)}
                                </div>
                            )}
                            
                            <div>
                              <Typography variant="body1" className="font-medium text-slate-200">
                                {user.name || user.username}
                              </Typography>
                              <Typography variant="caption" className="text-slate-400">
                                {user.email || user.provider_user_id} {user.is_bot === "True" && "(Bot)"}
                              </Typography>
                            </div>
                          </div>
                        </td>
                        <td className="p-3">
                          <Chip
                            label={user.is_active ? "active" : "inactive"}
                            variant={user.is_active ? "success" : "default"}
                            size="sm"
                          />
                        </td>
                        <td className="p-3">
                          <Typography variant="body2" className="text-slate-300">
                            {new Date(user.created_at).toLocaleDateString()}
                          </Typography>
                        </td>
                        <td className="p-3 text-right">
                          <Button 
                            variant={managingUser?.id === user.id ? "primary" : "outline"} 
                            size="sm" 
                            onClick={() => setManagingUser(managingUser?.id === user.id ? null : user)}
                          >
                            {managingUser?.id === user.id ? "Close" : "Manage"}
                          </Button>
                        </td>
                      </tr>
                      {managingUser?.id === user.id && (
                        <tr className="bg-slate-800/50">
                          <td colSpan={4} className="p-4 border-b border-white/5">
                            <Stack gap={4}>
                              <Typography variant="h4">Manage Permissions</Typography>
                              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                <label className="flex items-center gap-2 cursor-pointer">
                                  <input type="checkbox" checked={managingUser.is_active} onChange={e => handleUpdatePermission("is_active", e.target.checked)} className="rounded bg-slate-900 border-white/20 text-blue-500 focus:ring-blue-500 focus:ring-offset-slate-900" />
                                  <span className="text-sm text-slate-200">Is Active</span>
                                </label>
                                <label className="flex items-center gap-2 cursor-pointer">
                                  <input type="checkbox" checked={managingUser.can_read} onChange={e => handleUpdatePermission("can_read", e.target.checked)} className="rounded bg-slate-900 border-white/20 text-blue-500 focus:ring-blue-500 focus:ring-offset-slate-900" />
                                  <span className="text-sm text-slate-200">Can Read</span>
                                </label>
                                <label className="flex items-center gap-2 cursor-pointer">
                                  <input type="checkbox" checked={managingUser.can_write} onChange={e => handleUpdatePermission("can_write", e.target.checked)} className="rounded bg-slate-900 border-white/20 text-blue-500 focus:ring-blue-500 focus:ring-offset-slate-900" />
                                  <span className="text-sm text-slate-200">Can Write</span>
                                </label>
                                <label className="flex items-center gap-2 cursor-pointer">
                                  <input type="checkbox" checked={managingUser.can_delete} onChange={e => handleUpdatePermission("can_delete", e.target.checked)} className="rounded bg-slate-900 border-white/20 text-blue-500 focus:ring-blue-500 focus:ring-offset-slate-900" />
                                  <span className="text-sm text-slate-200">Can Delete</span>
                                </label>
                              </div>
                            </Stack>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          </Stack>
        </Card>
      </div>
    </div>
  );
}

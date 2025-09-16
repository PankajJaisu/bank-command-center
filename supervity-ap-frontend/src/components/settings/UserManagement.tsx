"use client";
import React, { useState, useEffect, useCallback } from "react";
import {
  getAllUsers,
  approveUser,
  updateUserRole,
  type UserWithVendors,
} from "@/lib/api";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/Table";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Loader2 } from "lucide-react";
import toast from "react-hot-toast";
import { UserPolicyManager } from "./UserPolicyManager";
import { formatRule } from "@/lib/utils";
import { type Policy } from "./AdvancedRuleBuilder";
import { useAppContext } from "@/lib/AppContext";

export const UserManagement = () => {
  const { currentUser } = useAppContext();
  const [users, setUsers] = useState<UserWithVendors[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isPolicyModalOpen, setIsPolicyModalOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<UserWithVendors | null>(
    null,
  );
  const [updatingUserId, setUpdatingUserId] = useState<number | null>(null);

  const fetchUsers = useCallback(() => {
    setIsLoading(true);
    getAllUsers()
      .then(setUsers)
      .catch((err) => {
        console.error("Error fetching users:", err);
        toast.error("Failed to fetch users");
      })
      .finally(() => setIsLoading(false));
  }, []);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const handleApprove = async (userId: number) => {
    try {
      await approveUser(userId);
      toast.success("User approved successfully!");
      fetchUsers(); // Refresh the list
    } catch (error) {
      console.error("Error approving user:", error);
      toast.error("Failed to approve user");
    }
  };

  const handleRoleChange = async (
    user: UserWithVendors,
    newRoleName: string,
  ) => {
    if (newRoleName === user.role.name) return;
    if (
      !window.confirm(
        `Are you sure you want to change ${user.email}'s role to "${newRoleName}"?`,
      )
    ) {
      return;
    }
    setUpdatingUserId(user.id);
    try {
      await updateUserRole(user.id, newRoleName);
      toast.success(`${user.email}'s role updated to ${newRoleName}.`);
      fetchUsers(); // Refresh the list with updated data
    } catch (error) {
      toast.error(
        `Failed to update role: ${error instanceof Error ? error.message : "Unknown error"}`,
      );
    } finally {
      setUpdatingUserId(null);
    }
  };

  const openPolicyModal = (user: UserWithVendors) => {
    setSelectedUser(user);
    setIsPolicyModalOpen(true);
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center p-8">
        <Loader2 className="w-8 h-8 animate-spin" />
      </div>
    );
  }

  return (
    <>
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-semibold">User Management</h3>
          <Button onClick={fetchUsers} variant="secondary" size="sm">
            Refresh
          </Button>
        </div>

        <div className="border rounded-lg overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Email</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Permission Policies</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.map((user) => (
                <TableRow key={user.id}>
                  <TableCell className="font-medium">{user.email}</TableCell>
                  <TableCell>
                    {updatingUserId === user.id ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <select
                        value={user.role.name}
                        onChange={(e) => handleRoleChange(user, e.target.value)}
                        disabled={
                          user.email === "admin@supervity.ai" || // Prevent default admin from being changed
                          currentUser?.id === user.id // Prevent users from changing their own role
                        }
                        className="h-9 rounded-md border border-gray-300 bg-white px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-blue-primary disabled:bg-gray-100 disabled:cursor-not-allowed"
                      >
                        <option value="admin">admin</option>
                        <option value="ap_processor">ap_processor</option>
                      </select>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant={user.is_approved ? "success" : "warning"}>
                      {user.is_approved ? "Approved" : "Pending"}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-col gap-1 text-xs">
                      {user.permission_policies.length > 0 ? (
                        user.permission_policies.map((p) => (
                          <span
                            key={p.id}
                            className="font-mono bg-gray-100 p-1 rounded text-xs"
                          >
                            {p.name}: {formatRule(p.conditions as Policy)}
                          </span>
                        ))
                      ) : (
                        <span className="text-gray-500">None</span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      {!user.is_approved && (
                        <Button
                          size="sm"
                          onClick={() => handleApprove(user.id)}
                        >
                          Approve
                        </Button>
                      )}
                      {user.role.name === "ap_processor" && (
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => openPolicyModal(user)}
                        >
                          Manage Policies
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          {users.length === 0 && (
            <div className="text-center py-8 text-gray-500">No users found</div>
          )}
        </div>
      </div>

      <UserPolicyManager
        isOpen={isPolicyModalOpen}
        onClose={() => setIsPolicyModalOpen(false)}
        user={selectedUser}
        onSave={fetchUsers}
      />
    </>
  );
};

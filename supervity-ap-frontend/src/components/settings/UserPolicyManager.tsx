"use client";
import React, { useState, useEffect } from "react";
import {
  type UserWithVendors,
  type PermissionPolicyCreate,
  updateUserPolicies,
} from "@/lib/api";
import { AdvancedRuleBuilder, type Policy } from "./AdvancedRuleBuilder";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Plus, Save, Trash2 } from "lucide-react";
import { formatRule } from "@/lib/utils";
import toast from "react-hot-toast";

interface UserPolicyManagerProps {
  isOpen: boolean;
  onClose: () => void;
  user: UserWithVendors | null;
  onSave: () => void; // Callback to refresh user list
}

const newPolicyTemplate: PermissionPolicyCreate = {
  name: "New Policy",
  conditions: {
    logical_operator: "AND",
    conditions: [{ field: "vendor_name", operator: "equals", value: "" }],
  },
  is_active: true,
};

export const UserPolicyManager = ({
  isOpen,
  onClose,
  user,
  onSave,
}: UserPolicyManagerProps) => {
  const [policies, setPolicies] = useState<PermissionPolicyCreate[]>([]);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (user) {
      // Convert existing policies to the create format
      const existingPolicies = user.permission_policies.map((p) => ({
        name: p.name,
        conditions: p.conditions,
        is_active: p.is_active,
      }));
      setPolicies(existingPolicies);
    } else {
      setPolicies([]);
    }
  }, [user]);

  const handlePolicyChange = (
    index: number,
    updatedPolicy: PermissionPolicyCreate,
  ) => {
    const newPolicies = [...policies];
    newPolicies[index] = updatedPolicy;
    setPolicies(newPolicies);
  };

  const addPolicy = () => setPolicies([...policies, { ...newPolicyTemplate }]);
  const removePolicy = (index: number) =>
    setPolicies(policies.filter((_, i) => i !== index));

  const handleSave = async () => {
    if (!user) return;
    setIsSaving(true);
    try {
      await updateUserPolicies(user.id, policies);
      toast.success("User policies updated successfully!");
      onSave(); // Refresh the user list in the parent
      onClose();
    } catch (error) {
      toast.error(
        `Failed to save policies: ${error instanceof Error ? error.message : "Unknown error"}`,
      );
    } finally {
      setIsSaving(false);
    }
  };

  if (!user) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Manage Policies for ${user.email}`}
    >
      <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-2">
        {policies.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No policies configured. Add a policy to get started.
          </div>
        ) : (
          policies.map((policy, index) => (
            <div key={index} className="p-4 border rounded-lg">
              <div className="flex justify-between items-center mb-4">
                <Input
                  value={policy.name}
                  onChange={(e) =>
                    handlePolicyChange(index, {
                      ...policy,
                      name: e.target.value,
                    })
                  }
                  className="font-semibold text-base"
                  placeholder="Policy name"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => removePolicy(index)}
                >
                  <Trash2 className="h-4 w-4 text-red-500" />
                </Button>
              </div>
              <div className="mb-2">
                <p className="text-sm text-gray-600 mb-1">Current rule:</p>
                <div className="text-xs font-mono bg-gray-100 p-2 rounded">
                  {formatRule(policy.conditions as Policy)}
                </div>
              </div>
              <AdvancedRuleBuilder
                policy={policy.conditions as Policy}
                onPolicyChange={(newConditions) =>
                  handlePolicyChange(index, {
                    ...policy,
                    conditions: newConditions,
                  })
                }
              />
            </div>
          ))
        )}
        <Button
          type="button"
          variant="secondary"
          onClick={addPolicy}
          className="w-full"
        >
          <Plus className="mr-2 h-4 w-4" /> Add Policy
        </Button>
      </div>
      <div className="flex justify-end gap-2 pt-4 border-t mt-4">
        <Button variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button onClick={handleSave} disabled={isSaving}>
          <Save className="mr-2 h-4 w-4" />{" "}
          {isSaving ? "Saving..." : "Save All Policies"}
        </Button>
      </div>
    </Modal>
  );
};

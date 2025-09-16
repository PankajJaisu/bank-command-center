"use client";
import React, { useState, useEffect, FormEvent } from "react";
import {
  getAutomationRules,
  createAutomationRule,
  updateAutomationRule,
  deleteAutomationRule,
  type AutomationRule,
  type AutomationRuleCreate,
} from "@/lib/api";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Pencil, Trash2, PlusCircle } from "lucide-react";
import toast from "react-hot-toast";
import { AdvancedRuleBuilder, type Policy } from "./AdvancedRuleBuilder"; // --- IMPORT ADVANCED BUILDER ---
import { formatRule } from "@/lib/utils"; // --- IMPORT FORMATTER ---

const initialFormData: AutomationRuleCreate = {
  rule_name: "",
  vendor_name: null,
  // --- USE THE NEW POLICY STRUCTURE ---
  conditions: {
    logical_operator: "AND",
    conditions: [{ field: "grand_total", operator: "<", value: 100 }],
  },
  action: "approve",
  is_active: true,
  source: "user",
};

export const AutomationRulesManager = () => {
  const [rules, setRules] = useState<AutomationRule[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<AutomationRule | null>(null);
  const [formData, setFormData] =
    useState<AutomationRuleCreate>(initialFormData);

  const fetchRules = () => getAutomationRules().then(setRules);

  useEffect(() => {
    fetchRules();
  }, []);

  const openModalForEdit = (rule: AutomationRule) => {
    setEditingRule(rule);
    setFormData({
      ...rule,
      // Ensure conditions are in the correct format
      conditions:
        typeof rule.conditions === "object" &&
        rule.conditions !== null &&
        !Array.isArray(rule.conditions)
          ? rule.conditions
          : { logical_operator: "AND", conditions: [] },
    });
    setIsModalOpen(true);
  };

  const openModalForNew = () => {
    setEditingRule(null);
    setFormData(initialFormData);
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingRule(null);
  };

  const handleDelete = async (id: number) => {
    if (window.confirm("Are you sure you want to delete this rule?")) {
      try {
        await deleteAutomationRule(id);
        toast.success("Rule deleted!");
        fetchRules();
      } catch {
        toast.error("Failed to delete rule.");
      }
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const apiCall = editingRule
      ? updateAutomationRule(editingRule.id, formData)
      : createAutomationRule(formData);

    try {
      await apiCall;
      toast.success(`Rule ${editingRule ? "updated" : "created"}!`);
      fetchRules();
      closeModal();
    } catch (err) {
      toast.error(
        `Failed to save rule: ${err instanceof Error ? err.message : "Unknown error"}`,
      );
    }
  };

  return (
    <>
      <div className="flex justify-end mb-4">
        <Button onClick={openModalForNew}>
          <PlusCircle className="mr-2 h-4 w-4" /> Add Automation Rule
        </Button>
      </div>
      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Rule Name</TableHead>
              <TableHead>Vendor</TableHead>
              <TableHead>Condition</TableHead>
              <TableHead>Action</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rules.map((rule) => (
              <TableRow key={rule.id}>
                <TableCell className="font-medium">{rule.rule_name}</TableCell>
                <TableCell>{rule.vendor_name || "Any Vendor"}</TableCell>
                <TableCell>
                  <span className="font-mono text-xs bg-gray-100 px-2 py-1 rounded">
                    {formatRule(rule.conditions as unknown as Policy)}
                  </span>
                </TableCell>
                <TableCell>
                  <Badge variant="success">{rule.action}</Badge>
                </TableCell>
                <TableCell className="text-right">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => openModalForEdit(rule)}
                  >
                    <Pencil className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-pink-destructive hover:text-pink-destructive"
                    onClick={() => handleDelete(rule.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <Modal
        isOpen={isModalOpen}
        onClose={closeModal}
        title={
          editingRule ? "Edit Automation Rule" : "Create New Automation Rule"
        }
      >
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* --- USE THE ADVANCED BUILDER --- */}
          <AdvancedRuleBuilder
            policy={formData.conditions as unknown as Policy}
            onPolicyChange={(newConditions) =>
              setFormData({
                ...formData,
                conditions: newConditions as unknown as Record<string, unknown>,
              })
            }
          />
          <div className="flex justify-end gap-2 border-t pt-4 mt-4">
            <Button type="button" variant="secondary" onClick={closeModal}>
              Cancel
            </Button>
            <Button type="submit">Save Rule</Button>
          </div>
        </form>
      </Modal>
    </>
  );
};

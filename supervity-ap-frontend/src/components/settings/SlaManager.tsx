"use client";
import React, { useState, useEffect, useCallback, FormEvent } from "react";
import {
  getSLAs,
  createSLA,
  updateSLA,
  deleteSLA,
  type SLA,
  type SLACreate,
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
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { Checkbox } from "@/components/ui/Checkbox";
import { Textarea } from "@/components/ui/Textarea";
import { Pencil, Trash2, PlusCircle, Check, X } from "lucide-react";
import toast from "react-hot-toast";
// --- NEW IMPORTS ---
import { AdvancedRuleBuilder, type Policy } from "./AdvancedRuleBuilder";
import { formatRule } from "@/lib/utils";
// --- END NEW IMPORTS ---

const initialPolicy: Policy = {
  logical_operator: "AND",
  conditions: [{ field: "status", operator: "equals", value: "needs_review" }],
};

const initialFormData: SLACreate = {
  name: "",
  description: "",
  conditions: initialPolicy as unknown as Record<string, unknown>,
  threshold_hours: 24,
  is_active: true,
};

export const SlaManager = () => {
  const [slas, setSlas] = useState<SLA[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingSla, setEditingSla] = useState<SLA | null>(null);
  const [formData, setFormData] = useState<SLACreate>(initialFormData);
  const [isLoading, setIsLoading] = useState(false);

  const fetchSLAs = useCallback(async () => {
    try {
      const data = await getSLAs();
      setSlas(data);
    } catch (error) {
      console.error("Error fetching SLAs:", error);
      toast.error("Failed to load SLAs");
    }
  }, []);

  useEffect(() => {
    fetchSLAs();
  }, [fetchSLAs]);

  const openModalForEdit = (sla: SLA) => {
    setEditingSla(sla);
    setFormData({
      name: sla.name,
      description: sla.description || "",
      conditions: sla.conditions as unknown as Record<string, unknown>, // Cast to match expected type
      threshold_hours: sla.threshold_hours,
      is_active: sla.is_active,
    });
    setIsModalOpen(true);
  };

  const openModalForNew = () => {
    setEditingSla(null);
    setFormData(initialFormData);
    setIsModalOpen(true);
  };

  const handleDelete = async (id: number) => {
    if (window.confirm("Are you sure you want to delete this SLA policy?")) {
      try {
        await deleteSLA(id);
        toast.success("SLA policy deleted!");
        fetchSLAs();
      } catch (error) {
        console.error("Error deleting SLA:", error);
        toast.error("Failed to delete SLA policy.");
      }
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      if (editingSla) {
        await updateSLA(editingSla.id, formData);
        toast.success("SLA policy updated!");
      } else {
        await createSLA(formData);
        toast.success("SLA policy created!");
      }
      fetchSLAs();
      setIsModalOpen(false);
    } catch (error) {
      console.error("Error saving SLA:", error);
      toast.error(
        `Failed to save SLA policy: ${error instanceof Error ? error.message : "Unknown error"}`,
      );
    } finally {
      setIsLoading(false);
    }
  };

  // Remove the old formatConditions function - we'll use formatRule instead

  return (
    <>
      <div className="flex justify-end mb-4">
        <Button onClick={openModalForNew}>
          <PlusCircle className="mr-2 h-4 w-4" /> Add SLA Policy
        </Button>
      </div>
      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Description</TableHead>
              <TableHead>Condition</TableHead>
              <TableHead>Threshold</TableHead>
              <TableHead>Active</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {slas.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={6}
                  className="text-center py-8 text-gray-500"
                >
                  No SLA policies configured yet. Create one to get started.
                </TableCell>
              </TableRow>
            ) : (
              slas.map((sla) => (
                <TableRow key={sla.id}>
                  <TableCell className="font-medium">{sla.name}</TableCell>
                  <TableCell className="max-w-xs truncate">
                    {sla.description || "—"}
                  </TableCell>
                  <TableCell>
                    <span className="font-mono text-xs bg-gray-100 px-2 py-1 rounded">
                      {formatRule(sla.conditions as unknown as Policy)}
                    </span>
                  </TableCell>
                  <TableCell>{sla.threshold_hours} hours</TableCell>
                  <TableCell>
                    {sla.is_active ? (
                      <Check className="h-4 w-4 text-green-600" />
                    ) : (
                      <X className="h-4 w-4 text-red-600" />
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => openModalForEdit(sla)}
                      className="mr-2"
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-red-600 hover:text-red-700"
                      onClick={() => handleDelete(sla.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingSla ? "Edit SLA Policy" : "Create New SLA Policy"}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="name"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              SLA Name *
            </label>
            <Input
              id="name"
              value={formData.name}
              onChange={(e) =>
                setFormData({ ...formData, name: e.target.value })
              }
              required
              placeholder="e.g., Standard Review Time"
            />
          </div>

          <div>
            <label
              htmlFor="description"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Description
            </label>
            <Textarea
              id="description"
              value={formData.description || ""}
              onChange={(e) =>
                setFormData({ ...formData, description: e.target.value })
              }
              placeholder="Optional description of this SLA policy"
              rows={3}
            />
          </div>

          <div>
            <label
              htmlFor="threshold"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Threshold (hours) *
            </label>
            <Input
              id="threshold"
              type="number"
              value={formData.threshold_hours}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  threshold_hours: parseInt(e.target.value) || 0,
                })
              }
              required
              min="1"
              placeholder="24"
            />
          </div>

          <div>
            <p className="block text-sm font-medium text-gray-700 mb-1">
              Conditions
            </p>
            <p className="text-xs text-gray-500 mb-2">
              This SLA will apply to invoices matching ALL (AND) or ANY (OR) of
              these conditions.
            </p>
            <AdvancedRuleBuilder
              policy={formData.conditions as unknown as Policy}
              onPolicyChange={(newPolicy) =>
                setFormData({
                  ...formData,
                  conditions: newPolicy as unknown as Record<string, unknown>,
                })
              }
            />
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="is_active"
              checked={formData.is_active}
              onCheckedChange={(checked) =>
                setFormData({ ...formData, is_active: !!checked })
              }
            />
            <label
              htmlFor="is_active"
              className="text-sm font-medium text-gray-700"
            >
              SLA is active
            </label>
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setIsModalOpen(false)}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isLoading}>
              {isLoading ? "Saving..." : "Save SLA Policy"}
            </Button>
          </div>
        </form>
      </Modal>
    </>
  );
};

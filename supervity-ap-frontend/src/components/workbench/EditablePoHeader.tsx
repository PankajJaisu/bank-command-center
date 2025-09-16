"use client";

import { useState, useEffect } from "react";
import {
  type PoHeader,
  type PoEditableField,
  updatePurchaseOrder,
} from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import toast from "react-hot-toast";
import { Save, Loader2 } from "lucide-react";

interface EditablePoHeaderProps {
  poData: PoHeader;
  editableFields: PoEditableField[];
  onUpdate: () => void;
}

export const EditablePoHeader = ({
  poData,
  editableFields,
  onUpdate,
}: EditablePoHeaderProps) => {
  const [formData, setFormData] = useState<Record<string, string | number>>({});
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    // Initialize form data with existing PO data
    const initialData: Record<string, string | number> = {};
    editableFields.forEach((field) => {
      const value = (poData as Record<string, unknown>)[field.field_name];
      // Convert unknown value to string or number
      if (typeof value === "number") {
        initialData[field.field_name] = value;
      } else if (typeof value === "string") {
        initialData[field.field_name] = value;
      } else {
        initialData[field.field_name] = value?.toString() ?? "";
      }
    });
    setFormData(initialData);
  }, [poData, editableFields]);

  const handleFieldChange = (fieldName: string, value: string) => {
    setFormData((prev) => ({ ...prev, [fieldName]: value }));
  };

  const handleSave = async () => {
    setIsSaving(true);
    // Convert numeric fields from string back to number
    const changes: Record<string, string | number> = {};
    for (const key in formData) {
      const originalValue = (poData as Record<string, unknown>)[key];
      const newValue = formData[key];
      // Only include changed fields
      if (newValue !== originalValue) {
        if (typeof originalValue === "number") {
          changes[key] = parseFloat(String(newValue)) || 0;
        } else {
          changes[key] = String(newValue);
        }
      }
    }

    if (Object.keys(changes).length === 0) {
      toast("No changes to save.", { icon: "ℹ️" });
      setIsSaving(false);
      return;
    }

    try {
      await updatePurchaseOrder(poData.id, { changes, version: 1 });
      toast.success("PO updated successfully! Re-matching in background.");
      onUpdate();
    } catch (error) {
      toast.error(
        `Failed to save PO: ${error instanceof Error ? error.message : "Unknown error"}`,
      );
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex justify-between items-center">
          <CardTitle>Editable PO Details ({poData.po_number})</CardTitle>
          <Button onClick={handleSave} disabled={isSaving} size="sm">
            {isSaving ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Save className="mr-2 h-4 w-4" />
            )}
            Save PO Changes
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {editableFields.map((field) => (
            <div key={field.field_name}>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {field.display_name}
              </label>
              <Input
                type={
                  typeof (poData as Record<string, unknown>)[
                    field.field_name
                  ] === "number"
                    ? "number"
                    : "text"
                }
                value={formData[field.field_name] ?? ""}
                onChange={(e) =>
                  handleFieldChange(field.field_name, e.target.value)
                }
              />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};

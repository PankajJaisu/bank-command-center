"use client";

import { useEffect, useState, FormEvent } from "react";
import { type VendorSettingCreate } from "@/lib/api";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Loader2 } from "lucide-react";

interface VendorPolicyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (policy: VendorSettingCreate, id?: number) => Promise<void>;
  initialData?: VendorSettingCreate & { id?: number };
}

const initialFormData: VendorSettingCreate = {
  vendor_name: "",
  price_tolerance_percent: 5.0,
  quantity_tolerance_percent: 2.0,
  contact_email: "",
};

export const VendorPolicyModal = ({
  isOpen,
  onClose,
  onSave,
  initialData,
}: VendorPolicyModalProps) => {
  const [formData, setFormData] =
    useState<VendorSettingCreate>(initialFormData);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (initialData) {
      setFormData({
        vendor_name: initialData.vendor_name,
        price_tolerance_percent: initialData.price_tolerance_percent ?? 5.0,
        quantity_tolerance_percent:
          initialData.quantity_tolerance_percent ?? 0.0,
        contact_email: initialData.contact_email ?? "",
      });
    } else {
      setFormData(initialFormData);
    }
  }, [initialData, isOpen]);

  const handleChange = (field: keyof VendorSettingCreate, value: string) => {
    const isNumeric = field.includes("tolerance");
    setFormData((prev) => ({
      ...prev,
      [field]: isNumeric ? (value === "" ? null : parseFloat(value)) : value,
    }));
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    await onSave(formData, initialData?.id);
    setIsSaving(false);
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        initialData
          ? `Edit Policy for ${initialData.vendor_name}`
          : "Add New Vendor Policy"
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-dark">
            Vendor Name
          </label>
          <Input
            value={formData.vendor_name}
            onChange={(e) => handleChange("vendor_name", e.target.value)}
            required
            disabled={!!initialData} // Don't allow editing name of existing vendor
            placeholder="e.g., Industrial Partners Ltd"
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-dark">
              Price Tolerance (%)
            </label>
            <Input
              type="number"
              step="0.1"
              value={formData.price_tolerance_percent ?? ""}
              onChange={(e) =>
                handleChange("price_tolerance_percent", e.target.value)
              }
              placeholder="e.g., 5.0"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-dark">
              Quantity Tolerance (%)
            </label>
            <Input
              type="number"
              step="0.1"
              value={formData.quantity_tolerance_percent ?? ""}
              onChange={(e) =>
                handleChange("quantity_tolerance_percent", e.target.value)
              }
              placeholder="e.g., 2.0"
            />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-dark">
            Contact Email (Optional)
          </label>
          <Input
            type="email"
            value={formData.contact_email ?? ""}
            onChange={(e) => handleChange("contact_email", e.target.value)}
            placeholder="e.g., accounts@industrialpartners.com"
          />
        </div>
        <div className="flex justify-end gap-2 pt-4 border-t">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={isSaving}>
            {isSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Save Policy
          </Button>
        </div>
      </form>
    </Modal>
  );
};

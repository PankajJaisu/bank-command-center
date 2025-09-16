"use client";
import { useState } from "react";
import { Input } from "../ui/Input";
import { Button } from "../ui/Button";
import { updateGLCode, createPoFromInvoice } from "@/lib/api";
import toast from "react-hot-toast";
import { Save, Loader2, FilePlus2 } from "lucide-react";

interface NonPoReviewProps {
  invoiceDbId: number;
  initialGlCode?: string | null;
  onActionComplete: () => void;
}

export const NonPoReview = ({
  invoiceDbId,
  initialGlCode,
  onActionComplete,
}: NonPoReviewProps) => {
  const [glCode, setGlCode] = useState(initialGlCode || "");
  const [isSaving, setIsSaving] = useState(false);
  const [isCreatingPo, setIsCreatingPo] = useState(false);

  const handleSave = async () => {
    if (!glCode.trim()) {
      toast.error("GL Code cannot be empty.");
      return;
    }
    setIsSaving(true);
    try {
      await updateGLCode(invoiceDbId, glCode);
      toast.success("GL Code saved!");
      onActionComplete(); // --- ADD THIS LINE TO TRIGGER REFRESH ---
    } catch (error) {
      toast.error(
        `Failed to save GL Code: ${error instanceof Error ? error.message : "Unknown error"}`,
      );
    } finally {
      setIsSaving(false);
    }
  };

  const handleCreatePo = async () => {
    setIsCreatingPo(true);
    try {
      await createPoFromInvoice(invoiceDbId);
      toast.success("PO created! The invoice is now being re-matched.");
      onActionComplete(); // This will close the workbench view
    } catch (error) {
      toast.error(
        `Failed to create PO: ${error instanceof Error ? error.message : "Unknown error"}`,
      );
    } finally {
      setIsCreatingPo(false);
    }
  };

  return (
    <div className="p-6 bg-white border rounded-lg">
      <h3 className="text-lg font-semibold text-black">
        Non-PO Invoice Review
      </h3>
      <p className="text-sm text-gray-500 mb-4">
        This invoice is not linked to a Purchase Order. You can either apply a
        GL code or create a PO from this invoice.
      </p>
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Input
            placeholder="Enter GL Code (e.g., 5010-Office-Supplies)"
            value={glCode}
            onChange={(e) => setGlCode(e.target.value)}
          />
          <Button onClick={handleSave} disabled={isSaving || isCreatingPo}>
            {isSaving ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Save className="mr-2 h-4 w-4" />
            )}
            Save GL Code
          </Button>
        </div>
        <div className="flex items-center">
          <div className="flex-grow border-t border-gray-200"></div>
          <span className="flex-shrink mx-4 text-gray-400 text-sm">OR</span>
          <div className="flex-grow border-t border-gray-200"></div>
        </div>
        <div>
          <Button
            onClick={handleCreatePo}
            disabled={isSaving || isCreatingPo}
            variant="secondary"
            className="w-full"
          >
            {isCreatingPo ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <FilePlus2 className="mr-2 h-4 w-4" />
            )}
            Create PO From Invoice
          </Button>
          <p className="text-xs text-gray-500 mt-1 text-center">
            This will generate a new PO using the invoice data and re-run the
            matching process.
          </p>
        </div>
      </div>
    </div>
  );
};

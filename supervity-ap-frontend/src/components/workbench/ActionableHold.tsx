"use client";
import { useState } from "react";
import { putInvoiceOnHold } from "@/lib/api";
import toast from "react-hot-toast";
import { Button } from "@/components/ui/Button";
import { Loader2, Clock } from "lucide-react";

interface ActionableHoldProps {
  invoiceDbId: number;
  onActionComplete: () => void;
  message: string;
}

export const ActionableHold = ({
  invoiceDbId,
  onActionComplete,
  message,
}: ActionableHoldProps) => {
  const [isHolding, setIsHolding] = useState<number | null>(null);

  const handleHold = async (days: number) => {
    setIsHolding(days);
    try {
      await putInvoiceOnHold(invoiceDbId, days);
      toast.success(`Invoice placed on hold for ${days} days.`);
      onActionComplete();
    } catch (error) {
      toast.error(
        `Failed to place on hold: ${error instanceof Error ? error.message : "Unknown error"}`,
      );
    } finally {
      setIsHolding(null);
    }
  };

  return (
    <div className="p-4 rounded-lg bg-orange-warning/10 border-l-4 border-orange-warning">
      <h4 className="font-semibold text-orange-700">GRN Validation</h4>
      <p className="text-sm text-gray-700 mt-1 mb-3">{message}</p>
      <div className="flex items-center gap-2 flex-wrap">
        <p className="text-sm font-medium">Action:</p>
        {[7, 14, 30].map((days) => (
          <Button
            key={days}
            size="sm"
            variant="secondary"
            onClick={() => handleHold(days)}
            disabled={isHolding !== null}
            className="bg-white"
          >
            {isHolding === days ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Clock className="w-4 h-4 mr-2" />
            )}
            Hold for {days} Days
          </Button>
        ))}
      </div>
    </div>
  );
};

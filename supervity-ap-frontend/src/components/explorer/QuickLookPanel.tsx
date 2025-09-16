"use client";
import { useState, useEffect } from "react";
import { getComparisonData, type ComparisonData } from "@/lib/api";
import { Loader2, ArrowRight, AlertTriangle } from "lucide-react";
import { Button } from "../ui/Button";
import Link from "next/link";
import { Badge } from "../ui/Badge";
import { ExceptionSummary } from "../workbench/ExceptionSummary"; // Reusing this component!

interface QuickLookPanelProps {
  invoiceDbId: number;
}

export const QuickLookPanel = ({ invoiceDbId }: QuickLookPanelProps) => {
  const [data, setData] = useState<ComparisonData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setIsLoading(true);
    setError(null);
    getComparisonData(invoiceDbId)
      .then(setData)
      .catch((err) => setError(err.message || "Failed to load data."))
      .finally(() => setIsLoading(false));
  }, [invoiceDbId]);

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-full">
        <Loader2 className="w-8 h-8 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-center text-pink-destructive">
        <AlertTriangle className="mx-auto w-8 h-8 mb-2" />
        {error}
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="p-6 flex flex-col h-full">
      <div className="flex-grow space-y-6">
        <div className="pb-4 border-b">
          <div className="flex justify-between items-start">
            <div>
              <h3 className="text-xl font-bold text-black">
                {data.invoice_id}
              </h3>
              <p className="text-gray-500">From: {data.vendor_name}</p>
            </div>
            <Badge
              variant={
                data.invoice_status === "matched" ? "success" : "warning"
              }
            >
              {data.invoice_status.replace(/_/g, " ")}
            </Badge>
          </div>
          <p className="text-3xl font-bold mt-2">
            ${(data.grand_total ?? 0).toFixed(2)}
          </p>
        </div>

        <div>
          <h4 className="font-semibold text-lg mb-2">Exception Summary</h4>
          <ExceptionSummary
            trace={data.match_trace}
            invoiceDbId={invoiceDbId}
            onActionComplete={() => {}}
          />
        </div>
      </div>

      <div className="mt-auto pt-4 border-t">
        <Link
          href={`/resolution-workbench?invoiceId=${data.invoice_id}`}
          className="w-full"
        >
          <Button className="w-full">
            Go to Workbench <ArrowRight className="ml-2 w-4 h-4" />
          </Button>
        </Link>
      </div>
    </div>
  );
};

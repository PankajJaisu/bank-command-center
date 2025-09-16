"use client";

import { useState, useEffect, useMemo } from "react";
import { type InvoiceSummary, getInvoices } from "@/lib/api";
import toast from "react-hot-toast";
import { cn } from "@/lib/utils";
import { Button } from "../ui/Button";
import { format, parseISO } from "date-fns";
import { EmptyState } from "./EmptyState";
import { Inbox, Loader2, Search } from "lucide-react";

interface InvoiceListProps {
  selectedInvoiceId: string | null;
  onInvoiceSelect: (invoice: InvoiceSummary) => void;
  refreshKey?: number;
  searchTerm?: string;
}

// --- MODIFIED HELPER FUNCTION ---
const getCategoryVariant = (category: string | null | undefined): string => {
  switch (category) {
    case "missing_document":
    case "policy_violation":
      return "border-l-4 border-pink-destructive"; // Use brand color
    case "data_mismatch":
      return "border-l-4 border-orange-warning"; // Use brand color
    default:
      return "border-l-4 border-transparent";
  }
};

export const InvoiceList = ({
  selectedInvoiceId,
  onInvoiceSelect,
  refreshKey,
  searchTerm = "",
}: InvoiceListProps) => {
  const [invoices, setInvoices] = useState<InvoiceSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("needs_review");

  useEffect(() => {
    setIsLoading(true);
    getInvoices(statusFilter)
      .then(setInvoices)
      .catch((error) =>
        toast.error(
          `Failed to fetch invoices: ${error instanceof Error ? error.message : "Unknown error"}`,
        ),
      )
      .finally(() => setIsLoading(false));
  }, [statusFilter, refreshKey]);

  // Filter invoices based on search term
  const filteredInvoices = useMemo(() => {
    if (!searchTerm.trim()) return invoices;

    const searchLower = searchTerm.toLowerCase();
    return invoices.filter(
      (invoice) =>
        invoice.invoice_id.toLowerCase().includes(searchLower) ||
        invoice.vendor_name?.toLowerCase().includes(searchLower) ||
        invoice.grand_total?.toString().includes(searchLower),
    );
  }, [invoices, searchTerm]);

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b">
        <div className="flex gap-2">
          <Button
            size="sm"
            variant={statusFilter === "needs_review" ? "primary" : "secondary"}
            onClick={() => setStatusFilter("needs_review")}
          >
            Review
          </Button>
          <Button
            size="sm"
            variant={statusFilter === "matched" ? "primary" : "secondary"}
            onClick={() => setStatusFilter("matched")}
          >
            Approved
          </Button>
        </div>
      </div>
      <div className="flex-grow overflow-y-auto">
        {/* --- START: MODIFIED RENDER LOGIC --- */}
        {isLoading ? (
          <div className="p-4 flex justify-center items-center h-full">
            <Loader2 className="w-6 h-6 animate-spin text-gray-500" />
          </div>
        ) : filteredInvoices.length === 0 ? (
          <EmptyState
            Icon={searchTerm.trim() ? Search : Inbox}
            title={searchTerm.trim() ? "No Results Found" : "Queue is Clear!"}
            description={
              searchTerm.trim()
                ? `No invoices found matching "${searchTerm}". Try a different search term.`
                : `There are no invoices currently in the "${statusFilter.replace("_", " ")}" state.`
            }
            className="py-16"
          />
        ) : (
          <ul className="p-2 space-y-2">
            {filteredInvoices.map((invoice) => (
              <li
                key={invoice.invoice_id}
                onClick={() => onInvoiceSelect(invoice)}
                className={cn(
                  "p-3 rounded-lg cursor-pointer transition-colors",
                  getCategoryVariant(invoice.review_category),
                  selectedInvoiceId === invoice.invoice_id
                    ? "bg-blue-primary/10"
                    : "bg-white hover:bg-gray-50",
                  "border",
                )}
              >
                <div className="flex justify-between items-center mb-1">
                  <p className="font-semibold">{invoice.invoice_id}</p>
                  <p className="font-bold text-lg">
                    ${invoice.grand_total?.toFixed(2)}
                  </p>
                </div>
                <div className="flex justify-between items-center text-sm text-gray-800">
                  <span className="font-medium">{invoice.vendor_name}</span>
                  <span className="font-medium">
                    {invoice.invoice_date
                      ? format(parseISO(invoice.invoice_date), "MMM d, yyyy")
                      : "N/A"}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
        {/* --- END: MODIFIED RENDER LOGIC --- */}
      </div>
    </div>
  );
};

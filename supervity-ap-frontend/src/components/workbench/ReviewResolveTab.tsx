"use client";
import { type ComparisonData, updateInvoiceNotes } from "@/lib/api";
import { DocumentViewer } from "@/components/shared/DocumentViewer";
import { LineItemComparisonTable } from "./LineItemComparisonTable";
import { NonPoReview } from "./NonPoReview";
import { Textarea } from "../ui/Textarea";
import { Button } from "../ui/Button";
import { useState, useEffect } from "react";
import toast from "react-hot-toast";
import { Save } from "lucide-react";
import { SuggestionCallout } from "./SuggestionCallout";
import { ExceptionSummary } from "./ExceptionSummary";
import { StructuredDataViewer } from "./StructuredDataViewer";
import { InvoiceHeaderDetails } from "./InvoiceHeaderDetails";

interface ReviewResolveTabProps {
  comparisonData: ComparisonData | null;
  invoiceDbId: number;
  onDataUpdate: () => void;
  onApplySuggestion: (action: string) => void;
  onActionComplete: () => void;
}

type ActiveDoc =
  | { type: "INVOICE"; path: string | null; data: null }
  | {
      type: "PO";
      path: string | null;
      data: Record<string, unknown> | Record<string, unknown>[] | null;
    }
  | {
      type: "GRN";
      path: string | null;
      data: Record<string, unknown> | Record<string, unknown>[] | null;
    };

export const ReviewResolveTab = ({
  comparisonData,
  invoiceDbId,
  onDataUpdate,
  onApplySuggestion,
  onActionComplete,
}: ReviewResolveTabProps) => {
  const [notes, setNotes] = useState("");
  const [isSavingNotes, setIsSavingNotes] = useState(false);
  const [activeDoc, setActiveDoc] = useState<ActiveDoc | null>(null);

  // --- START: NEW STATE FOR UNSAVED CHANGES ---
  const [isDirty, setIsDirty] = useState(false);

  useEffect(() => {
    if (comparisonData) {
      const notesChanged = notes !== (comparisonData.invoice_notes || "");
      // We will expand this later to include PO/GL code changes
      setIsDirty(notesChanged);
    }
  }, [notes, comparisonData]);

  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (isDirty) {
        e.preventDefault();
        e.returnValue = ""; // Required for legacy browsers
      }
    };

    window.addEventListener("beforeunload", handleBeforeUnload);

    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
    };
  }, [isDirty]);
  // --- END: NEW STATE FOR UNSAVED CHANGES ---

  useEffect(() => {
    if (comparisonData) {
      setNotes(comparisonData.invoice_notes || "");
      setActiveDoc({
        type: "INVOICE",
        path: comparisonData.related_documents.invoice?.file_path ?? null,
        data: null,
      });
    }
  }, [comparisonData]);

  if (!comparisonData) return <div>Loading comparison data...</div>;

  const handleSaveNotes = async () => {
    setIsSavingNotes(true);
    try {
      await updateInvoiceNotes(invoiceDbId, notes);
      toast.success("Notes saved successfully!");
      setIsDirty(false); // --- RESET DIRTY STATE ON SAVE ---
    } catch (error) {
      toast.error(
        `Failed to save notes: ${error instanceof Error ? error.message : "Unknown error"}`,
      );
    } finally {
      setIsSavingNotes(false);
    }
  };

  const isNonPoInvoice =
    !comparisonData.related_pos || comparisonData.related_pos.length === 0;

  const renderActiveDocument = () => {
    if (!activeDoc) {
      return <div className="p-4">Select a document to view.</div>;
    }

    switch (activeDoc.type) {
      case "INVOICE":
        return <DocumentViewer filePath={activeDoc.path} />;
      case "PO":
      case "GRN":
        return (
          <StructuredDataViewer
            documentType={activeDoc.type}
            data={
              Array.isArray(activeDoc.data)
                ? activeDoc.data
                : activeDoc.data
                  ? [activeDoc.data]
                  : []
            }
          />
        );
      default:
        return <div className="p-4">Select a document to view.</div>;
    }
  };

  const availableDocs: ActiveDoc[] = [
    {
      type: "INVOICE" as const,
      path: comparisonData.related_documents.invoice?.file_path ?? null,
      data: null,
    },
    ...(comparisonData.all_related_documents.pos.length > 0
      ? [
          {
            type: "PO" as const,
            path: null,
            data: comparisonData.all_related_documents.pos.map((p) => p.data),
          },
        ]
      : []),
    ...(comparisonData.all_related_documents.grns.length > 0
      ? [
          {
            type: "GRN" as const,
            path: null,
            data: comparisonData.all_related_documents.grns.map((g) => g.data),
          },
        ]
      : []),
  ];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-full">
      {/* Left Column: Document Viewer */}
      <div className="border rounded-lg flex flex-col bg-white overflow-hidden">
        <div className="p-2 border-b bg-gray-50 flex justify-between items-center flex-shrink-0">
          <h3 className="font-semibold text-black">
            Document Viewer:{" "}
            <span className="text-purple-accent">{activeDoc?.type}</span>
          </h3>
          <div className="flex gap-1">
            {availableDocs.map((doc) => (
              <Button
                key={doc.type}
                variant={activeDoc?.type === doc.type ? "primary" : "secondary"}
                size="sm"
                onClick={() => setActiveDoc(doc)}
                className="text-xs"
              >
                {doc.type === "INVOICE"
                  ? "Invoice"
                  : doc.type === "PO"
                    ? "PO"
                    : "GRN"}
              </Button>
            ))}
          </div>
        </div>
        <div className="flex-grow overflow-y-auto">
          {renderActiveDocument()}
        </div>
      </div>

      {/* Right Column: Details and Actions */}
      <div className="space-y-6 overflow-y-auto pr-2 pb-4">
        {/* Move Invoice Header Details to top for better information hierarchy */}
        <InvoiceHeaderDetails
          headerData={comparisonData.invoice_header_data}
          invoiceMetadata={comparisonData.invoice_header_data?.metadata ?? null}
        />

        {/* --- PASS NEW PROPS TO ExceptionSummary --- */}
        <ExceptionSummary
          trace={comparisonData.match_trace}
          invoiceDbId={invoiceDbId}
          onActionComplete={onActionComplete}
        />

        {comparisonData.suggestion && (
          <SuggestionCallout
            suggestion={comparisonData.suggestion}
            onApply={() => onApplySuggestion(comparisonData.suggestion!.action)}
          />
        )}

        {/* Always show NonPoReview for non-PO invoices */}
        {isNonPoInvoice && (
          <NonPoReview
            invoiceDbId={invoiceDbId}
            initialGlCode={comparisonData.gl_code}
            onActionComplete={onActionComplete}
          />
        )}

        {/* Always show LineItemComparisonTable */}
        <LineItemComparisonTable
          comparisonData={comparisonData}
          onUpdate={onDataUpdate}
        />

        <div>
          <h3 className="text-lg font-semibold mb-2 text-black">
            Reference Notes
          </h3>
          <Textarea
            placeholder="Add any internal notes for this invoice..."
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="min-h-[100px]"
          />
          <Button
            onClick={handleSaveNotes}
            disabled={isSavingNotes || !isDirty}
            size="sm"
            className="mt-2"
          >
            <Save className="mr-2 h-4 w-4" />
            {isSavingNotes ? "Saving..." : "Save Notes"}
          </Button>
        </div>
      </div>
    </div>
  );
};

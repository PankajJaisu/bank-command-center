// src/components/workbench/LineItemComparisonTable.tsx

"use client";
import { useState, useMemo } from "react";
import {
  type ComparisonData,
  updatePurchaseOrder,
  type InvoiceLineItem,
  type PoLineItem,
} from "@/lib/api";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/Table";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import toast from "react-hot-toast";
import { cn } from "@/lib/utils";
import {
  Loader2,
  Save,
  Search,
  ChevronDown,
  CheckCircle2,
  AlertTriangle,
  Info,
  Clock,
  Check,
} from "lucide-react";
import { MetadataModal } from "./MetadataModal";

interface LineItemComparisonTableProps {
  comparisonData: ComparisonData;
  onUpdate: () => void;
}

type EditableFields = {
  [key: string]: { ordered_qty?: number; unit_price?: number };
};

type MismatchType =
  | "none"
  | "price"
  | "quantity"
  | "both"
  | "unmatched"
  | "pending_receipt";

type LineWithMismatchInfo = {
  po_number: string | null;
  invoice_line: InvoiceLineItem | null;
  po_line: PoLineItem | null;
  mismatchType: MismatchType;
  mismatchReason: string | null;
  matchMethod: string | null;
};

const MismatchCell = ({
  children,
  isMismatch,
}: {
  children: React.ReactNode;
  isMismatch: boolean;
}) => (
  <TableCell
    className={cn(
      "text-center font-medium py-2 px-3 align-top",
      isMismatch && "bg-orange-warning/20 text-orange-700",
    )}
  >
    {children}
  </TableCell>
);

const StatusReason = ({
  type,
  reason,
}: {
  type: MismatchType;
  reason: string | null;
}) => {
  if (!reason && type !== "pending_receipt") return null;
  let Icon = AlertTriangle;
  let textColor = "text-orange-warning";
  let message = reason || "An unknown issue occurred.";
  if (type === "pending_receipt") {
    Icon = Clock;
    textColor = "text-blue-primary";
    message = "Item is pending receipt (no GRN found for this item yet).";
  } else if (type === "unmatched") {
    Icon = Info;
    textColor = "text-pink-destructive";
    message = "This item could not be matched to any item on the linked POs.";
  }
  return (
    <div
      className={cn(
        "text-xs font-semibold flex items-center gap-1.5 pt-1",
        textColor,
      )}
    >
      <Icon className="w-4 h-4 flex-shrink-0" />
      <span>{message}</span>
    </div>
  );
};

export const LineItemComparisonTable = ({
  comparisonData,
  onUpdate,
}: LineItemComparisonTableProps) => {
  const [editableFields, setEditableFields] = useState<EditableFields>({});
  const [isSaving, setIsSaving] = useState(false);
  const [lineItemSearch, setLineItemSearch] = useState("");
  const [isMatchedSectionOpen, setIsMatchedSectionOpen] = useState(false);
  const [inspectingLine, setInspectingLine] = useState<object | null>(null);

  const {
    matchedLines,
    mismatchedLines,
    unvalidatedLines,
    isMatchEngineFailed,
  } = useMemo(() => {
    if (!comparisonData || !comparisonData.line_item_comparisons) {
      return {
        matchedLines: [],
        mismatchedLines: [],
        unvalidatedLines: [],
        isMatchEngineFailed: false,
      };
    }
    const trace = comparisonData.match_trace || [];
    const overallFailure = trace.find(
      (t) => t.status === "FAIL" && t.step === "Document Validation",
    );
    const isEngineFailed = !!overallFailure;

    const linesWithInfo: LineWithMismatchInfo[] =
      comparisonData.line_item_comparisons.map((line) => {
        let mismatchType: MismatchType = "none";
        let mismatchReason: string | null = null;
        let matchMethod: string | null = null;
        const invDesc = line.invoice_line?.description ?? "unknown_item";
        const priceFail = trace.find(
          (t) =>
            t.status === "FAIL" &&
            t.step.includes(`Item '${invDesc}'`) &&
            t.step.includes("Price Match"),
        );
        const qtyFail = trace.find(
          (t) =>
            t.status === "FAIL" &&
            t.step.includes(`Item '${invDesc}'`) &&
            t.step.includes("Quantity Match"),
        );
        const itemMatchFail = trace.find(
          (t) =>
            t.status === "FAIL" &&
            t.step.includes(`Item '${invDesc}'`) &&
            t.step.includes("PO Item Match"),
        );
        const poMatchStep = trace.find(
          (t) =>
            t.status === "PASS" &&
            t.step.includes(`Item '${invDesc}'`) &&
            t.step.includes("PO Item Match"),
        );
        if (poMatchStep) {
          matchMethod = poMatchStep.message;
        }
        if (itemMatchFail) {
          mismatchType = "unmatched";
          mismatchReason = itemMatchFail.message;
        } else if (priceFail && qtyFail) {
          mismatchType = "both";
          mismatchReason = "Price & Quantity mismatch";
        } else if (priceFail) {
          mismatchType = "price";
          mismatchReason = priceFail.message;
        } else if (qtyFail) {
          if (qtyFail.details?.grn_total_qty === 0) {
            mismatchType = "pending_receipt";
          } else {
            mismatchType = "quantity";
          }
          mismatchReason = qtyFail.message;
        }
        return { ...line, mismatchType, mismatchReason, matchMethod };
      });

    const filteredLines = linesWithInfo.filter((line) =>
      (line.invoice_line?.description ?? "")
        .toLowerCase()
        .includes(lineItemSearch.toLowerCase()),
    );
    if (isEngineFailed) {
      return {
        matchedLines: [],
        mismatchedLines: [],
        unvalidatedLines: filteredLines,
        isMatchEngineFailed: true,
      };
    }
    return {
      matchedLines: filteredLines.filter(
        (line) => line.mismatchType === "none",
      ),
      mismatchedLines: filteredLines.filter(
        (line) => line.mismatchType !== "none",
      ),
      unvalidatedLines: [],
      isMatchEngineFailed: false,
    };
  }, [comparisonData, lineItemSearch]);

  const handleFieldChange = (
    poDbId: number | null | undefined,
    description: string | null | undefined,
    field: "ordered_qty" | "unit_price",
    value: string,
  ) => {
    if (poDbId == null || description == null) return;
    const fieldKey = `${poDbId}-${description}`;
    setEditableFields((prev) => ({
      ...prev,
      [fieldKey]: { ...prev[fieldKey], [field]: parseFloat(value) || 0 },
    }));
  };

  const handleSaveChanges = async () => {
    if (Object.keys(editableFields).length === 0) return;
    setIsSaving(true);
    try {
      const changesByPoId: Record<
        number,
        {
          line_items: Array<{
            description: string;
            ordered_qty?: number;
            unit_price?: number;
          }>;
        }
      > = {};
      Object.entries(editableFields).forEach(([key, changes]) => {
        const dashIndex = key.indexOf("-");
        const poDbIdStr = key.substring(0, dashIndex);
        const description = key.substring(dashIndex + 1);
        const poDbId = parseInt(poDbIdStr, 10);
        if (!changesByPoId[poDbId]) {
          changesByPoId[poDbId] = { line_items: [] };
        }
        const originalPoLine = comparisonData.line_item_comparisons.find(
          (l) =>
            l.po_line?.po_db_id === poDbId &&
            l.po_line.description === description,
        )?.po_line;
        const completeChanges = {
          description,
          ordered_qty:
            changes.ordered_qty ?? (originalPoLine?.ordered_qty || undefined),
          unit_price:
            changes.unit_price ?? (originalPoLine?.unit_price || undefined),
        };
        changesByPoId[poDbId].line_items.push(completeChanges);
      });
      const updatePromises = Object.entries(changesByPoId).map(
        async ([poDbIdStr, payload]) => {
          const poDbId = parseInt(poDbIdStr, 10);
          return updatePurchaseOrder(poDbId, { changes: payload, version: 1 });
        },
      );
      await Promise.all(updatePromises);
      toast.success(
        "PO changes saved successfully! Re-matching in background.",
      );
      setEditableFields({});
      onUpdate();
    } catch (error) {
      toast.error(
        `Failed to save PO changes: ${error instanceof Error ? error.message : "Check console"}`,
      );
    } finally {
      setIsSaving(false);
    }
  };

  const hasChanges = Object.keys(editableFields).length > 0;

  const renderTableRows = (lines: LineWithMismatchInfo[]) => {
    return lines.map((line, index) => {
      const {
        invoice_line: invLine,
        po_line: poLine,
        mismatchType,
        mismatchReason,
        matchMethod,
      } = line;
      if (!invLine) return null;

      const key = poLine
        ? `${poLine.po_db_id}-${poLine.description}`
        : `no-po-${index}`;
      let rowClass = "bg-white";
      if (mismatchType === "none") rowClass = "bg-green-50/50";
      if (["price", "quantity", "both"].includes(mismatchType))
        rowClass = "bg-orange-50/30";
      if (mismatchType === "unmatched") rowClass = "bg-red-50/30";
      if (mismatchType === "pending_receipt") rowClass = "bg-blue-50/50";

      // --- START MODIFICATION: Graceful handling of null/undefined prices and quantities ---
      const poQty = poLine?.ordered_qty;
      const poPrice = poLine?.unit_price;
      const invPrice = invLine?.unit_price;
      const lineTotal = invLine?.line_total;

      const poQtyDisplay = poQty != null ? poQty : "N/A";
      const poPriceDisplay =
        poPrice != null && typeof poPrice === "number"
          ? `$${poPrice.toFixed(2)}`
          : "N/A";
      const invPriceDisplay =
        invPrice != null && typeof invPrice === "number"
          ? `$${invPrice.toFixed(2)}`
          : "N/A";
      const lineTotalDisplay =
        lineTotal != null && typeof lineTotal === "number"
          ? `$${lineTotal.toFixed(2)}`
          : "N/A";
      // --- END MODIFICATION ---

      return (
        <TableRow key={`${key}-${index}`} className={cn("align-top", rowClass)}>
          <TableCell>
            <div className="flex items-start justify-between">
              <div>
                <p className="font-medium truncate">
                  {invLine.description ?? "N/A"}
                </p>
                <p className="text-xs text-gray-500">
                  PO: {line.po_number || "N/A"}
                </p>
                {matchMethod && (
                  <div className="text-xs text-green-700 font-semibold flex items-center gap-1.5 pt-1">
                    <Check className="w-4 h-4" />
                    <span>{matchMethod}</span>
                  </div>
                )}
              </div>
              <button
                onClick={() => setInspectingLine(invLine)}
                title="View extracted metadata"
              >
                <Info className="h-4 w-4 text-gray-400 hover:text-blue-primary cursor-pointer flex-shrink-0" />
              </button>
            </div>
            <StatusReason type={mismatchType} reason={mismatchReason} />
          </TableCell>
          <MismatchCell
            isMismatch={mismatchType === "quantity" || mismatchType === "both"}
          >
            <p>{invLine.quantity ?? "–"}</p>
            <p className="text-xs text-gray-500">{invLine.unit}</p>
          </MismatchCell>
          <TableCell className="text-center font-medium py-2 px-3 align-top">
            {poLine && poLine.po_db_id && poLine.description ? (
              <div>
                {editableFields[`${poLine.po_db_id}-${poLine.description}`]
                  ?.ordered_qty !== undefined ? (
                  <Input
                    type="number"
                    value={
                      editableFields[`${poLine.po_db_id}-${poLine.description}`]
                        .ordered_qty || 0
                    }
                    onChange={(e) =>
                      handleFieldChange(
                        poLine.po_db_id,
                        poLine.description,
                        "ordered_qty",
                        e.target.value,
                      )
                    }
                    className="w-20 text-center"
                  />
                ) : (
                  <button
                    onClick={() =>
                      handleFieldChange(
                        poLine.po_db_id,
                        poLine.description,
                        "ordered_qty",
                        poQty != null ? poQty.toString() : "0",
                      )
                    }
                    className="hover:bg-gray-100 px-2 py-1 rounded text-blue-600 hover:text-blue-800"
                  >
                    {poQtyDisplay}
                  </button>
                )}
                <p className="text-xs text-gray-500">{poLine.unit}</p>
              </div>
            ) : (
              <p>N/A</p>
            )}
          </TableCell>
          <MismatchCell
            isMismatch={mismatchType === "price" || mismatchType === "both"}
          >
            <p>{invPriceDisplay}</p>
          </MismatchCell>
          <TableCell className="text-right font-medium py-2 px-3 align-top">
            {poLine && poLine.po_db_id && poLine.description ? (
              <div>
                {editableFields[`${poLine.po_db_id}-${poLine.description}`]
                  ?.unit_price !== undefined ? (
                  <Input
                    type="number"
                    step="0.01"
                    value={
                      editableFields[`${poLine.po_db_id}-${poLine.description}`]
                        .unit_price || 0
                    }
                    onChange={(e) =>
                      handleFieldChange(
                        poLine.po_db_id,
                        poLine.description,
                        "unit_price",
                        e.target.value,
                      )
                    }
                    className="w-24 text-right"
                  />
                ) : (
                  <button
                    onClick={() =>
                      handleFieldChange(
                        poLine.po_db_id,
                        poLine.description,
                        "unit_price",
                        poPrice != null ? poPrice.toString() : "0",
                      )
                    }
                    className="hover:bg-gray-100 px-2 py-1 rounded text-blue-600 hover:text-blue-800"
                  >
                    {poPriceDisplay}
                  </button>
                )}
              </div>
            ) : (
              <p>N/A</p>
            )}
          </TableCell>
          <TableCell className="text-right font-bold py-2 px-3 align-top">
            {lineTotalDisplay}
          </TableCell>
        </TableRow>
      );
    });
  };

  if (
    !comparisonData.line_item_comparisons ||
    comparisonData.line_item_comparisons.length === 0
  ) {
    return (
      <div className="p-4 text-center text-gray-500 border rounded-lg bg-gray-50">
        <p className="font-medium">No line items extracted</p>
      </div>
    );
  }

  return (
    <>
      <div>
        <div className="flex justify-between items-center mb-2">
          <h3 className="text-lg font-semibold text-black">
            {isMatchEngineFailed
              ? "Line Items Pending Validation"
              : "Line Item Details"}
          </h3>
          {hasChanges && (
            <Button onClick={handleSaveChanges} disabled={isSaving} size="sm">
              {isSaving ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Save className="w-4 h-4 mr-2" />
              )}
              Save PO Changes
            </Button>
          )}
        </div>
        <div className="relative mb-2">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
          <Input
            placeholder="Search line items..."
            value={lineItemSearch}
            onChange={(e) => setLineItemSearch(e.target.value)}
            className="pl-10"
          />
        </div>
        <div className="border rounded-lg overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-2/5">Description / PO</TableHead>
                <TableHead className="text-center">Inv Qty</TableHead>
                <TableHead className="text-center">PO Qty</TableHead>
                <TableHead className="text-right">Inv Price</TableHead>
                <TableHead className="text-right">PO Price</TableHead>
                <TableHead className="text-right">Line Total</TableHead>
              </TableRow>
            </TableHeader>
            {isMatchEngineFailed ? (
              <TableBody>{renderTableRows(unvalidatedLines)}</TableBody>
            ) : (
              <>
                {mismatchedLines.length > 0 && (
                  <TableBody>{renderTableRows(mismatchedLines)}</TableBody>
                )}
                {matchedLines.length > 0 && (
                  <TableBody>
                    <TableRow>
                      <TableCell colSpan={6} className="p-0">
                        <div className="w-full">
                          <button
                            onClick={() =>
                              setIsMatchedSectionOpen((prev) => !prev)
                            }
                            className="w-full p-2 cursor-pointer flex items-center gap-2 font-semibold text-sm text-green-700 bg-green-50 hover:bg-green-100 transition-colors"
                          >
                            <ChevronDown
                              className={cn(
                                "w-4 h-4 transition-transform",
                                isMatchedSectionOpen && "rotate-180",
                              )}
                            />
                            {matchedLines.length} Matched Line Item(s)
                            <CheckCircle2 className="w-4 h-4" />
                          </button>
                          {isMatchedSectionOpen && (
                            <Table>
                              <TableBody>
                                {renderTableRows(matchedLines)}
                              </TableBody>
                            </Table>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  </TableBody>
                )}
              </>
            )}
            {!isMatchEngineFailed &&
              mismatchedLines.length === 0 &&
              matchedLines.length === 0 && (
                <TableBody>
                  <TableRow>
                    <TableCell
                      colSpan={6}
                      className="text-center h-24 text-gray-500"
                    >
                      No line items found or matching your search.
                    </TableCell>
                  </TableRow>
                </TableBody>
              )}
          </Table>
        </div>
      </div>
      <MetadataModal
        isOpen={!!inspectingLine}
        onClose={() => setInspectingLine(null)}
        data={inspectingLine}
      />
    </>
  );
};

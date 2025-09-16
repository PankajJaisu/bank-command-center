"use client";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/Table";

// Define a flexible type for our document data
type DocumentData = {
  [key: string]: unknown;
  line_items?: Record<string, unknown>[] | null;
};

interface StructuredDataViewerProps {
  documentType: "PO" | "GRN";
  data: DocumentData[]; // Now accepts an array of documents
}

const InfoField = ({ label, value }: { label: string; value: unknown }) => {
  if (!value) return null;
  return (
    <div>
      <p className="text-xs text-gray-500">{label}</p>
      <p className="font-medium text-black">{String(value)}</p>
    </div>
  );
};

export const StructuredDataViewer = ({
  documentType,
  data,
}: StructuredDataViewerProps) => {
  if (!data || data.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500">
        No data available for this document type.
      </div>
    );
  }

  const headers =
    documentType === "PO"
      ? ["Description", "SKU", "Ordered Qty", "Unit", "Unit Price", "Total"]
      : ["Description", "SKU", "Received Qty", "Unit"];

  return (
    <div className="h-full flex-grow overflow-y-auto p-4 bg-gray-200">
      <div className="bg-white p-4 rounded-lg border space-y-6">
        {data.map((doc, docIndex) => (
          <div key={docIndex}>
            {/* Document Header */}
            <h3 className="text-xl font-bold mb-4 text-purple-accent border-b pb-2">
              {documentType === "PO"
                ? String(doc.po_number || `PO ${docIndex + 1}`)
                : String(doc.grn_number || `GRN ${docIndex + 1}`)}
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <InfoField label="Vendor" value={doc.vendor_name} />
              <InfoField
                label={documentType === "PO" ? "Order Date" : "Received Date"}
                value={doc.order_date || doc.received_date}
              />
              {documentType === "PO" && (
                <InfoField label="Buyer" value={doc.buyer_name} />
              )}
              {documentType === "PO" && (
                <InfoField
                  label="Grand Total"
                  value={
                    doc.po_grand_total && typeof doc.po_grand_total === "number"
                      ? `$${doc.po_grand_total.toFixed(2)}`
                      : "N/A"
                  }
                />
              )}
            </div>

            {/* Line Items Table */}
            <h4 className="font-semibold mb-2">Line Items</h4>
            <div className="border rounded-lg overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow>
                    {headers.map((h) => (
                      <TableHead key={h}>{h}</TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(doc.line_items || []).map((item, itemIndex) => {
                    const unitPrice =
                      typeof item.unit_price === "number" ? item.unit_price : 0;
                    const orderedQty =
                      typeof item.ordered_qty === "number"
                        ? item.ordered_qty
                        : 0;
                    const receivedQty =
                      typeof item.received_qty === "number"
                        ? item.received_qty
                        : 0;

                    return (
                      <TableRow key={itemIndex}>
                        <TableCell>
                          {String(item.description || "N/A")}
                        </TableCell>
                        <TableCell>{String(item.sku || "N/A")}</TableCell>
                        <TableCell>
                          {documentType === "PO"
                            ? orderedQty || "N/A"
                            : receivedQty || "N/A"}
                        </TableCell>
                        <TableCell>{String(item.unit || "N/A")}</TableCell>
                        {documentType === "PO" && (
                          <TableCell>${unitPrice.toFixed(2)}</TableCell>
                        )}
                        {documentType === "PO" && (
                          <TableCell className="font-semibold">
                            ${(orderedQty * unitPrice).toFixed(2)}
                          </TableCell>
                        )}
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

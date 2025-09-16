"use client";

import { type InvoiceHeaderData } from "@/lib/api";
import { ChevronDown, Info, Database } from "lucide-react";
import { MetadataModal } from "./MetadataModal";
import { useState } from "react";

// Helper component to render a single field
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const DetailField = ({ label, value }: { label: string; value: any }) => {
  if (value === null || value === undefined || value === "") return null;
  return (
    <div className="py-2">
      <dt className="text-sm font-medium text-gray-500 capitalize">
        {label.replace(/_/g, " ")}
      </dt>
      <dd className="mt-1 text-sm text-gray-900 whitespace-pre-wrap">
        {String(value)}
      </dd>
    </div>
  );
};

export const InvoiceHeaderDetails = ({
  headerData,
  invoiceMetadata,
}: {
  headerData: InvoiceHeaderData | null;
  invoiceMetadata?: object | null;
}) => {
  const [isMetadataOpen, setIsMetadataOpen] = useState(false);

  if (!headerData) return null;

  const { other_header_fields, ...standardDetails } = headerData;
  const allDetails = { ...standardDetails, ...(other_header_fields || {}) };

  const hasDetails = Object.values(allDetails).some(
    (v) => v !== null && v !== "",
  );

  if (
    !hasDetails &&
    (!invoiceMetadata || Object.keys(invoiceMetadata).length === 0)
  ) {
    return (
      <div className="p-4 bg-gray-50 rounded-lg text-sm text-gray-600 flex items-center gap-2">
        <Info className="w-4 h-4" />
        No header details or metadata were extracted for this invoice.
      </div>
    );
  }

  return (
    <>
      <details className="group border rounded-lg overflow-hidden" open>
        <summary className="flex items-center justify-between p-4 cursor-pointer bg-white hover:bg-gray-50">
          <h3 className="text-lg font-semibold text-black">
            Invoice Header Details
          </h3>
          <div className="flex items-center gap-2">
            {/* --- NEW METADATA BUTTON --- */}
            {invoiceMetadata && Object.keys(invoiceMetadata).length > 0 && (
              <button
                onClick={(e) => {
                  e.preventDefault(); // Prevent the details section from toggling
                  setIsMetadataOpen(true);
                }}
                className="flex items-center gap-1 text-xs font-semibold text-blue-primary bg-blue-50 hover:bg-blue-100 px-2 py-1 rounded-md"
              >
                <Database className="w-3 h-3" />
                View Raw Metadata
              </button>
            )}
            <ChevronDown className="w-5 h-5 text-gray-500 transition-transform duration-200 group-open:rotate-180" />
          </div>
        </summary>
        <div className="p-4 bg-white border-t">
          {hasDetails ? (
            <dl className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-x-4 gap-y-2">
              {Object.entries(allDetails).map(([key, value]) => (
                <DetailField key={key} label={key} value={value} />
              ))}
            </dl>
          ) : (
            <div className="text-sm text-gray-600 flex items-center gap-2">
              <Info className="w-4 h-4" />
              No structured header details available, but you can view raw
              metadata above.
            </div>
          )}
        </div>
      </details>

      {/* --- METADATA MODAL INSTANCE --- */}
      <MetadataModal
        isOpen={isMetadataOpen}
        onClose={() => setIsMetadataOpen(false)}
        data={invoiceMetadata || null}
        title="Invoice Header Metadata"
      />
    </>
  );
};

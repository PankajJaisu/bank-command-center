"use client";

import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { Copy, Check } from "lucide-react";
import { useState } from "react";
import toast from "react-hot-toast";

interface MetadataModalProps {
  isOpen: boolean;
  onClose: () => void;
  data: object | null;
  title?: string;
}

export const MetadataModal = ({
  isOpen,
  onClose,
  data,
  title = "Extracted Line Item Metadata",
}: MetadataModalProps) => {
  const [hasCopied, setHasCopied] = useState(false);

  if (!isOpen || !data) return null;

  const jsonData = JSON.stringify(data, null, 2);

  const handleCopy = () => {
    navigator.clipboard.writeText(jsonData);
    setHasCopied(true);
    toast.success("Raw data copied to clipboard!");
    setTimeout(() => setHasCopied(false), 2000);
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title}>
      <div className="relative">
        <div className="bg-gray-50 p-4 rounded-md border text-sm max-h-[60vh] overflow-y-auto">
          {/* --- RENDER AS TABLE INSTEAD OF PRE --- */}
          <table className="w-full">
            <tbody>
              {Object.entries(data).map(([key, value]) => (
                <tr key={key} className="border-b last:border-b-0">
                  <td className="py-2 pr-4 font-semibold text-gray-600 align-top">
                    {key}
                  </td>
                  <td className="py-2 text-gray-800 font-mono break-all">
                    {JSON.stringify(value, null, 2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {/* --- END: RENDER AS TABLE --- */}
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="absolute top-2 right-2 p-1 h-auto text-gray-500 hover:bg-gray-200"
          onClick={handleCopy}
          title="Copy JSON"
        >
          {hasCopied ? (
            <Check className="w-4 h-4 text-green-success" />
          ) : (
            <Copy className="w-4 h-4" />
          )}
        </Button>
      </div>
    </Modal>
  );
};

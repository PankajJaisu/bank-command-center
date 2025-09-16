"use client";

import { type JobResult } from "@/lib/api";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import Link from "next/link";
import {
  CheckCircle,
  XCircle,
  Eye,
  FileText,
  FileJson,
  FileSpreadsheet,
  Database,
} from "lucide-react";

interface UploadStatusListProps {
  results: JobResult[];
}

const getIconForDocType = (docType?: string | null) => {
  switch (docType) {
    case "Invoice":
      return <FileText className="w-4 h-4 text-blue-500" />;
    case "PurchaseOrder":
      return <FileJson className="w-4 h-4 text-green-500" />;
    case "GoodsReceiptNote":
      return <FileSpreadsheet className="w-4 h-4 text-orange-500" />;
    case "StructuredData":
      return <Database className="w-4 h-4 text-purple-500" />;
    default:
      return <FileText className="w-4 h-4 text-gray-500" />;
  }
};

export const UploadStatusList = ({ results }: UploadStatusListProps) => {
  if (!results || results.length === 0) {
    return (
      <p className="text-center text-gray-medium">
        No processing results available.
      </p>
    );
  }

  return (
    <div className="mt-6 space-y-4">
      <h3 className="font-semibold text-lg">Processing Results</h3>
      <div className="border rounded-lg max-h-96 overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Filename</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Details</TableHead>
              <TableHead className="text-right">Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {results.map((result, index) => (
              <TableRow key={`${result.filename}-${index}`}>
                <TableCell className="font-medium">
                  <div className="flex items-center gap-2">
                    {getIconForDocType(result.document_type)}
                    <span>{result.filename}</span>
                  </div>
                </TableCell>
                <TableCell>
                  <Badge
                    variant={
                      result.status === "success" ? "success" : "destructive"
                    }
                  >
                    {result.status === "success" ? (
                      <CheckCircle className="mr-2 h-4 w-4" />
                    ) : (
                      <XCircle className="mr-2 h-4 w-4" />
                    )}
                    {result.status}
                  </Badge>
                </TableCell>
                <TableCell className="text-sm text-gray-medium">
                  {result.message}
                </TableCell>
                <TableCell className="text-right">
                  {result.status === "success" &&
                    result.document_type === "Invoice" &&
                    result.extracted_id && (
                      <Link
                        href={`/resolution-workbench?invoiceId=${result.extracted_id}`}
                      >
                        <Button variant="ghost" size="sm">
                          <Eye className="mr-2 h-4 w-4" /> View
                        </Button>
                      </Link>
                    )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
};

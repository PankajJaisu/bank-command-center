"use client";

import ReactMarkdown from "react-markdown";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "../ui/Card";
import { Button } from "../ui/Button";
import Link from "next/link";
import { ArrowRight, Eye, FileText, CheckCircle } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../ui/Table";
import { Badge } from "../ui/Badge";
import { type InvoiceSummary } from "@/lib/api";
import { useAppContext } from "@/lib/AppContext";

// --- Type definitions and Type Guards ---

interface KpiData {
  operational_efficiency?: {
    touchless_invoice_rate_percent?: number;
    invoices_in_review_queue?: number;
    avg_exception_handling_time_hours?: number;
  };
  financial_optimization?: { discounts_captured?: string };
}
interface DossierData {
  summary: { invoice_id: string; vendor_name: string; grand_total: number };
  exceptions?: Array<{ message: string }>;
}
interface EmailDraftData {
  draft_email: string;
}
interface GeneratedFileData {
  generated_file_path: string;
}

function isInvoiceArray(data: unknown): data is InvoiceSummary[] {
  return (
    Array.isArray(data) &&
    (data.length === 0 ||
      (typeof data[0] === "object" &&
        data[0] !== null &&
        "invoice_id" in data[0]))
  );
}
function isKpiData(data: unknown): data is KpiData {
  return (
    typeof data === "object" &&
    data !== null &&
    "operational_efficiency" in data
  );
}
function isDossierData(data: unknown): data is DossierData {
  return typeof data === "object" && data !== null && "summary" in data;
}
function isEmailDraftData(data: unknown): data is EmailDraftData {
  return typeof data === "object" && data !== null && "draft_email" in data;
}
function isGeneratedFileData(data: unknown): data is GeneratedFileData {
  return (
    typeof data === "object" && data !== null && "generated_file_path" in data
  );
}

// --- Sub-components for rendering specific data types ---

const InvoiceTable = ({ invoices }: { invoices: InvoiceSummary[] }) => {
  const { closeChat } = useAppContext();
  if (!invoices || invoices.length === 0) {
    return (
      <p className="text-sm text-gray-medium mt-2">
        No invoices found matching the criteria.
      </p>
    );
  }
  return (
    <Card className="mt-4 bg-white/50">
      <CardContent className="p-0">
        <div className="max-h-60 overflow-y-auto">
          <Table>
            <TableHeader className="sticky top-0 bg-white z-10">
              <TableRow>
                <TableHead>Invoice ID</TableHead>
                <TableHead>Vendor</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {invoices.map((inv) => (
                <TableRow key={inv.id}>
                  <TableCell className="font-medium">
                    {inv.invoice_id}
                  </TableCell>
                  <TableCell>{inv.vendor_name}</TableCell>
                  <TableCell>
                    <Badge
                      variant={
                        inv.status.includes("review") ? "warning" : "success"
                      }
                    >
                      {inv.status.replace(/_/g, " ")}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <Link
                      href={`/resolution-workbench?invoiceId=${inv.invoice_id}`}
                      passHref
                    >
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-auto p-1"
                        onClick={closeChat}
                      >
                        <Eye className="w-4 h-4" />
                      </Button>
                    </Link>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
};

const KpiCard = ({ kpis }: { kpis: KpiData }) => (
  <Card className="mt-4 bg-white/50">
    <CardHeader className="pb-2">
      <CardTitle className="text-lg">System KPIs</CardTitle>
    </CardHeader>
    <CardContent className="grid grid-cols-2 gap-3 text-sm">
      <div className="flex flex-col p-2 bg-gray-50 rounded-lg border">
        <span className="text-gray-500 text-xs">Touchless Rate</span>
        <span className="text-green-success font-bold text-xl">
          {kpis.operational_efficiency?.touchless_invoice_rate_percent}%
        </span>
      </div>
      <div className="flex flex-col p-2 bg-gray-50 rounded-lg border">
        <span className="text-gray-500 text-xs">Discounts Captured</span>
        <span className="text-green-success font-bold text-xl">
          {kpis.financial_optimization?.discounts_captured}
        </span>
      </div>
      <div className="flex flex-col p-2 bg-gray-50 rounded-lg border">
        <span className="text-gray-500 text-xs">In Review</span>
        <span className="text-orange-warning font-bold text-xl">
          {kpis.operational_efficiency?.invoices_in_review_queue}
        </span>
      </div>
      <div className="flex flex-col p-2 bg-gray-50 rounded-lg border">
        <span className="text-gray-500 text-xs">Avg. Handling Time</span>
        <span className="text-blue-primary font-bold text-xl">
          {kpis.operational_efficiency?.avg_exception_handling_time_hours} hrs
        </span>
      </div>
    </CardContent>
  </Card>
);

const GeneratedFileCard = ({ path }: { path: string }) => (
  <Card className="mt-4 bg-green-success/10 border-l-4 border-green-success">
    <CardContent className="p-3 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <FileText className="w-5 h-5 text-green-success" />
        <div>
          <p className="font-semibold text-green-success">File Generated</p>
          <p className="text-xs font-mono text-gray-600">
            {path.split("/").pop()}
          </p>
        </div>
      </div>
      <Button size="sm" variant="ghost">
        Download
      </Button>
    </CardContent>
  </Card>
);

const DossierCard = ({ data }: { data: DossierData }) => {
  const { closeChat } = useAppContext();
  const { summary, exceptions } = data;
  return (
    <Card className="mt-4 bg-white/50">
      <CardHeader className="pb-4">
        <CardTitle className="text-base">{summary.invoice_id}</CardTitle>
        <CardDescription>
          From: {summary.vendor_name} - Total: ${summary.grand_total.toFixed(2)}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {exceptions && exceptions.length > 0 && (
          <div className="mb-4">
            <p className="font-semibold text-xs mb-1 text-orange-warning">
              Issues Found:
            </p>
            <ul className="list-disc list-inside text-xs space-y-1">
              {exceptions.map((ex, i: number) => (
                <li key={i}>{ex.message}</li>
              ))}
            </ul>
          </div>
        )}
        <Link
          href={`/resolution-workbench?invoiceId=${summary.invoice_id}`}
          className="block"
        >
          <Button variant="secondary" className="w-full" onClick={closeChat}>
            Go to Resolution Workbench <ArrowRight className="ml-2 w-4 h-4" />
          </Button>
        </Link>
      </CardContent>
    </Card>
  );
};

// --- Main Renderer Component ---

interface BotMessageRendererProps {
  content: string;
  uiAction?: string;
  data?: unknown;
}

export const BotMessageRenderer = ({
  content,
  uiAction,
  data,
}: BotMessageRendererProps) => {
  const renderDataComponent = () => {
    if (!data) return null;

    if (isInvoiceArray(data)) {
      return <InvoiceTable invoices={data} />;
    }
    if (isKpiData(data)) {
      return <KpiCard kpis={data} />;
    }
    if (isDossierData(data)) {
      return <DossierCard data={data} />;
    }
    if (isEmailDraftData(data)) {
      return (
        <Card className="mt-4 bg-white/50">
          <CardContent className="p-4">
            <div className="prose prose-sm max-w-none text-gray-dark bg-gray-50 p-3 rounded-lg border">
              <ReactMarkdown>{data.draft_email}</ReactMarkdown>
            </div>
          </CardContent>
        </Card>
      );
    }
    if (isGeneratedFileData(data)) {
      return <GeneratedFileCard path={data.generated_file_path} />;
    }
    // General success message for actions that don't have a specific UI component
    if (uiAction === "SHOW_TOAST_SUCCESS") {
      return (
        <div className="mt-2 flex items-center gap-2 text-sm text-green-success">
          <CheckCircle className="w-4 h-4" />
          <span>Action completed successfully.</span>
        </div>
      );
    }
    // Fallback for any other data shape that should be loaded
    if (uiAction === "LOAD_DATA") {
      return (
        <pre className="text-xs bg-gray-900 text-white p-2 rounded-md mt-2 overflow-x-auto">
          {JSON.stringify(data, null, 2)}
        </pre>
      );
    }

    return null;
  };

  return (
    <div>
      <div className="prose prose-sm max-w-none prose-p:my-1">
        <ReactMarkdown>{content}</ReactMarkdown>
      </div>
      {renderDataComponent()}
    </div>
  );
};

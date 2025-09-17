"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { CollectionWorkbench } from "@/components/workbench/CollectionWorkbench";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/Table";
import {
  ArrowRight,
  Bot,
  Loader2,
  CheckCircle,
} from "lucide-react";
import { getWorkbenchCases, type WorkbenchCase } from "@/lib/collection-api";
import toast from "react-hot-toast";

function WorkbenchContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [selectedCustomerNo, setSelectedCustomerNo] = useState<string | null>(searchParams?.get("customerNo") || null);
  const [workbenchItems, setWorkbenchItems] = useState<WorkbenchCase[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchCases = async () => {
    setIsLoading(true);
    try {
      const cases = await getWorkbenchCases();
      setWorkbenchItems(cases);
    } catch (error) {
      toast.error("Failed to load workbench queue.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCases();
  }, []);
  
  const handleSelectCase = (customerNo: string) => {
    setSelectedCustomerNo(customerNo);
    // Update URL for bookmarking/sharing
    router.push(`/resolution-workbench?customerNo=${customerNo}`, { scroll: false });
  };
  
  const handleCloseDetail = () => {
    setSelectedCustomerNo(null);
    router.push('/resolution-workbench', { scroll: false });
    fetchCases(); // Refresh the list in case the item was processed
  };

  const getRiskBadgeColor = (riskLevel?: string | null) => {
    switch (riskLevel?.toLowerCase()) {
      case "high": return "bg-red-100 text-red-800";
      case "medium": return "bg-yellow-100 text-yellow-800";
      default: return "bg-gray-100 text-gray-800";
    }
  };

  // If a customer is selected, render the detailed workbench view
  if (selectedCustomerNo) {
    return (
      <CollectionWorkbench
        customerNo={selectedCustomerNo}
        onClose={handleCloseDetail}
      />
    );
  }

  // Otherwise, render the queue
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Resolution Workbench Queue</CardTitle>
          <CardDescription>
            Prioritized list of customer accounts requiring manual collection activities.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center items-center py-10">
              <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            </div>
          ) : workbenchItems.length === 0 ? (
            <div className="text-center py-10 text-gray-500">
                <CheckCircle className="h-12 w-12 mx-auto mb-2 text-green-500" />
                <p className="font-semibold">Queue is clear!</p>
                <p>No accounts are currently flagged for manual review.</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Customer</TableHead>
                  <TableHead>Segment</TableHead>
                  <TableHead>Risk Level</TableHead>
                  <TableHead>Outstanding</TableHead>
                  <TableHead>AI Suggested Action</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {workbenchItems.map((item) => (
                  <TableRow key={item.id} className="hover:bg-gray-50">
                    <TableCell>
                      <div className="font-medium">{item.name}</div>
                      <div className="text-sm text-gray-500">{item.customer_no}</div>
                    </TableCell>
                    <TableCell>{item.segment}</TableCell>
                    <TableCell>
                      <Badge className={getRiskBadgeColor(item.risk_level)}>{item.risk_level}</Badge>
                    </TableCell>
                    <TableCell className="font-mono">
                      ₹{item.cbs_outstanding_amount?.toLocaleString('en-IN') ?? 'N/A'}
                    </TableCell>
                    <TableCell>
                        <div className="flex items-center gap-2">
                            <Bot className="h-4 w-4 text-blue-600 shrink-0" />
                            <span className="text-sm font-medium">{item.ai_suggested_action}</span>
                        </div>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button size="sm" onClick={() => handleSelectCase(item.customer_no)}>
                        Resolve <ArrowRight className="h-4 w-4 ml-1" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function ResolutionWorkbenchPage() {
    return (
        <Suspense fallback={<div>Loading...</div>}>
            <WorkbenchContent />
        </Suspense>
    );
}
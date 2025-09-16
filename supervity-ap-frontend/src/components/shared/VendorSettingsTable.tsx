"use client";
import React, { useState, useEffect, useCallback } from "react";
import {
  getVendorPerformanceSummary,
  updateSingleVendorSetting,
  createVendorSetting,
  type VendorPerformanceSummary,
  type VendorSettingCreate,
} from "@/lib/api";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/Table";
import { Button } from "@/components/ui/Button";
import { Pencil, PlusCircle, AlertTriangle, Loader2 } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/Card";
import { VendorPolicyModal } from "../settings/VendorPolicyModal";
import { cn } from "@/lib/utils";
import toast from "react-hot-toast";

export const VendorSettingsTable = () => {
  const [summary, setSummary] = useState<VendorPerformanceSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingPolicy, setEditingPolicy] =
    useState<VendorPerformanceSummary | null>(null);

  const fetchData = useCallback(() => {
    setIsLoading(true);
    getVendorPerformanceSummary()
      .then(setSummary)
      .finally(() => setIsLoading(false));
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleOpenAddModal = () => {
    setEditingPolicy(null);
    setIsModalOpen(true);
  };

  const handleOpenEditModal = (policy: VendorPerformanceSummary) => {
    setEditingPolicy(policy);
    setIsModalOpen(true);
  };

  const handleSavePolicy = async (
    policyData: VendorSettingCreate,
    id?: number,
  ) => {
    try {
      if (id) {
        // Editing existing policy
        await updateSingleVendorSetting(id, policyData);
        toast.success("Vendor policy updated successfully!");
      } else {
        // Creating new policy
        await createVendorSetting(policyData);
        toast.success("New vendor policy created successfully!");
      }
      setIsModalOpen(false);
      fetchData(); // Refresh the data
    } catch (error) {
      toast.error(
        `Failed to save policy: ${error instanceof Error ? error.message : "Unknown error"}`,
      );
    }
  };

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <div>
              <CardTitle>Vendor Configuration & Performance</CardTitle>
              <CardDescription>
                Manage vendor-specific settings and monitor their performance.
              </CardDescription>
            </div>
            <Button onClick={handleOpenAddModal}>
              <PlusCircle className="mr-2 h-4 w-4" /> Add Vendor
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="border rounded-lg">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Vendor</TableHead>
                  <TableHead className="text-center">Price Tol. (%)</TableHead>
                  <TableHead className="text-center">Exception Rate</TableHead>
                  <TableHead className="text-center">Total Invoices</TableHead>
                  <TableHead className="text-center">Avg. Pay Time</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center h-24">
                      <Loader2 className="w-6 h-6 animate-spin mx-auto" />
                    </TableCell>
                  </TableRow>
                ) : (
                  summary.map((s) => (
                    <TableRow key={s.id}>
                      <TableCell className="font-medium">
                        {s.vendor_name}
                      </TableCell>
                      <TableCell className="text-center">
                        {s.price_tolerance_percent?.toFixed(1) ?? "N/A"}
                      </TableCell>
                      <TableCell
                        className={cn(
                          "text-center font-semibold",
                          s.exception_rate > 20 && "text-orange-warning",
                        )}
                      >
                        {s.exception_rate > 20 && (
                          <AlertTriangle className="inline-block h-4 w-4 mr-1" />
                        )}
                        {s.exception_rate.toFixed(1)}%
                      </TableCell>
                      <TableCell className="text-center">
                        {s.total_invoices}
                      </TableCell>
                      <TableCell className="text-center">
                        {s.avg_payment_time_days !== null
                          ? `${s.avg_payment_time_days} days`
                          : "N/A"}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleOpenEditModal(s)}
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <VendorPolicyModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSave={handleSavePolicy}
        initialData={editingPolicy || undefined}
      />
    </>
  );
};

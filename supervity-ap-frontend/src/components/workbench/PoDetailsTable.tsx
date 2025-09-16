"use client";
import { type ComparisonData } from "@/lib/api";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/Table";

export const PoDetailsTable = ({
  comparisonData,
}: {
  comparisonData: ComparisonData;
}) => {
  if (!comparisonData.related_pos || comparisonData.related_pos.length === 0) {
    return null;
  }
  return (
    <div className="mt-4">
      <h4 className="font-semibold mb-2 text-black">Linked Purchase Orders</h4>
      <div className="border rounded-lg overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>PO Number</TableHead>
              <TableHead>Order Date</TableHead>
              <TableHead className="text-right">Total</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {comparisonData.related_pos.map((po) => (
              <TableRow key={po.po_number}>
                <TableCell className="font-medium">{po.po_number}</TableCell>
                <TableCell>{po.order_date}</TableCell>
                <TableCell className="text-right font-semibold">
                  {po.po_grand_total != null
                    ? `$${po.po_grand_total.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                    : "$N/A"}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
};

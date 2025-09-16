"use client";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/Card";
import { InvoiceListModal } from "./InvoiceListModal";
import { useState } from "react";
import { getInvoicesByCategory, type InvoiceSummary } from "@/lib/api";
import { Loader2 } from "lucide-react";
import toast from "react-hot-toast";

const COLORS = [
  "#FF7426",
  "#5243AA",
  "#42B883",
  "#E74C3C",
  "#F39C12",
  "#9B59B6",
];

export interface ExceptionSummaryItem {
  name: string;
  count: number;
}

interface ExceptionChartProps {
  data: ExceptionSummaryItem[];
}

export const ExceptionChart = ({ data }: ExceptionChartProps) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalCategory, setModalCategory] = useState("");
  const [modalInvoices, setModalInvoices] = useState<InvoiceSummary[]>([]);
  const [isModalLoading, setIsModalLoading] = useState(false);

  const handleBarClick = async (data: ExceptionSummaryItem) => {
    if (!data || data.count === 0) return;

    setModalCategory(data.name);
    setIsModalOpen(true);
    setIsModalLoading(true);

    try {
      const categoryKey = data.name.toLowerCase().replace(/\s+/g, "_");
      const invoices = await getInvoicesByCategory(categoryKey);
      setModalInvoices(invoices);
    } catch (error) {
      toast.error("Failed to load invoice details");
      console.error("Error loading invoices for category:", error);
    } finally {
      setIsModalLoading(false);
    }
  };

  return (
    <>
      <Card className="h-full">
        <CardHeader>
          <CardTitle>Live Exception Analysis</CardTitle>
          <CardDescription>
            Root causes of invoices currently in review. Click a bar to drill
            down.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart
              data={data}
              layout="vertical"
              margin={{ top: 5, right: 30, left: 10, bottom: 5 }}
              barSize={25}
            >
              <XAxis
                type="number"
                stroke="#888888"
                fontSize={12}
                tickLine={false}
                axisLine={false}
                allowDecimals={false}
                label={{
                  value: "Number of Invoices",
                  position: "insideBottom",
                  offset: -5,
                  fontSize: 12,
                  fill: "#6B778C",
                }}
              />
              <YAxis
                type="category"
                dataKey="name"
                stroke="#888888"
                fontSize={12}
                tickLine={false}
                axisLine={false}
                width={120}
                interval={0}
              />
              <Tooltip
                cursor={{ fill: "rgba(240, 240, 240, 0.5)" }}
                contentStyle={{
                  background: "#fff",
                  border: "1px solid #e2e8f0",
                  borderRadius: "0.5rem",
                }}
                labelStyle={{ fontWeight: "bold", color: "#0A2540" }}
                formatter={(value: number) => [value, "Invoices"]}
              />
              <Bar
                dataKey="count"
                radius={[0, 4, 4, 0]}
                className="cursor-pointer"
              >
                {data.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={COLORS[index % COLORS.length]}
                    onClick={() => handleBarClick(entry)}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <InvoiceListModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={`Invoices with Exception: ${modalCategory}`}
      >
        {isModalLoading ? (
          <div className="flex justify-center items-center h-48">
            <Loader2 className="w-8 h-8 animate-spin" />
          </div>
        ) : (
          <InvoiceListModal.Content invoices={modalInvoices} />
        )}
      </InvoiceListModal>
    </>
  );
};

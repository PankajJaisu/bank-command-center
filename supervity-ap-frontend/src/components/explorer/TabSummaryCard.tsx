"use client";

import { Card, CardContent } from "@/components/ui/Card";
import {
  DollarSign,
  FileWarning,
  HelpCircle,
  History,
  Package,
  Sigma,
  ListTodo,
} from "lucide-react";
import CountUp from "react-countup";

type SummaryData = {
  total_count: number;
  total_value: number;
  exception_breakdown?: Record<string, number>;
  average_age_days?: number;
  potential_discounts?: number;
};

interface TabSummaryCardProps {
  summary: SummaryData | null;
  isLoading: boolean;
}

const StatCard = ({
  icon: Icon,
  label,
  value,
  format,
  unit,
  colorClass,
}: {
  icon: React.ElementType;
  label: string;
  value: number;
  format?: "currency" | "decimal";
  unit?: string;
  colorClass?: string;
}) => (
  <div className="flex-1 p-4 bg-white rounded-lg border shadow-sm flex items-center gap-4">
    <div
      className={`p-3 rounded-full bg-opacity-10 ${colorClass?.replace("text-", "bg-")}`}
    >
      <Icon className={`w-6 h-6 ${colorClass}`} />
    </div>
    <div>
      <p className="text-sm text-gray-500">{label}</p>
      <p className="text-2xl font-bold text-gray-800">
        <CountUp
          end={value}
          duration={1.5}
          separator=","
          prefix={format === "currency" ? "$" : ""}
          decimals={format === "currency" ? 2 : Number.isInteger(value) ? 0 : 1}
        />
        {unit && <span className="text-lg ml-1">{unit}</span>}
      </p>
    </div>
  </div>
);

export const TabSummaryCard = ({ summary, isLoading }: TabSummaryCardProps) => {
  if (isLoading) {
    return (
      <Card className="mb-4">
        <CardContent className="p-4">
          <div className="h-24 bg-gray-200 rounded-lg animate-pulse"></div>
        </CardContent>
      </Card>
    );
  }

  if (!summary) return null;

  return (
    <Card className="mb-6 bg-gray-50/70">
      <CardContent className="p-4">
        <div className="flex flex-wrap gap-4">
          <StatCard
            icon={ListTodo}
            label="Total Invoices"
            value={summary.total_count}
            colorClass="text-blue-primary"
          />
          <StatCard
            icon={Sigma}
            label="Total Value"
            value={summary.total_value}
            format="currency"
            colorClass="text-purple-accent"
          />

          {summary.average_age_days !== undefined && (
            <StatCard
              icon={History}
              label="Average Age"
              value={summary.average_age_days}
              unit="days"
              colorClass="text-cyan-accent"
            />
          )}

          {summary.potential_discounts !== undefined &&
            summary.potential_discounts > 0 && (
              <StatCard
                icon={DollarSign}
                label="Potential Discounts"
                value={summary.potential_discounts}
                format="currency"
                colorClass="text-green-success"
              />
            )}

          {summary.exception_breakdown &&
            Object.entries(summary.exception_breakdown).map(([key, value]) => {
              let Icon = Package;
              if (key === "missing_document") Icon = FileWarning;
              if (key === "policy_violation") Icon = HelpCircle;

              return (
                <StatCard
                  key={key}
                  icon={Icon}
                  label={key
                    .replace(/_/g, " ")
                    .replace(/\b\w/g, (l) => l.toUpperCase())}
                  value={value}
                  colorClass="text-orange-warning"
                />
              );
            })}
        </div>
      </CardContent>
    </Card>
  );
};

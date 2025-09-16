"use client";
import { type CostRoiMetrics } from "@/lib/api";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/Card";
import { ArrowDown, ArrowUp, Zap, Cpu } from "lucide-react";
import CountUp from "react-countup";

const Metric = ({
  label,
  value,
  icon: Icon,
  colorClass,
  isCurrency = true,
}: {
  label: string;
  value: number;
  icon: React.ElementType;
  colorClass?: string;
  isCurrency?: boolean;
}) => (
  <div className="flex justify-between items-center text-sm py-2 border-b last:border-b-0">
    <div className="flex items-center gap-2 text-gray-500">
      <Icon className="w-4 h-4" />
      <span>{label}</span>
    </div>
    <span className={`font-semibold ${colorClass}`}>
      <CountUp
        start={0}
        end={value}
        duration={1.5}
        separator=","
        decimals={2}
        prefix={isCurrency ? "$" : ""}
      />
    </span>
  </div>
);

export const CostRoiCard = ({ data }: { data: CostRoiMetrics }) => {
  const netValue = data.total_return_for_period - data.total_cost_for_period;
  const timeSavedValue = data.total_return_for_period; // Assuming total return is mostly time saved for this example

  return (
    <Card className="h-full flex flex-col">
      <CardHeader>
        <CardTitle>Value Generation</CardTitle>
        <CardDescription>
          Estimated value generated for the selected period.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col flex-grow">
        <div className="flex-grow flex justify-center items-center my-4">
          <div
            className={`flex items-center text-4xl font-bold ${netValue >= 0 ? "text-green-success" : "text-pink-destructive"}`}
          >
            {netValue >= 0 ? (
              <ArrowUp className="h-8 w-8 mr-2" />
            ) : (
              <ArrowDown className="h-8 w-8 mr-2" />
            )}
            <CountUp
              start={0}
              end={netValue}
              duration={2}
              separator=","
              decimals={2}
              prefix="$"
            />
          </div>
        </div>
        <div className="space-y-1 mt-auto">
          <Metric
            label="Time & Efficiency Savings"
            value={timeSavedValue}
            icon={Zap}
            colorClass="text-green-success"
          />
          <Metric
            label="Automation Cost"
            value={data.total_cost_for_period}
            icon={Cpu}
            colorClass="text-pink-destructive"
          />
        </div>
      </CardContent>
    </Card>
  );
};

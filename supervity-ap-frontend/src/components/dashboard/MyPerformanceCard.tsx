"use client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import CountUp from "react-countup";

interface MyPerformanceProps {
  invoices_processed: number;
  team_average_processed: number;
}

export const MyPerformanceCard = ({ data }: { data: MyPerformanceProps }) => {
  const difference = data.invoices_processed - data.team_average_processed;
  const performanceStatus =
    difference > 0 ? "above" : difference < 0 ? "below" : "equal";

  const statusInfo = {
    above: { icon: TrendingUp, color: "text-green-success" },
    below: { icon: TrendingDown, color: "text-pink-destructive" },
    equal: { icon: Minus, color: "text-gray-500" },
  };

  const { icon: Icon, color } = statusInfo[performanceStatus];

  return (
    <Card>
      <CardHeader>
        <CardTitle>My Performance</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex justify-between items-baseline p-4 bg-gray-50 rounded-lg">
          <span className="text-gray-600 font-medium">Invoices Processed</span>
          <span className="text-3xl font-bold text-blue-primary">
            <CountUp end={data.invoices_processed} duration={2} />
          </span>
        </div>
        <div
          className={`flex justify-between items-center p-4 rounded-lg ${performanceStatus === "above" ? "bg-green-50" : "bg-red-50"}`}
        >
          <span className={`font-medium ${color}`}>vs. Team Average</span>
          <div className={`flex items-center text-xl font-bold ${color}`}>
            <Icon className="w-5 h-5 mr-1" />
            <CountUp
              end={data.team_average_processed}
              duration={2}
              decimals={1}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

"use client";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  LabelList,
} from "recharts";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/Card";

interface TeamPerformanceData {
  name: string;
  invoices_processed: number;
}

interface TeamPerformanceLeaderboardProps {
  data: TeamPerformanceData[];
}

export const TeamPerformanceLeaderboard = ({
  data,
}: TeamPerformanceLeaderboardProps) => {
  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>Team Throughput</CardTitle>
        <CardDescription>
          Invoices processed by each team member in the selected period.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 5, right: 40, left: 20, bottom: 20 }}
          >
            <CartesianGrid strokeDasharray="3 3" horizontal={false} />
            <XAxis
              type="number"
              allowDecimals={false}
              stroke="#888888"
              fontSize={12}
              tickLine={false}
              axisLine={false}
              label={{
                value: "Invoices Processed",
                position: "insideBottom",
                offset: -10,
                fontSize: 12,
                fill: "#6B778C",
              }}
            />
            <YAxis
              type="category"
              dataKey="name"
              width={100}
              stroke="#888888"
              fontSize={12}
              tickLine={false}
              axisLine={false}
              interval={0}
            />
            <Tooltip
              cursor={{ fill: "#f3f4f6" }}
              labelStyle={{ fontWeight: "bold", color: "#0A2540" }}
              formatter={(value: number) => [`${value} invoices`, "Processed"]}
            />
            <Bar dataKey="invoices_processed" fill="#5243AA" barSize={30}>
              <LabelList
                dataKey="invoices_processed"
                position="right"
                style={{ fill: "#42526E", fontSize: 12, fontWeight: "bold" }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
};

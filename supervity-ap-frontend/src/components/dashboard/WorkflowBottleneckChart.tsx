"use client";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/Card";

interface WorkflowBottleneckProps {
  data: Record<string, number>;
}

export const WorkflowBottleneckChart = ({ data }: WorkflowBottleneckProps) => {
  const chartData = Object.entries(data).map(([name, value]) => ({
    name: name.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase()),
    "Avg. Time (Hours)": value,
  }));

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>Workflow Bottlenecks</CardTitle>
        <CardDescription>
          Average time invoices spend in each queue. Higher bars indicate
          potential delays.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart
            data={chartData}
            margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
          >
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="Avg. Time (Hours)" fill="#FF7426" />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
};

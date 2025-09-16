"use client";

import { useState, useEffect, useMemo } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import {
  Brain,
  TrendingUp,
  AlertTriangle,
  Lightbulb,
  Users,
  CreditCard,
  TrendingDown,
  Phone,
  Mail,
  Scale,
} from "lucide-react";
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
} from "recharts";
import { cn } from "@/lib/utils";

// Types for loan collections AI insights
interface RiskDriver {
  reason: string;
  count: number;
  percentage: number;
  color: string;
}

interface NextBestAction {
  id: number;
  customerNo: string;
  customerName: string;
  riskLevel: "red" | "amber" | "yellow";
  primaryReason: string;
  suggestedAction: string;
  confidence: number;
  expectedOutcome: string;
}

interface DelinquencyForecast {
  month: string;
  historical: number | null;
  forecasted: number | null;
  isProjected: boolean;
}

// Mock data for loan collections AI insights
const mockRiskDrivers: RiskDriver[] = [
  { reason: "Credit Score Drop", count: 25, percentage: 55, color: "#EF4444" },
  { reason: "Consecutive Missed EMIs", count: 14, percentage: 30, color: "#F97316" },
  { reason: "Large Overdue Amount", count: 7, percentage: 15, color: "#EAB308" },
];

const mockNextBestActions: NextBestAction[] = [
  {
    id: 1,
    customerNo: "CUST-8801",
    customerName: "John Smith",
    riskLevel: "red",
    primaryReason: "Credit Score Drop",
    suggestedAction: "Send Final Warning & Offer Credit Counseling Link",
    confidence: 92,
    expectedOutcome: "85% likelihood of payment within 7 days",
  },
  {
    id: 2,
    customerNo: "CUST-8803", 
    customerName: "Acme Corp",
    riskLevel: "red",
    primaryReason: "Payment Disputes",
    suggestedAction: "Schedule Legal Review & Document Validation",
    confidence: 88,
    expectedOutcome: "70% chance of dispute resolution",
  },
  {
    id: 3,
    customerNo: "CUST-8802",
    customerName: "Jane Doe",
    riskLevel: "amber",
    primaryReason: "Single EMI Miss",
    suggestedAction: "Send Personalized Payment Plan Offer",
    confidence: 76,
    expectedOutcome: "60% acceptance rate for payment plans",
  },
];

const mockDelinquencyForecast: DelinquencyForecast[] = [
  { month: "Aug '24", historical: 22.1, forecasted: null, isProjected: false },
  { month: "Sep '24", historical: 24.3, forecasted: null, isProjected: false },
  { month: "Oct '24", historical: 23.8, forecasted: null, isProjected: false },
  { month: "Nov '24", historical: 25.2, forecasted: null, isProjected: false },
  { month: "Dec '24", historical: 26.1, forecasted: null, isProjected: false },
  { month: "Jan '25", historical: 25.5, forecasted: null, isProjected: false },
  { month: "Feb '25", historical: null, forecasted: 27.8, isProjected: true },
  { month: "Mar '25", historical: null, forecasted: 29.2, isProjected: true },
  { month: "Apr '25", historical: null, forecasted: 30.5, isProjected: true },
];

const RISK_LEVEL_COLORS = {
  red: "#EF4444",
  amber: "#F59E0B",
  yellow: "#EAB308",
};

// Widget 1: Key Risk Drivers
const KeyRiskDrivers = () => {
  const [riskDrivers] = useState<RiskDriver[]>(mockRiskDrivers);

  const renderCustomizedLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }: any) => {
    if (percent < 0.05) return null; // Don't show labels for slices < 5%
    
    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);

    return (
      <text 
        x={x} 
        y={y} 
        fill="white" 
        textAnchor={x > cx ? 'start' : 'end'} 
        dominantBaseline="central"
        fontSize="12"
        fontWeight="bold"
      >
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-red-600" />
          Key Risk Drivers
        </CardTitle>
        <CardDescription>
          Primary reasons customers are flagged as Red or Amber risk
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={riskDrivers}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={renderCustomizedLabel}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="percentage"
                >
                  {riskDrivers.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip 
                  formatter={(value: number, name: string, props: any) => [
                    `${value}% (${props.payload.count} customers)`,
                    props.payload.reason
                  ]}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          
          <div className="space-y-4">
            <h4 className="font-medium text-gray-900">Risk Breakdown</h4>
            {riskDrivers.map((driver, index) => (
              <div key={index} className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div 
                    className="w-4 h-4 rounded-full"
                    style={{ backgroundColor: driver.color }}
                  />
                  <span className="text-sm font-medium">{driver.reason}</span>
                </div>
                <div className="text-right">
                  <div className="text-sm font-semibold">{driver.percentage}%</div>
                  <div className="text-xs text-gray-500">{driver.count} customers</div>
                    </div>
              </div>
            ))}
            </div>
            </div>
      </CardContent>
    </Card>
  );
};

// Widget 2: Next Best Action Suggestions
const NextBestActionSuggestions = () => {
  const [nextActions] = useState<NextBestAction[]>(mockNextBestActions);
  const [selectedCustomer, setSelectedCustomer] = useState<NextBestAction | null>(null);

  const getActionIcon = (action: string) => {
    if (action.includes("Warning") || action.includes("Final")) return Mail;
    if (action.includes("Legal") || action.includes("Review")) return Scale;
    if (action.includes("Call") || action.includes("Contact")) return Phone;
    return Lightbulb;
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 90) return "text-green-600";
    if (confidence >= 75) return "text-amber-600";
    return "text-red-600";
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Lightbulb className="h-5 w-5 text-blue-600" />
          Next Best Action Suggestions
        </CardTitle>
        <CardDescription>
          AI-powered recommendations for optimal customer engagement
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {nextActions.map((action) => {
            const ActionIcon = getActionIcon(action.suggestedAction);
            return (
              <div
                key={action.id}
                className="border rounded-lg p-4 hover:bg-gray-50 cursor-pointer transition-colors"
                onClick={() => setSelectedCustomer(action)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <div className={cn("w-3 h-3 rounded-full", {
                        "bg-red-500": action.riskLevel === "red",
                        "bg-amber-500": action.riskLevel === "amber", 
                        "bg-yellow-500": action.riskLevel === "yellow",
                      })} />
                      <span className="font-medium">{action.customerName}</span>
                      <span className="text-sm text-gray-500">({action.customerNo})</span>
                    </div>
                    
                    <div className="flex items-center gap-2 mb-2">
                      <ActionIcon className="h-4 w-4 text-gray-600" />
                      <span className="text-sm font-medium">{action.suggestedAction}</span>
                    </div>
                    
                    <p className="text-xs text-gray-600 mb-1">
                      <strong>Reason:</strong> {action.primaryReason}
                    </p>
                    <p className="text-xs text-gray-600">
                      <strong>Expected:</strong> {action.expectedOutcome}
                    </p>
                  </div>
                  
                  <div className="text-right">
                    <div className={cn("text-sm font-semibold", getConfidenceColor(action.confidence))}>
                      {action.confidence}% confidence
                    </div>
                    <Button size="sm" className="mt-2">
                      Apply Action
                    </Button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
        
        {selectedCustomer && (
          <div className="mt-6 p-4 bg-blue-50 rounded-lg border-l-4 border-blue-500">
            <h4 className="font-medium text-blue-900 mb-2">
              Recommendation for {selectedCustomer.customerName}
            </h4>
            <p className="text-sm text-blue-800 mb-3">
              {selectedCustomer.suggestedAction}
            </p>
            <div className="text-xs text-blue-700">
              <strong>AI Analysis:</strong> Based on similar customer profiles and historical outcomes, 
              this action has a {selectedCustomer.confidence}% success rate. {selectedCustomer.expectedOutcome}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

// Widget 3: Portfolio Delinquency Forecast
const PortfolioDelinquencyForecast = () => {
  const [forecastData] = useState<DelinquencyForecast[]>(mockDelinquencyForecast);
  
  const customTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-white p-3 border rounded-lg shadow-lg">
          <p className="font-medium">{label}</p>
          {data.historical !== null && (
            <p className="text-blue-600">
              Historical: {data.historical.toFixed(1)}%
            </p>
          )}
          {data.forecasted !== null && (
            <p className="text-red-600">
              Forecasted: {data.forecasted.toFixed(1)}%
            </p>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-purple-600" />
          Portfolio Delinquency Forecast
        </CardTitle>
        <CardDescription>
          Historical trends and 3-month forward projection based on current patterns
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-80 mb-4">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={forecastData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="month" 
                tick={{ fontSize: 12 }}
              />
              <YAxis 
                tick={{ fontSize: 12 }}
                tickFormatter={(value) => `${value}%`}
              />
              <Tooltip content={customTooltip} />
              <Line
                type="monotone"
                dataKey="historical"
                stroke="#3B82F6"
                strokeWidth={3}
                dot={{ fill: "#3B82F6", strokeWidth: 2, r: 4 }}
                connectNulls={false}
              />
              <Line
                type="monotone"
                dataKey="forecasted"
                stroke="#EF4444"
                strokeWidth={3}
                strokeDasharray="8 8"
                dot={{ fill: "#EF4444", strokeWidth: 2, r: 4 }}
                connectNulls={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 bg-blue-50 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-4 h-4 bg-blue-500 rounded"></div>
              <span className="font-medium text-blue-900">Historical Data</span>
            </div>
            <p className="text-sm text-blue-800">
              Current delinquency rate: <strong>25.5%</strong>
            </p>
            <p className="text-xs text-blue-700 mt-1">
              6-month trend: +3.4% increase
            </p>
          </div>
          
          <div className="p-4 bg-red-50 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-4 h-4 bg-red-500 rounded"></div>
              <span className="font-medium text-red-900">3-Month Forecast</span>
            </div>
            <p className="text-sm text-red-800">
              Projected rate: <strong>30.5%</strong>
            </p>
            <p className="text-xs text-red-700 mt-1">
              ⚠️ Continued deterioration expected
            </p>
          </div>
        </div>
        
        <div className="mt-4 p-3 bg-amber-50 border-l-4 border-amber-400 rounded-r-lg">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-600" />
            <span className="font-medium text-amber-900">AI Recommendation</span>
          </div>
          <p className="text-sm text-amber-800 mt-1">
            Consider implementing proactive outreach campaigns and reviewing risk assessment criteria 
            to prevent further portfolio deterioration.
          </p>
        </div>
      </CardContent>
    </Card>
  );
};

// Main Page Component
export default function AiInsightsPage() {
  return (
    <div className="container mx-auto px-4 py-6 max-w-7xl">
    <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
              <Brain className="h-8 w-8 text-purple-600" />
              AI Insights
            </h1>
            <p className="text-gray-600 mt-1">
              Actionable intelligence for managing loan delinquencies and optimizing collections
            </p>
          </div>
        </div>

        {/* Widget 1: Key Risk Drivers */}
        <KeyRiskDrivers />

        {/* Widget 2 & 3: Side by side layout */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <NextBestActionSuggestions />
          <PortfolioDelinquencyForecast />
        </div>
      </div>
    </div>
  );
}

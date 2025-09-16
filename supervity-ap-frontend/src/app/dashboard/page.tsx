"use client";
import { useEffect, useState, useCallback } from "react";
import { subDays } from "date-fns";
import { Loader2, TrendingUp, Clock, DollarSign, Target, Trash2 } from "lucide-react";
import { DateRangePicker } from "@/components/ui/DateRangePicker";
import { type DateRange } from "@/lib/api";
import {
  StaggeredFadeIn,
  FadeInItem,
} from "@/components/dashboard/StaggeredFadeIn";
import toast from "react-hot-toast";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import CountUp from "react-countup";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';



// Collections dashboard data types
interface CollectionsDashboardData {
  kpis: {
    totalAccountsProcessed: number;
    recoveryRate: number;
    totalCollections: number;
    averageResolutionTime: number;
  };
  processingAgents: Array<{
    name: string;
    status: string;
    todayActivity: string;
  }>;
  operationsAgents: Array<{
    name: string;
    activity: string;
    count: string;
  }>;
  dddBucketAnalysis: Array<{
    bucket: string;
    amount: number;
    accounts: number;
  }>;
  recoveryPerformance: Array<{
    loanType: string;
    recoveryRate: number;
  }>;
}

// Mock data for collections dashboard
const mockCollectionsData: CollectionsDashboardData = {
  kpis: {
    totalAccountsProcessed: 12847,
    recoveryRate: 74.2,
    totalCollections: 89.2,
    averageResolutionTime: 12.3
  },
  processingAgents: [
    { name: "CBS Integration Agent", status: "active", todayActivity: "2.1K synced today" },
    { name: "DPD Monitoring Agent", status: "active", todayActivity: "847 accounts flagged" },
    { name: "Communication Orchestrator", status: "active", todayActivity: "5.2K messages sent" },
    { name: "Payment Intent Tracker", status: "active", todayActivity: "34% response rate" }
  ],
  operationsAgents: [
    { name: "Risk Assessment Agent", activity: "profiles scored", count: "1.2K" },
    { name: "Legal Escalation Agent", activity: "cases flagged", count: "89" },
    { name: "Recovery Documentation", activity: "notices generated", count: "156" },
    { name: "Performance Analytics", activity: "Real-time insights", count: "" }
  ],
  dddBucketAnalysis: [
    { bucket: "0-30", amount: 6.2, accounts: 2100 },
    { bucket: "31-60", amount: 4.1, accounts: 1580 },
    { bucket: "61-90", amount: 2.8, accounts: 950 },
    { bucket: "90+", amount: 1.6, accounts: 567 }
  ],
  recoveryPerformance: [
    { loanType: "Personal Loans", recoveryRate: 78.5 },
    { loanType: "Auto Loans", recoveryRate: 82.1 },
    { loanType: "Home Loans", recoveryRate: 68.3 },
    { loanType: "Education Loans", recoveryRate: 71.9 }
  ]
};

// KPI Card Component
const KpiCard = ({
  title,
  value,
  icon: Icon,
  isCurrency = false,
  isPercentage = false,
  unit = "",
  trend = "",
  trendValue = "",
}: {
  title: string;
  value: number;
  icon: React.ElementType;
  isCurrency?: boolean;
  isPercentage?: boolean;
  unit?: string;
  trend?: string;
  trendValue?: string;
}) => (
  <Card>
    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
      <CardTitle className="text-sm font-medium text-gray-500">
        {title}
      </CardTitle>
      <Icon className="h-4 w-4 text-blue-600" />
    </CardHeader>
    <CardContent>
      <div className="text-2xl font-bold text-gray-900">
        <CountUp
          start={0}
          end={value}
          duration={2}
          separator=","
          decimals={isCurrency || isPercentage || !Number.isInteger(value) ? 1 : 0}
          prefix={isCurrency ? "₹" : ""}
          suffix={isPercentage ? "%" : unit}
        />
      </div>
      {trend && (
        <p className="text-xs text-gray-600 mt-1">
          <span className={trend.includes("increase") ? "text-green-600" : "text-red-600"}>
            {trendValue}
          </span>{" "}
          {trend}
        </p>
      )}
    </CardContent>
  </Card>
);

// Agent Status Component
const AgentCard = ({
  title,
  agents,
  type = "processing"
}: {
  title: string;
  agents: Array<{
    name: string;
    status?: string;
    todayActivity?: string;
    activity?: string;
    count?: string;
  }>;
  type?: "processing" | "operations";
}) => (
  <Card>
    <CardHeader>
      <CardTitle className="text-lg font-semibold">{title}</CardTitle>
      <p className="text-sm text-gray-600">
        {type === "processing" 
          ? "Real-time status of processing agents handling incoming accounts." 
          : "Advanced processing and decision-making agents for complex cases."
        }
      </p>
    </CardHeader>
    <CardContent>
      <div className="space-y-3">
        {agents.map((agent, index) => (
          <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center space-x-3">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span className="font-medium text-gray-900">{agent.name}</span>
            </div>
            <span className="text-sm text-gray-600">
              {type === "processing" ? agent.todayActivity : `${agent.count} ${agent.activity}`}
            </span>
          </div>
        ))}
      </div>
    </CardContent>
  </Card>
);

// DDD Bucket Analysis Component
const DddBucketAnalysis = ({ data }: { 
  data: Array<{
    bucket: string;
    amount: number;
    accounts: number;
  }>;
}) => {
  const COLORS = ['#3B82F6', '#60A5FA', '#93C5FD', '#DBEAFE'];
  
  return (
    <Card>
      <CardHeader>
        <CardTitle>DDD Bucket Analysis</CardTitle>
        <p className="text-sm text-gray-600">
          Current distribution of overdue accounts across DPD buckets.
        </p>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis 
              dataKey="bucket" 
              tick={{ fontSize: 12 }}
            />
            <YAxis 
              tick={{ fontSize: 12 }}
              tickFormatter={(value) => `${value}K`}
            />
            <Tooltip 
              formatter={(value: number, name: string) => [
                name === 'amount' ? `₹${value}K Cr` : `${value} accounts`,
                name === 'amount' ? 'Amount' : 'Accounts'
              ]}
              labelFormatter={(label) => `DPD: ${label} days`}
            />
            <Bar dataKey="amount" fill="#3B82F6" radius={[4, 4, 0, 0]}>
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <div className="mt-4 grid grid-cols-2 gap-4">
          {data.map((bucket, index) => (
            <div key={index} className="text-center">
              <div className="text-sm text-gray-600">DPD {bucket.bucket}</div>
              <div className="font-semibold">{bucket.accounts} accounts</div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};

// Recovery Performance Component
const RecoveryPerformance = ({ data }: { 
  data: Array<{
    loanType: string;
    recoveryRate: number;
  }>;
}) => (
  <Card>
    <CardHeader>
      <CardTitle>Recovery Performance</CardTitle>
      <p className="text-sm text-gray-600">
        Collections effectiveness by product type and channel.
      </p>
    </CardHeader>
    <CardContent>
      <div className="space-y-4">
        {data.map((item, index) => (
          <div key={index} className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium">{item.loanType}</span>
              <span className="text-sm font-semibold text-green-600">
                {item.recoveryRate}% recovery
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-green-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${item.recoveryRate}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </CardContent>
  </Card>
);

export default function DashboardPage() {
  const [isLoading, setIsLoading] = useState(true);
  const [data, setData] = useState<CollectionsDashboardData>(mockCollectionsData);
  
  // Date range state
  const [dateRange, setDateRange] = useState<DateRange>({
    from: subDays(new Date(), 7).toISOString().split('T')[0],
    to: new Date().toISOString().split('T')[0],
  });

  const fetchDashboardData = useCallback(async () => {
    setIsLoading(true);
    try {
      // Fetch real data from collection APIs
      const [kpis, metrics, dashboardSummary] = await Promise.all([
        import('@/lib/collection-api').then(api => api.getCollectionKPIs()),
        import('@/lib/collection-api').then(api => api.getCollectionMetrics()),
        import('@/lib/api').then(api => api.getCollectionDashboardSummary())
      ]);

      // Transform API data to match component expectations
      const transformedData: CollectionsDashboardData = {
        kpis: {
          totalAccountsProcessed: dashboardSummary.contract_processing.total_contracts_processed,
          recoveryRate: 100 - kpis.delinquencyRate, // Inverse of delinquency rate
          totalCollections: kpis.totalCollected / 1000000, // Convert to millions
          averageResolutionTime: 12.3 // Keep static for now
        },
        processingAgents: [], // Removed as requested
        operationsAgents: [], // Removed as requested
        dddBucketAnalysis: [
          { bucket: "0-30", amount: metrics.agingBuckets.days1_30 / 100000, accounts: 2100 },
          { bucket: "31-60", amount: metrics.agingBuckets.days31_60 / 100000, accounts: 1580 },
          { bucket: "61-90", amount: metrics.agingBuckets.days61_90 / 100000, accounts: 950 },
          { bucket: "90+", amount: metrics.agingBuckets.days90Plus / 100000, accounts: kpis.accountsOverdue }
        ],
        recoveryPerformance: [
          { loanType: "Personal Loans", recoveryRate: 78.5 },
          { loanType: "Auto Loans", recoveryRate: 82.1 },
          { loanType: "Home Loans", recoveryRate: 68.3 },
          { loanType: "Education Loans", recoveryRate: 71.9 }
        ]
      };

      setData(transformedData);
    } catch (error) {
      console.error("Failed to fetch dashboard data:", error);
      toast.error("Failed to load dashboard data");
      // Fallback to mock data on error
      setData(mockCollectionsData);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const clearAllCustomerData = useCallback(async () => {
    const confirmed = window.confirm(
      "Are you sure you want to clear all customer data? This action cannot be undone."
    );
    
    if (confirmed) {
      setIsLoading(true);
      try {
        // Check if user is authenticated
        const token = localStorage.getItem('authToken');
        if (!token) {
          toast.error("Please log in to clear data. You'll be redirected to the login page.");
          setTimeout(() => {
            window.location.href = '/login';
          }, 2000);
          return;
        }

        // Call the clear database API using the proper API function
        const result = await import('@/lib/api').then(api => api.clearAllCustomerData());
        toast.success(`Successfully cleared ${result.total_deleted || 'all'} records!`);
        // Refresh the dashboard to show empty state
        await fetchDashboardData();
      } catch (error) {
        console.error("Failed to clear customer data:", error);
        const errorMessage = error instanceof Error ? error.message : "Unknown error occurred";
        if (errorMessage.includes('401') || errorMessage.includes('validate credentials')) {
          toast.error("Authentication failed. Please log in again.");
          localStorage.removeItem('authToken');
          setTimeout(() => {
            window.location.href = '/login';
          }, 2000);
        } else {
          toast.error(`Failed to clear customer data: ${errorMessage}`);
        }
      } finally {
        setIsLoading(false);
      }
    }
  }, [fetchDashboardData]);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        <span className="ml-2 text-gray-600">Loading dashboard...</span>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600 mt-1">Collections Command Center</p>
        </div>
        <div className="flex items-center space-x-4 mt-4 md:mt-0">
          <div className="flex items-center space-x-2 text-sm text-gray-600">
            <span>Viewing Dashboard For:</span>
            <select className="border rounded px-2 py-1">
              <option>Entire Team</option>
            </select>
          </div>
          <DateRangePicker
            value={dateRange}
            onValueChange={setDateRange}
          />
          <button 
            onClick={fetchDashboardData}
            className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
          >
            Refresh
          </button>
          <button 
            onClick={clearAllCustomerData}
            className="px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700 flex items-center gap-1"
            disabled={isLoading}
          >
            <Trash2 className="w-3 h-3" />
            Clear Data
          </button>
        </div>
      </div>

      <StaggeredFadeIn>
        {/* KPI Cards */}
        <FadeInItem>
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            <KpiCard
              title="Total Accounts Processed"
              value={data.kpis.totalAccountsProcessed}
              icon={Target}
              trend="+6.2% from last period"
              trendValue="+6.2%"
            />
            <KpiCard
              title="Recovery Rate"
              value={data.kpis.recoveryRate}
              icon={TrendingUp}
              isPercentage={true}
              trend="+2.1% improvement"
              trendValue="+2.1%"
            />
            <KpiCard
              title="Total Collections"
              value={data.kpis.totalCollections}
              icon={DollarSign}
              isCurrency={true}
              unit=" Cr"
              trend="+5.4% vs target"
              trendValue="+5.4%"
            />
            <KpiCard
              title="Average Resolution Time"
              value={data.kpis.averageResolutionTime}
              icon={Clock}
              unit=" days"
              trend="+1.2 days increase"
              trendValue="+1.2"
            />
          </div>
        </FadeInItem>



        {/* Analytics Charts */}
        <FadeInItem>
          <div className="grid gap-6 md:grid-cols-2">
            <DddBucketAnalysis data={data.dddBucketAnalysis} />
            <RecoveryPerformance data={data.recoveryPerformance} />
          </div>
        </FadeInItem>
      </StaggeredFadeIn>
    </div>
  );
}
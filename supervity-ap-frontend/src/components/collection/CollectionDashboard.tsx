"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, LineChart, Line } from 'recharts';

interface CollectionMetrics {
  agingBuckets: {
    current: number;
    days1_30: number;
    days31_60: number;
    days61_90: number;
    days90Plus: number;
  };
  collectionFunnel: {
    totalDue: number;
    paidByCustomer: number;
    clearedByBank: number;
  };
  delinquencyTrend: Array<{
    month: string;
    rate: number;
  }>;
}

interface CollectionDashboardProps {
  metrics: CollectionMetrics;
}

const formatCurrency = (amount: number) => {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
};

const COLORS = ['#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#374151'];

export const CollectionDashboard = ({ metrics }: CollectionDashboardProps) => {
  // Prepare aging data for bar chart
  const agingData = [
    { name: 'Current', amount: metrics.agingBuckets.current },
    { name: '1-30 Days', amount: metrics.agingBuckets.days1_30 },
    { name: '31-60 Days', amount: metrics.agingBuckets.days31_60 },
    { name: '61-90 Days', amount: metrics.agingBuckets.days61_90 },
    { name: '90+ Days', amount: metrics.agingBuckets.days90Plus },
  ];

  // Prepare funnel data
  const funnelData = [
    { name: 'Total Due', value: metrics.collectionFunnel.totalDue, fill: '#3B82F6' },
    { name: 'Paid by Customer', value: metrics.collectionFunnel.paidByCustomer, fill: '#10B981' },
    { name: 'Cleared by Bank', value: metrics.collectionFunnel.clearedByBank, fill: '#059669' },
  ];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Accounts Receivable Aging Chart */}
      <Card className="col-span-1 lg:col-span-2">
        <CardHeader>
          <CardTitle>Accounts Receivable Aging</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={agingData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="name" 
                tick={{ fontSize: 10 }}
                interval={0}
                angle={-45}
                textAnchor="end"
                height={70}
              />
              <YAxis 
                tick={{ fontSize: 10 }}
                tickFormatter={formatCurrency}
              />
              <Tooltip 
                formatter={(value: number) => [formatCurrency(value), 'Amount']}
                labelStyle={{ color: '#374151' }}
              />
              <Bar 
                dataKey="amount" 
                fill="#3B82F6"
                radius={[4, 4, 0, 0]}
              >
                {agingData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Delinquency Trend */}
      <Card className="col-span-1 lg:col-span-2">
        <CardHeader>
          <CardTitle>Delinquency Trend (Last 6 Months)</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={metrics.delinquencyTrend}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="month" 
                tick={{ fontSize: 10 }}
              />
              <YAxis 
                tick={{ fontSize: 10 }}
                tickFormatter={(value) => `${value}%`}
              />
              <Tooltip 
                formatter={(value: number) => [`${value}%`, 'Delinquency Rate']}
                labelStyle={{ color: '#374151' }}
              />
              <Line 
                type="monotone" 
                dataKey="rate" 
                stroke="#EF4444" 
                strokeWidth={3}
                dot={{ fill: '#EF4444', strokeWidth: 2, r: 6 }}
                activeDot={{ r: 8, stroke: '#EF4444', strokeWidth: 2 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Collection Funnel */}
      <Card>
        <CardHeader>
          <CardTitle>Collection Funnel</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {funnelData.map((item, index) => {
              const percentage = index === 0 ? 100 : (item.value / funnelData[0].value) * 100;
              return (
                <div key={item.name} className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">{item.name}</span>
                    <span className="text-sm text-gray-600">{formatCurrency(item.value)}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-3">
                    <div
                      className="h-3 rounded-full transition-all duration-300"
                      style={{
                        width: `${percentage}%`,
                        backgroundColor: item.fill,
                      }}
                    />
                  </div>
                  <div className="text-xs text-gray-500">{percentage.toFixed(1)}% of total</div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Quick Stats Cards */}
      <Card>
        <CardHeader>
          <CardTitle>Collection Efficiency</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Collection Rate</span>
              <span className="text-lg font-semibold text-green-600">
                {((metrics.collectionFunnel.paidByCustomer / metrics.collectionFunnel.totalDue) * 100).toFixed(1)}%
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Clearance Rate</span>
              <span className="text-lg font-semibold text-blue-600">
                {((metrics.collectionFunnel.clearedByBank / metrics.collectionFunnel.paidByCustomer) * 100).toFixed(1)}%
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Processing Gap</span>
              <span className="text-lg font-semibold text-orange-600">
                {formatCurrency(metrics.collectionFunnel.paidByCustomer - metrics.collectionFunnel.clearedByBank)}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Risk Distribution */}
      <Card>
        <CardHeader>
          <CardTitle>Risk Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex justify-between items-center p-3 bg-green-50 rounded-lg">
              <span className="text-sm font-medium">Low Risk (Current)</span>
              <span className="text-sm font-semibold text-green-700">
                {formatCurrency(metrics.agingBuckets.current)}
              </span>
            </div>
            <div className="flex justify-between items-center p-3 bg-yellow-50 rounded-lg">
              <span className="text-sm font-medium">Medium Risk (1-60 days)</span>
              <span className="text-sm font-semibold text-yellow-700">
                {formatCurrency(metrics.agingBuckets.days1_30 + metrics.agingBuckets.days31_60)}
              </span>
            </div>
            <div className="flex justify-between items-center p-3 bg-red-50 rounded-lg">
              <span className="text-sm font-medium">High Risk (60+ days)</span>
              <span className="text-sm font-semibold text-red-700">
                {formatCurrency(metrics.agingBuckets.days61_90 + metrics.agingBuckets.days90Plus)}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Performance Indicators */}
      <Card>
        <CardHeader>
          <CardTitle>Performance Indicators</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {(metrics.delinquencyTrend[metrics.delinquencyTrend.length - 1]?.rate || 0).toFixed(1)}%
              </div>
              <div className="text-sm text-gray-600">Current Delinquency Rate</div>
              <div className="text-xs text-green-600 mt-1">
                ↓ 0.6% from last month
              </div>
            </div>
            <div className="text-center border-t pt-4">
              <div className="text-2xl font-bold text-green-600">
                {((metrics.agingBuckets.current / (metrics.agingBuckets.current + metrics.agingBuckets.days1_30 + metrics.agingBuckets.days31_60 + metrics.agingBuckets.days61_90 + metrics.agingBuckets.days90Plus)) * 100).toFixed(1)}%
              </div>
              <div className="text-sm text-gray-600">Accounts Current</div>
              <div className="text-xs text-green-600 mt-1">
                ↑ 2.1% from last month
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

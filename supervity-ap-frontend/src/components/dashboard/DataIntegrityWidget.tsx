"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { AlertTriangle, CheckCircle, Clock, TrendingUp, AlertCircle } from "lucide-react";
import { getCollectionDashboardSummary, getDataIntegrityAlerts, resolveDataIntegrityAlert } from "@/lib/api";
import toast from "react-hot-toast";

interface DataIntegrityAlert {
  id: number;
  alert_type: string;
  title: string;
  description: string;
  severity: "high" | "medium" | "low";
  customer_name?: string;
  cbs_value?: string;
  contract_value?: string;
  created_at: string;
  is_resolved: boolean;
}

interface DashboardSummary {
  data_integrity: {
    total_unresolved_alerts: number;
    high_priority_alerts: number;
    recent_alerts: Array<{
      id: number;
      type: string;
      title: string;
      customer_name: string;
      severity: string;
      created_at: string;
    }>;
  };
  customer_risk: Record<string, number>;
  contract_processing: {
    total_contracts_processed: number;
  };
}

export function DataIntegrityWidget() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [alerts, setAlerts] = useState<DataIntegrityAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [resolving, setResolving] = useState<number | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [summaryResponse, alertsResponse] = await Promise.all([
        getCollectionDashboardSummary(),
        getDataIntegrityAlerts({ limit: 10, resolved: false }),
      ]);

      setSummary(summaryResponse);
      setAlerts(alertsResponse);
    } catch (error) {
      console.error("Error fetching data integrity data:", error);
      toast.error("Failed to load data integrity information");
    } finally {
      setLoading(false);
    }
  };

  const resolveAlert = async (alertId: number) => {
    try {
      setResolving(alertId);
      await resolveDataIntegrityAlert(alertId);
      toast.success("Alert resolved successfully");
      fetchData(); // Refresh data
    } catch (error) {
      console.error("Error resolving alert:", error);
      toast.error("Failed to resolve alert");
    } finally {
      setResolving(null);
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case "high":
        return <AlertTriangle className="h-4 w-4 text-red-500" />;
      case "medium":
        return <AlertCircle className="h-4 w-4 text-yellow-500" />;
      case "low":
        return <Clock className="h-4 w-4 text-blue-500" />;
      default:
        return <AlertCircle className="h-4 w-4 text-gray-500" />;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "high":
        return "bg-red-100 text-red-800 border-red-200";
      case "medium":
        return "bg-yellow-100 text-yellow-800 border-yellow-200";
      case "low":
        return "bg-blue-100 text-blue-800 border-blue-200";
      default:
        return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

  const formatAlertType = (type: string) => {
    return type.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());
  };

  useEffect(() => {
    fetchData();
  }, []);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-orange-500" />
            Data Integrity Monitor
          </CardTitle>
          <CardDescription>
            Loading data integrity status...
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-4">
            <div className="h-20 bg-gray-200 rounded"></div>
            <div className="h-32 bg-gray-200 rounded"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-medium">Unresolved Alerts</p>
                <p className="text-2xl font-bold text-red-600">
                  {summary?.data_integrity.total_unresolved_alerts || 0}
                </p>
              </div>
              <AlertTriangle className="h-8 w-8 text-red-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-medium">High Priority</p>
                <p className="text-2xl font-bold text-orange-600">
                  {summary?.data_integrity.high_priority_alerts || 0}
                </p>
              </div>
              <AlertCircle className="h-8 w-8 text-orange-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-medium">Contracts Processed</p>
                <p className="text-2xl font-bold text-green-600">
                  {summary?.contract_processing.total_contracts_processed || 0}
                </p>
              </div>
              <TrendingUp className="h-8 w-8 text-green-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Active Alerts */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-orange-500" />
                Active Data Integrity Alerts
              </CardTitle>
              <CardDescription>
                Mismatches between CBS data and contract terms requiring attention
              </CardDescription>
            </div>
            <Button 
              variant="secondary" 
              size="sm" 
              onClick={fetchData}
              disabled={loading}
            >
              Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {alerts.length === 0 ? (
            <div className="text-center py-8">
              <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-4" />
              <p className="text-gray-medium">
                All data integrity checks are passing! No alerts to display.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {alerts.map((alert) => (
                <div
                  key={alert.id}
                  className="border rounded-lg p-4 space-y-3 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3 flex-1">
                      {getSeverityIcon(alert.severity)}
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <h4 className="font-medium text-gray-900">{alert.title}</h4>
                          <Badge 
                            variant="outline" 
                            className={getSeverityColor(alert.severity)}
                          >
                            {alert.severity.toUpperCase()}
                          </Badge>
                          <Badge variant="outline">
                            {formatAlertType(alert.alert_type)}
                          </Badge>
                        </div>
                        <p className="text-sm text-gray-600 mb-2">
                          {alert.description}
                        </p>
                        {alert.customer_name && (
                          <p className="text-sm text-gray-500">
                            Customer: <span className="font-medium">{alert.customer_name}</span>
                          </p>
                        )}
                        {alert.cbs_value && alert.contract_value && (
                          <div className="text-sm text-gray-500 mt-1">
                            CBS Value: <span className="font-mono">{alert.cbs_value}</span> | 
                            Contract Value: <span className="font-mono">{alert.contract_value}</span>
                          </div>
                        )}
                        <p className="text-xs text-gray-400 mt-1">
                          {new Date(alert.created_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => resolveAlert(alert.id)}
                      disabled={resolving === alert.id}
                      className="ml-4"
                    >
                      {resolving === alert.id ? "Resolving..." : "Resolve"}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Customer Risk Distribution */}
      {summary?.customer_risk && Object.keys(summary.customer_risk).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Customer Risk Distribution</CardTitle>
            <CardDescription>
              Overview of customer risk levels based on CBS data
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4">
              {Object.entries(summary.customer_risk).map(([riskLevel, count]) => (
                <div
                  key={riskLevel}
                  className={`p-4 rounded-lg border ${
                    riskLevel === "RED"
                      ? "bg-red-50 border-red-200"
                      : riskLevel === "AMBER"
                      ? "bg-yellow-50 border-yellow-200"
                      : riskLevel === "GREEN"
                      ? "bg-green-50 border-green-200"
                      : "bg-gray-50 border-gray-200"
                  }`}
                >
                  <div className="text-center">
                    <p className="text-2xl font-bold">{count}</p>
                    <p className="text-sm font-medium">{riskLevel || "UNKNOWN"}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

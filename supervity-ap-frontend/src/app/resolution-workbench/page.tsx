"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { CollectionWorkbench } from "@/components/workbench/CollectionWorkbench";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/Table";
import {
  Search,
  Filter,
  ArrowRight,
  Clock,
  AlertTriangle,
  TrendingDown,
  Users,
} from "lucide-react";

interface WorkbenchItem {
  id: string;
  customerNo: string;
  customerName: string;
  loanId: string;
  amountDue: number;
  daysOverdue: number;
  riskLevel: string;
  priority: "high" | "medium" | "low";
  lastAction: string;
  assignedTo: string;
}

// Mock data for the workbench queue
const mockWorkbenchItems: WorkbenchItem[] = [
  {
    id: "1",
    customerNo: "CUST-8801",
    customerName: "Rajesh Kumar",
    loanId: "LN-78001",
    amountDue: 15000,
    daysOverdue: 15,
    riskLevel: "amber",
    priority: "high",
    lastAction: "Email sent 3 days ago",
    assignedTo: "Collection Agent 1"
  },
  {
    id: "2",
    customerNo: "CUST-8802",
    customerName: "Priya Sharma",
    loanId: "LN-78002",
    amountDue: 25000,
    daysOverdue: 30,
    riskLevel: "red",
    priority: "high",
    lastAction: "Phone call attempted",
    assignedTo: "Collection Agent 2"
  },
  {
    id: "3",
    customerNo: "CUST-8803",
    customerName: "Amit Patel",
    loanId: "LN-78003",
    amountDue: 12000,
    daysOverdue: 7,
    riskLevel: "yellow",
    priority: "medium",
    lastAction: "SMS reminder sent",
    assignedTo: "Collection Agent 1"
  },
];

function WorkbenchContent() {
  const searchParams = useSearchParams();
  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(
    searchParams?.get("accountId") || null
  );
  const [workbenchItems, setWorkbenchItems] = useState<WorkbenchItem[]>(mockWorkbenchItems);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterRisk, setFilterRisk] = useState<string>("");

  const filteredItems = workbenchItems.filter(item => {
    const matchesSearch = 
      item.customerName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.customerNo.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.loanId.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesRisk = !filterRisk || item.riskLevel === filterRisk;
    
    return matchesSearch && matchesRisk;
  });

  const getRiskBadgeColor = (riskLevel: string) => {
    switch (riskLevel.toLowerCase()) {
      case "red":
        return "bg-red-100 text-red-800";
      case "amber":
        return "bg-yellow-100 text-yellow-800";
      case "yellow":
        return "bg-yellow-50 text-yellow-700";
      default:
        return "bg-green-100 text-green-800";
    }
  };

  const getPriorityBadgeColor = (priority: string) => {
    switch (priority.toLowerCase()) {
      case "high":
        return "bg-red-100 text-red-800";
      case "medium":
        return "bg-yellow-100 text-yellow-800";
      default:
        return "bg-green-100 text-green-800";
    }
  };

  // If an account is selected, show the workbench
  if (selectedAccountId) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="bg-white border-b px-6 py-4">
          <Button
            variant="ghost"
            onClick={() => setSelectedAccountId(null)}
            className="mb-2"
          >
            ← Back to Queue
          </Button>
        </div>
        <CollectionWorkbench accountId={selectedAccountId} />
      </div>
    );
  }

  // Show the workbench queue
  return (
    <div className="container mx-auto px-4 py-6 max-w-7xl">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Collection Resolution Workbench</h1>
        <p className="text-gray-600">
          Review and resolve customer accounts requiring collection action
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <div className="p-2 bg-red-100 rounded-lg">
                <AlertTriangle className="h-6 w-6 text-red-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">High Priority</p>
                <p className="text-2xl font-bold text-gray-900">
                  {workbenchItems.filter(item => item.priority === "high").length}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <div className="p-2 bg-yellow-100 rounded-lg">
                <Clock className="h-6 w-6 text-yellow-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Overdue 30+ Days</p>
                <p className="text-2xl font-bold text-gray-900">
                  {workbenchItems.filter(item => item.daysOverdue >= 30).length}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Users className="h-6 w-6 text-blue-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Total Accounts</p>
                <p className="text-2xl font-bold text-gray-900">{workbenchItems.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <div className="p-2 bg-green-100 rounded-lg">
                <TrendingDown className="h-6 w-6 text-green-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Total Amount Due</p>
                <p className="text-2xl font-bold text-gray-900">
                  ₹{workbenchItems.reduce((sum, item) => sum + item.amountDue, 0).toLocaleString()}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card className="mb-6">
        <CardContent className="p-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                <Input
                  placeholder="Search by customer name, number, or loan ID..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <div className="flex gap-2">
              <select
                value={filterRisk}
                onChange={(e) => setFilterRisk(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm"
              >
                <option value="">All Risk Levels</option>
                <option value="red">Red</option>
                <option value="amber">Amber</option>
                <option value="yellow">Yellow</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Workbench Queue Table */}
      <Card>
        <CardHeader>
          <CardTitle>Collection Queue</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Customer</TableHead>
                <TableHead>Loan ID</TableHead>
                <TableHead>Amount Due</TableHead>
                <TableHead>Days Overdue</TableHead>
                <TableHead>Risk Level</TableHead>
                <TableHead>Priority</TableHead>
                <TableHead>Last Action</TableHead>
                <TableHead>Assigned To</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredItems.map((item) => (
                <TableRow key={item.id} className="hover:bg-gray-50">
                  <TableCell>
                    <div>
                      <div className="font-medium">{item.customerName}</div>
                      <div className="text-sm text-gray-600">{item.customerNo}</div>
                    </div>
                  </TableCell>
                  <TableCell className="font-mono text-sm">{item.loanId}</TableCell>
                  <TableCell className="font-semibold">
                    ₹{item.amountDue.toLocaleString()}
                  </TableCell>
                  <TableCell>
                    <span className={`font-medium ${
                      item.daysOverdue > 30 ? 'text-red-600' : 
                      item.daysOverdue > 15 ? 'text-yellow-600' : 'text-gray-900'
                    }`}>
                      {item.daysOverdue} days
                    </span>
                  </TableCell>
                  <TableCell>
                    <Badge className={getRiskBadgeColor(item.riskLevel)}>
                      {item.riskLevel.toUpperCase()}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge className={getPriorityBadgeColor(item.priority)}>
                      {item.priority.toUpperCase()}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm text-gray-600">
                    {item.lastAction}
                  </TableCell>
                  <TableCell className="text-sm">{item.assignedTo}</TableCell>
                  <TableCell>
                    <Button
                      size="sm"
                      onClick={() => setSelectedAccountId(item.id)}
                      className="flex items-center gap-1"
                    >
                      Review
                      <ArrowRight className="h-3 w-3" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          {filteredItems.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              No accounts found matching your criteria.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function ResolutionWorkbenchPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    }>
      <WorkbenchContent />
    </Suspense>
  );
}

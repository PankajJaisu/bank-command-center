"use client";

import { useState, useMemo, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/Table";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Checkbox } from "@/components/ui/Checkbox";
import { Modal } from "@/components/ui/Modal";
import {
  CreditCard,
  Loader2,
  IndianRupee,
  Search,
  X,
  AlertCircle,
  Download,
  Phone,
  Calendar,
  FileText,
  TrendingUp,
  TrendingDown,
  Users,
  Target,
  RefreshCw,
  Bot,
  Zap,
} from "lucide-react";
import { format, parseISO } from "date-fns";
import toast from "react-hot-toast";

import { EmptyState } from "@/components/shared/EmptyState";
import { Tooltip } from "@/components/ui/Tooltip";
import { cn } from "@/lib/utils";
import {
  getLoanAccounts,
  getLoanAccountsWithContracts,
  getCollectionKPIs,
  getCollectionMetrics,
  logContact,
  updateCollectionStatus,
  performBatchAction,
  generateDunningLetter,
  type LoanAccount,
  type CollectionKPIs,
  type CollectionMetrics,
} from "@/lib/collection-api";

// Types are now imported from collection-api.ts

// Mock data for demonstration
const mockLoanAccounts: LoanAccount[] = [
  {
    id: 1,
    customerId: 1001, // NEW: Customer ID
    customerNo: "CUST-8801",
    customerName: "John Smith",
    loanId: "LN-12345",
    nextPaymentDueDate: "2025-08-05",
    amountDue: 1500.00,
    daysOverdue: 9,
    lastPaymentDate: "2025-07-05",
    collectionStatus: "promise_to_pay",
    reconciliationStatus: "cleared",
    lastContactNote: "Promised payment by 08/15",
    totalOutstanding: 35000,
    principalBalance: 32000,
    interestAccrued: 3000,
    collectorName: "Mike Davis",
    riskLevel: "red",
    alertSummary: "3 Missed EMIs, Credit Score Dropped by 55 pts",
    lastContactDate: "2025-08-10",
    // NEW: Contract note information
    hasContractNote: true,
    contractNoteId: 1,
    contractEmiAmount: 1500.00,
    contractDueDay: 5,
    contractLateFeePercent: 2.0,
    contractFilename: "CUST-8801_contract_note.pdf",
    contractFilePath: "/contracts/CUST-8801_contract_note.pdf",
    cibilScore: 665,
    pendingAmount: 1500.00,
    emi_pending: 2,
    segment: "Premium",
  },
  {
    id: 2,
    customerId: 1002, // NEW: Customer ID
    customerNo: "CUST-8803",
    customerName: "Acme Corp",
    loanId: "LN-12347",
    nextPaymentDueDate: "2025-08-12",
    amountDue: 5000.00,
    daysOverdue: 2,
    lastPaymentDate: "2025-07-12",
    collectionStatus: "disputed",
    reconciliationStatus: "unreconciled",
    lastContactNote: "Customer disputes amount",
    totalOutstanding: 125000,
    principalBalance: 115000,
    interestAccrued: 10000,
    collectorName: "Tom Wilson",
    riskLevel: "red",
    alertSummary: "Payment Disputes, 2 Missed EMIs",
    lastContactDate: "2025-08-12",
    // NEW: Contract note information (no contract uploaded yet)
    hasContractNote: false,
    contractNoteId: null,
    contractEmiAmount: null,
    contractDueDay: null,
    contractLateFeePercent: null,
    contractFilename: null,
    contractFilePath: null,
    cibilScore: 720,
    pendingAmount: 5000.00,
    emi_pending: 1,
    segment: "Corporate",
  },
  {
    id: 3,
    customerId: 1003, // NEW: Customer ID
    customerNo: "CUST-8802",
    customerName: "Jane Doe",
    loanId: "LN-12346",
    nextPaymentDueDate: "2025-08-10",
    amountDue: 3000.00,
    daysOverdue: 4,
    lastPaymentDate: "2025-07-10",
    collectionStatus: "pending",
    reconciliationStatus: "in_transit",
    lastContactNote: null,
    totalOutstanding: 75000,
    principalBalance: 70000,
    interestAccrued: 5000,
    collectorName: "Lisa Chen",
    riskLevel: "amber",
    alertSummary: "Credit Score Drop by 25 pts",
    lastContactDate: "2025-08-08",
    // NEW: Contract note information
    hasContractNote: true,
    contractNoteId: 2,
    contractEmiAmount: 3000.00,
    contractDueDay: 10,
    contractLateFeePercent: 1.5,
    contractFilename: "CUST-8802_contract_note.pdf",
    contractFilePath: "/contracts/CUST-8802_contract_note.pdf",
    cibilScore: 690,
    pendingAmount: 3000.00,
    emi_pending: 3,
    segment: "Retail",
  },
  {
    id: 4,
    customerId: 1004, // NEW: Customer ID
    customerNo: "CUST-8804",
    customerName: "Innovations Inc.",
    loanId: "LN-12348",
    nextPaymentDueDate: "2025-08-13",
    amountDue: 2000.00,
    daysOverdue: 1,
    lastPaymentDate: "2025-07-13",
    collectionStatus: "contacted",
    reconciliationStatus: "unreconciled",
    lastContactNote: "Sent email reminder 08/14",
    totalOutstanding: 45000,
    principalBalance: 42000,
    interestAccrued: 3000,
    collectorName: "Sarah Johnson",
    riskLevel: "yellow",
    alertSummary: "1 Day Overdue",
    lastContactDate: "2025-08-14",
    // NEW: Contract note information (no contract uploaded yet)
    hasContractNote: false,
    contractNoteId: null,
    contractEmiAmount: null,
    contractDueDay: null,
    contractLateFeePercent: null,
    contractFilename: null,
    contractFilePath: null,
    cibilScore: 750,
    pendingAmount: 2000.00,
    emi_pending: 0,
    segment: "SME",
  }
];

const mockKPIs: CollectionKPIs = {
  totalReceivablesDue: 11500.00,
  totalCollected: 8500.00,
  delinquencyRate: 25.5,
  totalAmountOverdue: 11500.00,
  accountsOverdue: 4,
  collectedCleared: 6500.00,
  collectedInTransit: 2000.00
};

const mockMetrics: CollectionMetrics = {
  agingBuckets: {
    current: 125000,
    days1_30: 75000,
    days31_60: 45000,
    days61_90: 25000,
    days90Plus: 10000
  },
  collectionFunnel: {
    totalDue: 280000,
    paidByCustomer: 220000,
    clearedByBank: 200000
  },
  delinquencyTrend: [
    { month: "Feb", rate: 22.1 },
    { month: "Mar", rate: 24.3 },
    { month: "Apr", rate: 23.8 },
    { month: "May", rate: 25.2 },
    { month: "Jun", rate: 26.1 },
    { month: "Jul", rate: 25.5 }
  ]
};

const COLLECTION_STATUS_COLORS = {
  pending: "bg-gray-100 text-gray-800",
  contacted: "bg-blue-100 text-blue-800",
  promise_to_pay: "bg-yellow-100 text-yellow-800",
  disputed: "bg-red-100 text-red-800",
  cleared: "bg-green-100 text-green-800"
};

const RECONCILIATION_STATUS_COLORS = {
  cleared: "bg-green-100 text-green-800",
  in_transit: "bg-yellow-100 text-yellow-800",
  unreconciled: "bg-red-100 text-red-800"
};

const RISK_LEVEL_COLORS = {
  red: "bg-red-500",
  amber: "bg-amber-500", 
  green: "bg-green-500"
};

const RISK_LEVEL_PRIORITY = {
  red: 1,
  amber: 2,
  green: 3
};

const getDaysOverdueColor = (days: number) => {
  if (days === 0) return "text-green-600";
  if (days <= 30) return "text-amber-600";
  return "text-red-600";
};

const formatCurrency = (amount: number) => {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR'
  }).format(amount);
};

// Calculate aggregate risk assessment based on CIBIL score and risk level
const calculateRiskAssessment = (cibilScore: number | null, riskLevel: string, daysOverdue: number) => {
  let score = 0;
  
  // CIBIL Risk Score (40% weight)
  if (cibilScore) {
    if (cibilScore >= 750) score += 40; // Green
    else if (cibilScore >= 700) score += 25; // Amber  
    else score += 10; // Red
  } else {
    score += 10; // Default to red if no CIBIL
  }
  
  // Risk Level Score (35% weight)
  if (riskLevel === 'green') score += 35;
  else if (riskLevel === 'amber') score += 15;
  else score += 5; // red
  
  // Days Overdue Score (25% weight)
  if (daysOverdue === 0) score += 25;
  else if (daysOverdue <= 30) score += 15;
  else if (daysOverdue <= 60) score += 10;
  else score += 5;
  
  // Return assessment based on total score
  if (score >= 80) return { level: 'EXCELLENT', color: 'text-green-800 bg-green-200' };
  else if (score >= 65) return { level: 'GOOD', color: 'text-green-800 bg-green-200' };
  else if (score >= 45) return { level: 'MODERATE', color: 'text-amber-800 bg-amber-200' };
  else if (score >= 30) return { level: 'HIGH RISK', color: 'text-amber-800 bg-amber-200' };
  else return { level: 'CRITICAL', color: 'text-red-800 bg-red-200' };
};



export default function CollectionCellPage() {
  const router = useRouter();
  
  // State management
  const [loanAccounts, setLoanAccounts] = useState<LoanAccount[]>([]);
  const [kpis, setKpis] = useState<CollectionKPIs>(mockKPIs);
  const [metrics, setMetrics] = useState<CollectionMetrics>(mockMetrics);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedRows, setSelectedRows] = useState<Record<number, boolean>>({});
  
  // Filter states
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [collectorFilter, setCollectorFilter] = useState("");
  const [overdueFilter, setOverdueFilter] = useState<"all" | "current" | "overdue">("all");
  const [riskLevelFilter, setRiskLevelFilter] = useState("");
  
  // Tab states
  const [activeTab, setActiveTab] = useState<"collection" | "processed">("collection");
  
  // Modal states
  const [isContactModalOpen, setIsContactModalOpen] = useState(false);
  const [selectedAccount, setSelectedAccount] = useState<LoanAccount | null>(null);
  const [contactNote, setContactNote] = useState("");
  const [isPolicyAgentRunning, setIsPolicyAgentRunning] = useState(false);
  const [schedulerStatus, setSchedulerStatus] = useState<{
    scheduler_running: boolean;
    interval_minutes: number | null;
    message: string;
  } | null>(null);

  // Filter loan accounts based on current filters and active tab
  const filteredAccounts = useMemo(() => {
    let filtered = loanAccounts.filter(account => {
      const matchesSearch = !searchTerm || 
        account.customerName.toLowerCase().includes(searchTerm.toLowerCase()) ||
        account.customerNo.toLowerCase().includes(searchTerm.toLowerCase()) ||
        account.loanId.toLowerCase().includes(searchTerm.toLowerCase());
      
      const matchesStatus = !statusFilter || account.collectionStatus === statusFilter;
      
      const matchesCollector = !collectorFilter || 
        account.collectorName?.toLowerCase().includes(collectorFilter.toLowerCase());
      
      const matchesOverdue = overdueFilter === "all" || 
        (overdueFilter === "current" && account.daysOverdue === 0) ||
        (overdueFilter === "overdue" && account.daysOverdue > 0);
      
      const matchesRiskLevel = !riskLevelFilter || account.riskLevel === riskLevelFilter;
      
      // Filter by tab - processed tab shows accounts with GOOD or EXCELLENT risk assessment (AI-processed low priority cases)
      const assessment = calculateRiskAssessment(account.cibilScore, account.riskLevel, account.daysOverdue);
      const isProcessed = assessment.level === 'GOOD' || assessment.level === 'EXCELLENT';
      
      if (activeTab === "processed") {
        return matchesSearch && matchesStatus && matchesCollector && matchesOverdue && matchesRiskLevel && isProcessed;
      }
      
      // Need Review tab shows all accounts EXCEPT processed ones
      return matchesSearch && matchesStatus && matchesCollector && matchesOverdue && matchesRiskLevel && !isProcessed;
    });
    
    // Sort by risk level priority (Red first, then Amber, then Green)
    filtered.sort((a, b) => {
      const priorityA = RISK_LEVEL_PRIORITY[a.riskLevel as keyof typeof RISK_LEVEL_PRIORITY];
      const priorityB = RISK_LEVEL_PRIORITY[b.riskLevel as keyof typeof RISK_LEVEL_PRIORITY];
      return priorityA - priorityB;
    });
    
    return filtered;
  }, [loanAccounts, searchTerm, statusFilter, collectorFilter, overdueFilter, riskLevelFilter, activeTab]);

  const selectedIds = useMemo(
    () => Object.keys(selectedRows)
      .filter(id => selectedRows[Number(id)])
      .map(Number),
    [selectedRows]
  );

  // Handle row selection
  const handleRowSelect = (id: number, checked: boolean) => {
    setSelectedRows(prev => ({ ...prev, [id]: checked }));
  };

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      const newSelection: Record<number, boolean> = {};
      filteredAccounts.forEach(account => {
        newSelection[account.id] = true;
      });
      setSelectedRows(newSelection);
    } else {
      setSelectedRows({});
    }
  };

  // Actions
  const handleLogContact = (account: LoanAccount) => {
    setSelectedAccount(account);
    setContactNote("");
    setIsContactModalOpen(true);
  };

  const saveContactNote = () => {
    if (selectedAccount && contactNote.trim()) {
      setLoanAccounts(prev => prev.map(account => 
        account.id === selectedAccount.id 
          ? { ...account, lastContactNote: contactNote.trim(), collectionStatus: 'contacted' as const }
          : account
      ));
      setIsContactModalOpen(false);
      toast.success("Contact note saved successfully");
    }
  };

  const fetchSchedulerStatus = async () => {
    try {
      const response = await fetch('/api/collection/policy-scheduler-status', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('authToken')}`
        }
      });
      
      if (response.ok) {
        const status = await response.json();
        setSchedulerStatus(status);
      }
    } catch (error) {
      console.error('Failed to fetch scheduler status:', error);
    }
  };

  const runPolicyAgent = async () => {
    setIsPolicyAgentRunning(true);
    
    try {
      const response = await fetch('/api/collection/run-policy-agent', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('authToken')}`
        }
      });
      
      if (!response.ok) {
        throw new Error('Failed to run policy agent');
      }
      
      const result = await response.json();
      
      if (result.success) {
        const { matches_found, actions_executed, errors } = result.results;
        toast.success(
          `Policy Agent completed! ${matches_found} matches found, ${actions_executed} emails sent`,
          { duration: 5000 }
        );
        
        if (errors > 0) {
          toast.error(`${errors} errors occurred during execution`, { duration: 3000 });
        }
      } else {
        throw new Error(result.message || 'Policy agent failed');
      }
      
    } catch (error) {
      console.error('Policy agent error:', error);
      toast.error('Failed to run policy agent. Please try again.');
    } finally {
      setIsPolicyAgentRunning(false);
    }
  };

  const handleSetFollowUp = (account: LoanAccount) => {
    // This would typically open a calendar/date picker
    toast.success(`Follow-up reminder set for ${account.customerName}`);
  };

  const handleGenerateLetter = (account: LoanAccount) => {
    // This would generate a dunning letter
    toast.success(`Dunning letter generated for ${account.customerName}`);
  };



  // Load data from database (automatically loads synced customer data)
  const loadData = useCallback(async () => {
    setIsLoading(true);
    try {
      // Fetch both accounts and KPIs in parallel
      const [accounts, collectionKpis, collectionMetrics] = await Promise.all([
        getLoanAccountsWithContracts({
          limit: 50,
          status: statusFilter || undefined,
          risk_level: overdueFilter !== "all" ? overdueFilter : undefined,
        }),
        getCollectionKPIs(),
        getCollectionMetrics()
      ]);
      
      setLoanAccounts(accounts);
      setKpis(collectionKpis);
      setMetrics(collectionMetrics);
      
      if (accounts.length === 0) {
        toast.success("No customer data found. Use 'Sync Sample Data' in Data Center to import data.");
      }
    } catch (error) {
      console.error("Error loading customer data:", error);
      toast.error("Failed to load customer data. Please check if sync has been completed.");
      setLoanAccounts([]);
      // Keep mock data for KPIs/metrics if API fails
      setKpis(mockKPIs);
      setMetrics(mockMetrics);
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter, overdueFilter]);

  // Load data when filters change or on initial load
  useEffect(() => {
    loadData();
    fetchSchedulerStatus();
  }, [statusFilter, overdueFilter, loadData]);

  // Fetch scheduler status periodically
  useEffect(() => {
    const interval = setInterval(fetchSchedulerStatus, 60000); // Check every minute
    return () => clearInterval(interval);
  }, []);

  const handleBatchAction = async (action: string) => {
    if (selectedIds.length === 0) {
      toast.error("Please select accounts to perform batch action");
      return;
    }

    setIsLoading(true);
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      switch (action) {
        case "generate_letters":
          toast.success(`Generated dunning letters for ${selectedIds.length} accounts`);
          break;
        case "mark_contacted":
          setLoanAccounts(prev => prev.map(account => 
            selectedIds.includes(account.id)
              ? { ...account, collectionStatus: 'contacted' as const }
              : account
          ));
          toast.success(`Marked ${selectedIds.length} accounts as contacted`);
          break;
        case "export_data":
          toast.success(`Exported data for ${selectedIds.length} accounts`);
          break;
      }
      
      setSelectedRows({});
    } catch {
      toast.error("Failed to perform batch action");
    } finally {
      setIsLoading(false);
    }
  };

  const handleRowClick = (account: LoanAccount) => {
    router.push(`/collection-cell/customer/${account.customerNo}`);
  };

  return (
    <div className="container mx-auto px-4 py-6 max-w-7xl">
      <div className="space-y-6">
      {/* Section 1: High-Level KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Receivables Due</p>
                <p className="text-2xl font-bold text-blue-600">{formatCurrency(kpis.totalReceivablesDue)}</p>
              </div>
              <IndianRupee className="h-8 w-8 text-blue-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Collected</p>
                <p className="text-2xl font-bold text-green-600">{formatCurrency(kpis.totalCollected)}</p>
              </div>
              <TrendingUp className="h-8 w-8 text-green-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Delinquency Rate</p>
                <p className="text-2xl font-bold text-red-600">{kpis.delinquencyRate}%</p>
              </div>
              <TrendingDown className="h-8 w-8 text-red-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Amount Overdue</p>
                <p className="text-2xl font-bold text-red-600">{formatCurrency(kpis.totalAmountOverdue)}</p>
              </div>
              <AlertCircle className="h-8 w-8 text-red-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Accounts Overdue</p>
                <p className="text-2xl font-bold text-orange-600">{kpis.accountsOverdue}</p>
                <div className="mt-2 space-y-1">
                  <p className="text-xs text-gray-500">Cleared: {formatCurrency(kpis.collectedCleared)}</p>
                  <p className="text-xs text-yellow-600">Pending: {formatCurrency(kpis.collectedInTransit)}</p>
                </div>
              </div>
              <Users className="h-8 w-8 text-orange-600" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Section 2: Tabs and Filters */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex gap-2">
              <Button
                size="sm"
                variant={activeTab === "collection" ? "primary" : "secondary"}
                onClick={() => setActiveTab("collection")}
              >
                Need Review
              </Button>
              <Button
                size="sm"
                variant={activeTab === "processed" ? "primary" : "secondary"}
                onClick={() => setActiveTab("processed")}
              >
                Processed ({loanAccounts.filter(account => {
                  const assessment = calculateRiskAssessment(account.cibilScore, account.riskLevel, account.daysOverdue);
                  return assessment.level === 'GOOD' || assessment.level === 'EXCELLENT';
                }).length})
              </Button>
            </div>
            <div className="flex items-center gap-2">
              {activeTab === "processed" && (
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => {
                    const matchedCount = filteredAccounts.length;
                    toast.success(`${matchedCount} matched accounts sent for bank reconciliation processing`);
                  }}
                  disabled={filteredAccounts.length === 0}
                  className="text-xs"
                >
                  Send to Bank Reconciliation
                </Button>
              )}
              <Button
                variant="ghost"
                size="sm"
                onClick={loadData}
                disabled={isLoading}
                className="text-xs"
                title="Refresh Customer Data"
              >
                <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
              <div className="flex items-center gap-2">
                {schedulerStatus && (
                  <div className="flex items-center gap-2 px-3 py-1 bg-gray-50 rounded-md border">
                    <div className={`w-2 h-2 rounded-full ${schedulerStatus.scheduler_running ? 'bg-green-500 animate-pulse' : 'bg-gray-400'}`}></div>
                    <span className="text-xs text-gray-600">
                      {schedulerStatus.scheduler_running 
                        ? `Auto-Policy: Every ${schedulerStatus.interval_minutes === 0.5 ? '30sec' : schedulerStatus.interval_minutes + 'min'}`
                        : 'Auto-Policy: Stopped'
                      }
                    </span>
                  </div>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={runPolicyAgent}
                  disabled={isPolicyAgentRunning}
                  className="text-xs"
                  title="Manually run AI Policy Agent now"
                >
                  {isPolicyAgentRunning ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Bot className="h-4 w-4" />
                  )}
                  {isPolicyAgentRunning ? "Running..." : "Run Now"}
                </Button>
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {/* Filter Bar */}
          <div className="space-y-4 mb-6">
            <div className="flex items-center space-x-2">
              <Search className="h-4 w-4 text-gray-400" />
              <Input
                placeholder="Search customers, loan IDs..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="flex-1"
              />
            </div>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
              <select
                value={riskLevelFilter}
                onChange={(e) => setRiskLevelFilter(e.target.value)}
                className="px-3 py-2 border rounded-md text-sm"
              >
                <option value="">All Risk Levels</option>
                <option value="red">Red</option>
                <option value="amber">Amber</option>
                <option value="green">Green</option>
              </select>

              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-3 py-2 border rounded-md text-sm"
              >
                <option value="">All Statuses</option>
                <option value="pending">Pending</option>
                <option value="contacted">Contacted</option>
                <option value="promise_to_pay">Promise to Pay</option>
                <option value="disputed">Disputed</option>
                <option value="cleared">Cleared</option>
              </select>

              <select
                value={overdueFilter}
                onChange={(e) => setOverdueFilter(e.target.value as "all" | "current" | "overdue")}
                className="px-3 py-2 border rounded-md text-sm"
              >
                <option value="all">All Accounts</option>
                <option value="current">Current</option>
                <option value="overdue">Overdue</option>
              </select>

              <Input
                placeholder="Filter by collector..."
                value={collectorFilter}
                onChange={(e) => setCollectorFilter(e.target.value)}
                className="text-sm"
              />

              {(searchTerm || statusFilter || collectorFilter || overdueFilter !== "all" || riskLevelFilter) && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setSearchTerm("");
                    setStatusFilter("");
                    setCollectorFilter("");
                    setOverdueFilter("all");
                    setRiskLevelFilter("");
                  }}
                  className="text-sm"
                >
                  <X className="mr-2 h-4 w-4" /> Clear
                </Button>
              )}
            </div>
          </div>

          {/* Batch Actions */}
          {selectedIds.length > 0 && (
            <div className="mb-4 p-3 bg-blue-50 rounded-lg space-y-3">
              <span className="text-sm font-medium text-blue-700 block">
                {selectedIds.length} account(s) selected
              </span>
              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => handleBatchAction("mark_contacted")}
                  disabled={isLoading}
                  className="text-xs"
                >
                  Mark Contacted
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => handleBatchAction("generate_letters")}
                  disabled={isLoading}
                  className="text-xs"
                >
                  Generate Letters
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => handleBatchAction("export_data")}
                  disabled={isLoading}
                  className="text-xs"
                >
                  <Download className="mr-1 h-3 w-3" />
                  Export
                </Button>
              </div>
            </div>
          )}

          {/* Collection Worklist Table */}
          <div className="border rounded-lg overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12">
                    <Checkbox
                      checked={selectedIds.length === filteredAccounts.length && filteredAccounts.length > 0}
                      onCheckedChange={handleSelectAll}
                    />
                  </TableHead>
                  <TableHead className="w-32">Customer ID</TableHead>
                  <TableHead className="w-48">Customer Name</TableHead>
                  <TableHead className="w-16">Contract</TableHead>
                  <TableHead className="w-32">Overdue Amount</TableHead>
                  <TableHead className="w-32">Segment</TableHead>
                  <TableHead className="w-20">EMI Pending</TableHead>
                  <TableHead className="w-20">CIBIL Risk</TableHead>
                  <TableHead className="w-16">Internal Assessment</TableHead>
                  <TableHead className="w-24">Overall Risk Assessment</TableHead>
                  <TableHead className="w-24">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center py-8">
                      <Loader2 className="h-6 w-6 animate-spin mx-auto" />
                      <p className="mt-2 text-gray-500">Loading collection data...</p>
                    </TableCell>
                  </TableRow>
                ) : filteredAccounts.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center py-8">
                      {activeTab === "processed" ? (
                        <EmptyState
                          Icon={Target}
                          title="The Processed Queue is Clear"
                          description="There are no AI-processed low priority accounts currently. Great job!"
                        />
                      ) : (
                        <EmptyState
                          Icon={CreditCard}
                          title="No accounts found"
                          description="No loan accounts match your current filters."
                        />
                      )}
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredAccounts.map((account) => (
                    <TableRow 
                      key={account.id} 
                      className="hover:bg-gray-50 cursor-pointer"
                      onClick={(e) => {
                        // Only navigate if not clicking on checkbox or action buttons
                        if (!(e.target as HTMLElement).closest('input, button')) {
                          handleRowClick(account);
                        }
                      }}
                    >
                      <TableCell>
                        <Checkbox
                          checked={selectedRows[account.id] || false}
                          onCheckedChange={(checked) => handleRowSelect(account.id, checked as boolean)}
                        />
                      </TableCell>
                      <TableCell className="text-sm font-mono">
                        {account.customerNo}
                      </TableCell>
                      <TableCell className="font-medium">
                        <Tooltip text={`${account.customerName} (${account.customerNo})`}>
                          <div>
                            <div className="truncate text-sm font-medium" style={{ maxWidth: '180px' }}>
                              {account.customerName}
                            </div>
                            <div className="text-xs text-gray-500 truncate" style={{ maxWidth: '180px' }}>
                              {account.customerNo}
                            </div>
                          </div>
                        </Tooltip>
                      </TableCell>
                      <TableCell className="text-center">
                        {account.hasContractNote ? (
                          <Tooltip text={`Contract Note ID: ${account.contractNoteId}\nEMI: ₹${account.contractEmiAmount?.toLocaleString()}\nDue Day: ${account.contractDueDay}th\nLate Fee: ${account.contractLateFeePercent}%`}>
                            <div className="flex items-center justify-center">
                              <FileText className="h-4 w-4 text-green-600" />
                            </div>
                          </Tooltip>
                        ) : (
                          <Tooltip text="No contract note uploaded">
                            <div className="flex items-center justify-center">
                              <FileText className="h-4 w-4 text-gray-300" />
                            </div>
                          </Tooltip>
                        )}
                      </TableCell>
                      <TableCell>
                        <span className={cn("font-semibold text-sm", getDaysOverdueColor(account.daysOverdue))}>
                          {account.pendingAmount ? formatCurrency(account.pendingAmount) : 
                           account.daysOverdue > 0 ? formatCurrency(account.amountDue) : "₹0"}
                        </span>
                      </TableCell>
                      <TableCell className="text-center">
                        <span className="text-xs font-medium text-gray-600">
                          {account.segment || "N/A"}
                        </span>
                      </TableCell>
                      <TableCell className="text-center">
                        <span className="text-xs font-medium text-orange-600">
                          {account.emi_pending || 0} EMIs
                        </span>
                      </TableCell>
                      <TableCell className="text-center">
                        <div className="flex items-center justify-center">
                          <div className={cn(
                            "w-3 h-3 rounded-full",
                            account.cibilScore ? (
                              account.cibilScore >= 750 ? "bg-green-500" :
                              account.cibilScore >= 700 ? "bg-amber-500" :
                              "bg-red-500"
                            ) : "bg-red-500"
                          )}></div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className={cn("w-3 h-3 rounded-full", RISK_LEVEL_COLORS[account.riskLevel as keyof typeof RISK_LEVEL_COLORS])}></div>
                      </TableCell>
                      <TableCell className="text-center">
                        {(() => {
                          const assessment = calculateRiskAssessment(account.cibilScore, account.riskLevel, account.daysOverdue);
                          return (
                            <span className={cn("text-xs font-bold px-2 py-1 rounded uppercase tracking-wide", assessment.color)}>
                              {assessment.level}
                            </span>
                          );
                        })()}
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Tooltip text="View customer profile">
                            <Button
                              size="sm"
                              variant="secondary"
                              onClick={() => handleRowClick(account)}
                              className="h-8 px-3 text-xs"
                            >
                              View
                            </Button>
                          </Tooltip>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Contact Note Modal */}
      <Modal
        isOpen={isContactModalOpen}
        onClose={() => setIsContactModalOpen(false)}
        title={`Log Contact - ${selectedAccount?.customerName}`}
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Contact Note
            </label>
            <textarea
              value={contactNote}
              onChange={(e) => setContactNote(e.target.value)}
              placeholder="Enter details of the contact..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={4}
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button
              variant="ghost"
              onClick={() => setIsContactModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              onClick={saveContactNote}
              disabled={!contactNote.trim()}
            >
              Save Note
            </Button>
          </div>
        </div>
      </Modal>


      </div>
    </div>
  );
}

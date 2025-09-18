"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { PDFPreview } from "@/components/shared/PDFPreview";
import {
  ArrowLeft,
  Phone,
  Mail,
  AlertCircle,
  FileText,
  User,
  CreditCard,
  TrendingDown,
  History,
  Flag,
  Scale,
  MessageSquare,
} from "lucide-react";
import { format, parseISO } from "date-fns";
import toast from "react-hot-toast";
import { cn } from "@/lib/utils";
import { getLoanAccountsWithContracts } from "@/lib/collection-api";

// Mock detailed customer data - would come from API
const getMockCustomerDetails = (customerNo: string) => ({
  customerId: 1001, // NEW: Customer ID
  customerNo: customerNo,
  customerName: "John Smith",
  loanId: "LN-12345",
  riskLevel: "red" as const,
  alertSummary: "3 Missed EMIs, Credit Score Dropped by 55 pts",
  
  // Loan Details
  loanDetails: {
    productType: "Personal Loan",
    originalAmount: 50000,
    currentBalance: 35000,
    principalBalance: 32000,
    interestAccrued: 3000,
    emiAmount: 1500,
    nextDueDate: "2025-08-05",
    lastPaymentDate: "2025-07-05",
    loanTenure: 36,
    remainingTenure: 24,
    interestRate: 12.5,
    daysOverdue: 9,
  },
  
  // Customer Information
  customerInfo: {
    email: "panku526154@gmail.com",
    phone: "+1-555-0123",
    address: "123 Main St, Springfield, IL",
    employmentStatus: "Employed",
    monthlyIncome: 5000,
    creditScore: 665,
    previousCreditScore: 720,
    segment: "Premium",
  },
  
  // Active Alerts
  activeAlerts: [
    {
      id: 1,
      type: "payment_missed",
      severity: "high",
      message: "EMI payment of ₹1,500 missed on 2025-08-05",
      date: "2025-08-05",
    },
    {
      id: 2,
      type: "payment_missed", 
      severity: "high",
      message: "EMI payment of ₹1,500 missed on 2025-07-05",
      date: "2025-07-05",
    },
    {
      id: 3,
      type: "payment_missed",
      severity: "high", 
      message: "EMI payment of ₹1,500 missed on 2025-06-05",
      date: "2025-06-05T00:00:00Z",
    },
    {
      id: 4,
      type: "credit_score_drop",
      severity: "medium",
      message: "Credit score dropped from 720 to 665 (-55 points)",
      date: "2025-08-01T00:00:00Z",
    },
  ],
  
  // Contract Note Information
  contractNote: {
    hasContract: true,
    contractId: 1,
    filename: `${customerNo}_contract_note.pdf`, // Dynamic filename based on customer number
    extractedData: {
      emiAmount: 1500.00,
      dueDay: 5,
      lateFeePercent: 2.0,
      defaultClause: "3 consecutive missed EMIs constitute default",
      governingLaw: "State of Maharashtra",
      interestRate: 12.5,
      loanAmount: 50000,
      tenureMonths: 36,
    },
    uploadedAt: "2025-08-01T09:00:00Z",
    processedAt: "2025-08-01T09:05:30Z",
  },
  
  // Activity History - Comprehensive timeline for high-risk customer
  activityHistory: [
    {
      id: 1,
      date: "2025-08-14T10:30:00Z",
      type: "email",
      action: "Final payment notice sent",
      performer: "Sarah Johnson",
      note: "Final notice sent for overdue EMI of ₹1,500. Legal action warning included.",
      status: "completed",
      priority: "high",
      channel: "email",
      outcome: "delivered",
    },
    {
      id: 2,
      date: "2025-08-12T09:15:00Z", 
      type: "phone",
      action: "Escalation call made",
      performer: "Mike Davis",
      note: "Spoke with customer about payment plan options. Customer agreed to partial payment by Aug 20th.",
      status: "completed",
      priority: "high",
      channel: "phone",
      outcome: "customer_response",
    },
    {
      id: 3,
      date: "2025-08-10T14:15:00Z", 
      type: "phone",
      action: "Call attempted",
      performer: "Mike Davis",
      note: "Left voicemail requesting urgent call back within 24 hours",
      status: "completed",
      priority: "medium",
      channel: "phone",
      outcome: "no_response",
    },
    {
      id: 4,
      date: "2025-08-08T09:00:00Z",
      type: "system",
      action: "Risk level escalated",
      performer: "System Auto",
      note: "Risk level changed from Amber to Red due to 3rd consecutive missed payment",
      status: "completed",
      priority: "high",
      channel: "system",
      outcome: "escalated",
    },
    {
      id: 5,
      date: "2025-08-07T16:45:00Z",
      type: "sms",
      action: "Urgent SMS sent",
      performer: "System Auto",
      note: "Urgent SMS alert sent regarding overdue payment and potential account suspension",
      status: "completed",
      priority: "high",
      channel: "sms",
      outcome: "delivered",
    },
    {
      id: 6,
      date: "2025-08-05T09:00:00Z",
      type: "payment",
      action: "Payment missed",
      performer: "System",
      note: "EMI payment of ₹1,500 not received by due date. Account marked overdue.",
      status: "failed",
      priority: "high",
      channel: "system",
      outcome: "missed_payment",
    },
    {
      id: 7,
      date: "2025-08-03T11:20:00Z",
      type: "email",
      action: "Pre-due reminder sent",
      performer: "System Auto",
      note: "2-day advance reminder sent for upcoming EMI payment with payment link",
      status: "completed",
      priority: "medium",
      channel: "email",
      outcome: "delivered",
    },
    {
      id: 8,
      date: "2025-07-28T14:30:00Z",
      type: "phone",
      action: "Customer contacted",
      performer: "Lisa Chen",
      note: "Customer reported job loss and financial hardship. Discussed restructuring options.",
      status: "completed",
      priority: "high",
      channel: "phone",
      outcome: "customer_response",
    },
    {
      id: 9,
      date: "2025-07-25T10:15:00Z",
      type: "letter",
      action: "Formal notice sent",
      performer: "Collections Team",
      note: "Formal collection notice sent via registered mail due to payment delays",
      status: "completed",
      priority: "high",
      channel: "mail",
      outcome: "delivered",
    },
    {
      id: 10,
      date: "2025-07-20T13:45:00Z",
      type: "email",
      action: "Payment plan offered",
      performer: "Collections Team",
      note: "Restructured payment plan proposal sent with reduced EMI options",
      status: "completed",
      priority: "medium",
      channel: "email",
      outcome: "delivered",
    },
    {
      id: 11,
      date: "2025-07-15T16:30:00Z",
      type: "phone",
      action: "Courtesy call made",
      performer: "Tom Wilson",
      note: "Routine follow-up call. Customer mentioned temporary financial difficulties.",
      status: "completed",
      priority: "low",
      channel: "phone",
      outcome: "customer_response",
    },
    {
      id: 12,
      date: "2025-07-10T08:00:00Z",
      type: "system",
      action: "CIBIL score updated",
      performer: "System Auto",
      note: "CIBIL score updated from 720 to 665. Credit monitoring alert triggered.",
      status: "completed",
      priority: "medium",
      channel: "system",
      outcome: "score_updated",
    },
    {
      id: 13,
      date: "2025-07-05T12:00:00Z",
      type: "payment",
      action: "Payment received",
      performer: "System",
      note: "EMI payment of ₹1,500 received successfully via bank transfer",
      status: "completed",
      priority: "low",
      channel: "system",
      outcome: "payment_received",
    },
    {
      id: 14,
      date: "2025-07-01T09:30:00Z",
      type: "email",
      action: "Monthly statement sent",
      performer: "System Auto",
      note: "Monthly account statement sent with payment history and outstanding balance details",
      status: "completed",
      priority: "low",
      channel: "email",
      outcome: "delivered",
    },
    {
      id: 15,
      date: "2025-06-28T11:15:00Z",
      type: "system",
      action: "Account review completed",
      performer: "System Auto",
      note: "Quarterly account review completed. Risk factors assessed and updated.",
      status: "completed",
      priority: "low",
      channel: "system",
      outcome: "reviewed",
    }
  ],
});

const RISK_LEVEL_COLORS = {
  red: "bg-red-500",
  amber: "bg-amber-500",
  green: "bg-green-500"
};

const ALERT_SEVERITY_COLORS = {
  high: "text-red-600 bg-red-50 border-red-200",
  medium: "text-amber-600 bg-amber-50 border-amber-200", 
  low: "text-blue-600 bg-blue-50 border-blue-200",
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

export default function CustomerProfilePage() {
  const params = useParams();
  const router = useRouter();
  const customerNo = params.customerNo as string;
  
  const [customerData, setCustomerData] = useState(() => {
    const mockData = getMockCustomerDetails(customerNo || "CUST-8801");
    return {
      ...mockData,
      activeAlerts: mockData.activeAlerts || [],
      activityHistory: mockData.activityHistory || [],
      recentActivities: [] as Array<{id: number; type: string; description: string; date: string; user: string}>
    };
  });
  const [isActionModalOpen, setIsActionModalOpen] = useState(false);
  const [selectedAction, setSelectedAction] = useState<string>("");
  const [actionNote, setActionNote] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isPDFPreviewOpen, setIsPDFPreviewOpen] = useState(false);

  // Load customer data based on customerNo from URL
  const loadCustomerData = useCallback(async () => {
    if (!customerNo) return;
    
    setIsLoading(true);
    try {
      // Fetch customer data from API using customer number
      const accounts = await getLoanAccountsWithContracts({
        limit: 50, // Get more accounts to find the right one
      });
      
      // Find the account that matches the customer number
      const account = accounts.find(acc => acc.customerNo === customerNo);
      console.log('=== CUSTOMER DATA DEBUG ===');
      console.log('Customer No:', customerNo);
      console.log('Accounts found:', accounts.length);
      console.log('Matching account:', account);
      console.log('Account contract info:', account ? {
        hasContractNote: account.hasContractNote,
        contractFilename: account.contractFilename,
        contractNoteId: account.contractNoteId
      } : 'No account found');
      
      if (account) {
        // Transform the loan account data to match our customer detail structure
        const transformedData = {
          customerId: account.customerId || account.id,
          customerNo: account.customerNo,
          customerName: account.customerName,
          loanId: account.loanId,
          riskLevel: account.riskLevel,
          alertSummary: account.alertSummary,
          
          // Loan Details
          loanDetails: {
            productType: "Personal Loan", // Default for now
            originalAmount: account.totalOutstanding * 1.5, // Estimate
            currentBalance: account.totalOutstanding,
            principalBalance: account.principalBalance,
            interestAccrued: account.interestAccrued,
            emiAmount: account.contractEmiAmount || account.amountDue,
            nextDueDate: account.nextPaymentDueDate || new Date().toISOString(),
            lastPaymentDate: account.lastPaymentDate || "2025-07-01",
            loanTenure: 60,
            remainingTenure: 24,
            interestRate: 12.5,
            daysOverdue: account.daysOverdue,
          },
          
          // Customer Info (use real data when available)
          customerInfo: {
            email: `${account.customerName.toLowerCase().replace(/\s+/g, '.')}@email.com`,
            phone: "+1 (555) 123-4567",
            address: "1234 Main Street, City, State 12345",
            employmentStatus: "Employed",
            monthlyIncome: 50000,
            creditScore: account.cibilScore || 720,
            previousCreditScore: (account.cibilScore || 720) + 30,
            segment: account.segment || "Retail",
          },
          
          // Active Alerts
          activeAlerts: [
            {
              id: 1,
              type: account.riskLevel === "red" ? "HIGH_RISK" : "PAYMENT_DUE",
              message: account.alertSummary || "No alert information available",
              severity: account.riskLevel === "red" ? "high" : account.riskLevel === "amber" ? "medium" : "low",
              date: new Date().toISOString(),
            }
          ],
          
          // Payment History (mock for now)
          paymentHistory: account.lastPaymentDate ? [
            {
              id: 1,
              date: account.lastPaymentDate,
              amount: account.contractEmiAmount || account.amountDue,
              status: "completed",
              method: "Bank Transfer",
            }
          ] : [],
          
          // Recent Activities
          recentActivities: [
            {
              id: 1,
              type: "payment_due",
              description: `Payment of ${formatCurrency(account.amountDue)} is due`,
              date: account.nextPaymentDueDate || new Date().toISOString(),
              user: "System",
            }
          ],
          
          // Activity History - Enhanced with more comprehensive data
          activityHistory: [
            {
              id: 1,
              date: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(), // 1 day ago
              type: "email",
              action: "Payment reminder sent",
              performer: "Sarah Johnson",
              note: `Payment reminder sent for overdue amount of ${formatCurrency(account.amountDue)}`,
              status: "completed",
              priority: "high",
              channel: "email",
              outcome: "delivered",
            },
            {
              id: 2,
              date: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(), // 3 days ago
              type: "phone",
              action: "Customer contacted",
              performer: "Mike Davis",
              note: "Discussed payment options and financial hardship. Customer requested 7-day extension.",
              status: "completed",
              priority: "high",
              channel: "phone",
              outcome: "customer_response",
            },
            {
              id: 3,
              date: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(), // 5 days ago
              type: "system",
              action: "Risk assessment updated",
              performer: "System Auto",
              note: `Risk level changed to ${account.riskLevel.toUpperCase()} based on payment history and CIBIL score`,
              status: "completed",
              priority: "medium",
              channel: "system",
              outcome: "escalated",
            },
            {
              id: 4,
              date: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(), // 7 days ago
              type: "sms",
              action: "SMS alert sent",
              performer: "System Auto",
              note: "Automated SMS sent regarding upcoming EMI due date",
              status: "completed",
              priority: "low",
              channel: "sms",
              outcome: "delivered",
            },
            {
              id: 5,
              date: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(), // 10 days ago
              type: "payment",
              action: account.daysOverdue > 0 ? "Payment missed" : "Payment received",
              performer: "System",
              note: account.daysOverdue > 0 
                ? `EMI payment of ${formatCurrency(account.amountDue)} not received by due date`
                : `EMI payment of ${formatCurrency(account.amountDue)} received successfully`,
              status: account.daysOverdue > 0 ? "failed" : "completed",
              priority: "high",
              channel: "system",
              outcome: account.daysOverdue > 0 ? "missed_payment" : "payment_received",
            },
            {
              id: 6,
              date: new Date(Date.now() - 12 * 24 * 60 * 60 * 1000).toISOString(), // 12 days ago
              type: "email",
              action: "Pre-due reminder sent",
              performer: "System Auto",
              note: "2-day advance reminder sent for upcoming EMI payment",
              status: "completed",
              priority: "medium",
              channel: "email",
              outcome: "delivered",
            },
            {
              id: 7,
              date: new Date(Date.now() - 15 * 24 * 60 * 60 * 1000).toISOString(), // 15 days ago
              type: "phone",
              action: "Follow-up call",
              performer: "Lisa Chen",
              note: "Routine check-in call. Customer confirmed employment status and updated contact information.",
              status: "completed",
              priority: "low",
              channel: "phone",
              outcome: "customer_response",
            },
            {
              id: 8,
              date: new Date(Date.now() - 18 * 24 * 60 * 60 * 1000).toISOString(), // 18 days ago
              type: "letter",
              action: account.riskLevel === "red" ? "Formal notice sent" : "Welcome letter sent",
              performer: "Collections Team",
              note: account.riskLevel === "red" 
                ? "Formal collection notice sent via registered mail due to payment delays"
                : "Welcome letter sent with account details and payment schedule",
              status: "completed",
              priority: account.riskLevel === "red" ? "high" : "low",
              channel: "mail",
              outcome: "delivered",
            },
            {
              id: 9,
              date: new Date(Date.now() - 20 * 24 * 60 * 60 * 1000).toISOString(), // 20 days ago
              type: "system",
              action: "Account verification",
              performer: "System",
              note: "KYC documents verified and account status updated",
              status: "completed",
              priority: "medium",
              channel: "system",
              outcome: "verified",
            },
            {
              id: 10,
              date: new Date(Date.now() - 25 * 24 * 60 * 60 * 1000).toISOString(), // 25 days ago
              type: "email",
              action: "Account statement sent",
              performer: "System Auto",
              note: "Monthly account statement sent with payment history and outstanding balance",
              status: "completed",
              priority: "low",
              channel: "email",
              outcome: "delivered",
            },
            {
              id: 11,
              date: new Date().toISOString(),
              type: "system",
              action: "Profile accessed",
              performer: "System",
              note: "Customer profile viewed from collection dashboard",
              status: "completed",
              priority: "low",
              channel: "system",
              outcome: "accessed",
            }
          ],
          
          // Contract note information
          contractNote: {
            hasContract: account.hasContractNote,
            contractId: account.contractNoteId || 0,
            filename: account.contractFilename || `${account.customerNo}_contract_note.pdf`, // Dynamic filename matching actual files
            extractedData: {
              emiAmount: account.contractEmiAmount || 1500,
              dueDay: account.contractDueDay || 5,
              lateFeePercent: account.contractLateFeePercent || 2.0,
              defaultClause: "3 consecutive missed EMIs constitute default",
              governingLaw: "State of Maharashtra",
              interestRate: 12.5,
              loanAmount: account.totalOutstanding * 1.5,
              tenureMonths: 36,
            },
            uploadedAt: new Date().toISOString(),
            processedAt: new Date().toISOString(),
          },
          
          // Has contract note (for backward compatibility)
          hasContractNote: account.hasContractNote,
          contractNoteId: account.contractNoteId,
          contractEmiAmount: account.contractEmiAmount,
          contractDueDay: account.contractDueDay,
          contractLateFeePercent: account.contractLateFeePercent,
        };
        
        setCustomerData({
          ...transformedData,
          activeAlerts: transformedData.activeAlerts || [],
          activityHistory: transformedData.activityHistory || [],
          recentActivities: transformedData.recentActivities || [],
          loanDetails: transformedData.loanDetails || {},
          customerInfo: transformedData.customerInfo || {},
          contractNote: transformedData.contractNote || { hasContract: false, extractedData: {} }
        });
      } else {
        toast.error(`Customer ${customerNo} not found`);
        // Update mock data with correct customer number
        const mockData = getMockCustomerDetails(customerNo);
        setCustomerData({
          ...mockData,
          activeAlerts: mockData.activeAlerts || [],
          activityHistory: mockData.activityHistory || [],
          recentActivities: []
        });
      }
    } catch (err) {
      console.error("Error loading customer data:", err);
      toast.error("Failed to load customer data");
      // Update mock data with correct customer number on error
      const mockData = getMockCustomerDetails(customerNo);
      setCustomerData({
        ...mockData,
        activeAlerts: mockData.activeAlerts || [],
        activityHistory: mockData.activityHistory || [],
        recentActivities: []
      });
    } finally {
      setIsLoading(false);
    }
  }, [customerNo]);

  useEffect(() => {
    loadCustomerData();
  }, [loadCustomerData]);

  // Removed automatic redirect logic - customers should stay on their detail page regardless of risk assessment

  // Get available actions based on risk level
  const getAvailableActions = (riskLevel: string) => {
    switch (riskLevel) {
      case "red":
        return [
          { id: "final_warning", label: "Send Final Warning Email", icon: Mail },
          { id: "legal_review", label: "Flag for Legal Review", icon: Flag },
        ];
      case "amber":
        return [
          { id: "reminder_email", label: "Send Reminder Email", icon: Mail },
          { id: "log_call", label: "Log a Call", icon: Phone },
        ];
      case "yellow":
        return [
          { id: "gentle_reminder", label: "Send Gentle Reminder", icon: Mail },
        ];
      default:
        return [];
    }
  };

  const handleActionClick = (actionId: string) => {
    setSelectedAction(actionId);
    setActionNote("");
    setIsActionModalOpen(true);
  };

  const handleActionSubmit = async () => {
    if (!selectedAction) return;
    
    setIsLoading(true);
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      const actionLabels: Record<string, string> = {
        final_warning: "Final warning email sent",
        legal_review: "Case flagged for legal review",
        reminder_email: "Reminder email sent", 
        log_call: "Call logged",
        gentle_reminder: "Gentle reminder sent",
      };
      
      toast.success(actionLabels[selectedAction] || "Action completed");
      
      // If flagging for legal review, redirect after action
      if (selectedAction === "legal_review") {
        setTimeout(() => {
          toast.success("Customer removed from Collection Cell and moved to Resolution Workbench");
          router.push("/collection-cell");
        }, 2000);
      }
      
      setIsActionModalOpen(false);
    } catch {
      toast.error("Failed to perform action");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container mx-auto px-4 py-6 max-w-7xl">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => router.back()}
              className="flex items-center"
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Collection Cell
            </Button>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
                <User className="h-6 w-6" />
                {customerData.customerName}
                <div className={cn("w-4 h-4 rounded-full", RISK_LEVEL_COLORS[customerData.riskLevel])}></div>
              </h1>
              <p className="text-gray-600">Customer No: {customerData.customerNo}</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Loan Details & Customer Info */}
          <div className="lg:col-span-2 space-y-6">
            {/* Loan Details */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CreditCard className="h-5 w-5" />
                  Loan Details
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
                  <div>
                    <label className="text-sm font-medium text-gray-500">Product Type</label>
                    <p className="text-sm font-semibold">{customerData.loanDetails?.productType || "N/A"}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">Loan ID</label>
                    <p className="text-sm font-semibold">{customerData.loanId}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">Original Amount</label>
                    <p className="text-sm font-semibold">{formatCurrency(customerData.loanDetails?.originalAmount || 0)}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">Current Balance</label>
                    <p className="text-sm font-semibold">{formatCurrency(customerData.loanDetails?.currentBalance || 0)}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">EMI Amount</label>
                    <p className="text-sm font-semibold">{formatCurrency(customerData.loanDetails?.emiAmount || 0)}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">Interest Rate</label>
                    <p className="text-sm font-semibold">{customerData.loanDetails?.interestRate || 0}%</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">Next Due Date</label>
                    <p className="text-sm font-semibold">
                      {customerData.loanDetails?.nextDueDate 
                        ? format(parseISO(customerData.loanDetails.nextDueDate), "MMM dd, yyyy")
                        : "Not available"}
                    </p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">Days Overdue</label>
                    <p className="text-sm font-semibold text-red-600">
                      {customerData.loanDetails?.daysOverdue || 0} days
                    </p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">Remaining Tenure</label>
                    <p className="text-sm font-semibold">
                      {customerData.loanDetails?.remainingTenure || 0} / {customerData.loanDetails?.loanTenure || 0} months
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Active Alerts */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertCircle className="h-5 w-5" />
                  Active Alerts
                </CardTitle>
                <CardDescription>
                  Events that triggered the current risk level
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {customerData.activeAlerts && customerData.activeAlerts.length > 0 ? customerData.activeAlerts.map((alert) => (
                    <div
                      key={alert.id}
                      className={cn(
                        "p-3 rounded-lg border",
                        ALERT_SEVERITY_COLORS[alert.severity as keyof typeof ALERT_SEVERITY_COLORS]
                      )}
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <p className="font-medium text-sm">{alert.message}</p>
                          <p className="text-xs opacity-75 mt-1">
                            {alert.date ? format(parseISO(alert.date), "MMM dd, yyyy") : "Recent"}
                          </p>
                        </div>
                        <Badge variant="default" className="text-xs">
                          {alert.severity}
                        </Badge>
                      </div>
                    </div>
                  )) : (
                    <p className="text-gray-500 text-sm">No active alerts</p>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Activity History */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <History className="h-5 w-5" />
                  Activity History
                </CardTitle>
                <CardDescription>
                  Past communications and actions taken
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {customerData.activityHistory && customerData.activityHistory.length > 0 ? customerData.activityHistory.map((activity) => (
                    <div key={activity.id} className="flex items-start space-x-3 p-4 bg-gray-50 rounded-lg border-l-4 border-gray-300">
                      <div className="flex-shrink-0">
                        {activity.type === "email" && <Mail className="h-4 w-4 text-blue-500 mt-1" />}
                        {activity.type === "phone" && <Phone className="h-4 w-4 text-green-500 mt-1" />}
                        {activity.type === "system" && <AlertCircle className="h-4 w-4 text-orange-500 mt-1" />}
                        {activity.type === "sms" && <MessageSquare className="h-4 w-4 text-purple-500 mt-1" />}
                        {activity.type === "payment" && <CreditCard className="h-4 w-4 text-red-500 mt-1" />}
                        {activity.type === "letter" && <FileText className="h-4 w-4 text-indigo-500 mt-1" />}
                      </div>
                      <div className="flex-1">
                        <div className="flex justify-between items-start">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <p className="font-medium text-sm">{activity.action}</p>
                              {activity.priority && (
                                <Badge 
                                  className={cn("text-xs px-2 py-0.5", {
                                    "bg-red-100 text-red-800": activity.priority === "high",
                                    "bg-yellow-100 text-yellow-800": activity.priority === "medium", 
                                    "bg-blue-100 text-blue-800": activity.priority === "low"
                                  })}
                                >
                                  {activity.priority}
                                </Badge>
                              )}
                              {activity.status && (
                                <Badge 
                                  className={cn("text-xs px-2 py-0.5", {
                                    "bg-green-100 text-green-800": activity.status === "completed",
                                    "bg-red-100 text-red-800": activity.status === "failed",
                                    "bg-gray-100 text-gray-800": activity.status === "pending"
                                  })}
                                >
                                  {activity.status}
                                </Badge>
                              )}
                            </div>
                            <p className="text-xs text-gray-600 mt-1 leading-relaxed">{activity.note}</p>
                            {activity.outcome && (
                              <div className="flex items-center gap-1 mt-2">
                                <span className="text-xs text-gray-500">Outcome:</span>
                                <span className={cn("text-xs font-medium", {
                                  "text-green-600": activity.outcome === "delivered" || activity.outcome === "customer_response" || activity.outcome === "payment_received" || activity.outcome === "verified" || activity.outcome === "reviewed",
                                  "text-red-600": activity.outcome === "no_response" || activity.outcome === "missed_payment",
                                  "text-amber-600": activity.outcome === "escalated" || activity.outcome === "score_updated",
                                  "text-blue-600": activity.outcome === "accessed"
                                })}>
                                  {activity.outcome.replace(/_/g, ' ')}
                                </span>
                              </div>
                            )}
                          </div>
                          <div className="text-right ml-4">
                            <p className="text-xs text-gray-500 font-medium">
                              {activity.date ? format(parseISO(activity.date), "MMM dd, yyyy") : "Recent"}
                            </p>
                            <p className="text-xs text-gray-500">
                              {activity.date ? format(parseISO(activity.date), "h:mm a") : ""}
                            </p>
                            <p className="text-xs text-gray-600 font-medium mt-1">{activity.performer}</p>
                            {activity.channel && (
                              <p className="text-xs text-gray-400 capitalize">{activity.channel}</p>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  )) : (
                    <p className="text-gray-500 text-sm">No activity history available</p>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Right Column - Action Panel & Customer Info */}
          <div className="space-y-6">
            {/* Action Panel */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="h-5 w-5" />
                  Action Panel
                </CardTitle>
                <CardDescription>
                  Available actions for {customerData.riskLevel?.toUpperCase() || "UNKNOWN"} risk level
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {getAvailableActions(customerData.riskLevel)?.map((action) => (
                    <Button
                      key={action.id}
                      variant="secondary"
                      className="w-full justify-start"
                      onClick={() => handleActionClick(action.id)}
                    >
                      <action.icon className="mr-2 h-4 w-4" />
                      {action.label}
                    </Button>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Customer Information */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <User className="h-5 w-5" />
                  Customer Information
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div>
                    <label className="text-sm font-medium text-gray-500">Email</label>
                    <p className="text-sm">{customerData.customerInfo?.email || "N/A"}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">Phone</label>
                    <p className="text-sm">{customerData.customerInfo?.phone || "N/A"}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">Address</label>
                    <p className="text-sm">{customerData.customerInfo?.address || "N/A"}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">Employment</label>
                    <p className="text-sm">{customerData.customerInfo?.employmentStatus || "N/A"}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">Monthly Income</label>
                    <p className="text-sm">{formatCurrency(customerData.customerInfo?.monthlyIncome || 0)}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">Segment</label>
                    <p className="text-sm font-medium">{customerData.customerInfo?.segment || "Retail"}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">Credit Score</label>
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-semibold">{customerData.customerInfo?.creditScore || "N/A"}</p>
                      <div className="flex items-center text-red-600">
                        <TrendingDown className="h-3 w-3 mr-1" />
                        <span className="text-xs">
                          (-{(customerData.customerInfo?.previousCreditScore || 0) - (customerData.customerInfo?.creditScore || 0)})
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Contract Information */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="h-5 w-5" />
                  Contract Information
                </CardTitle>
                <CardDescription>
                  {customerData.contractNote?.hasContract 
                    ? `Contract processed on ${customerData.contractNote?.processedAt ? format(parseISO(customerData.contractNote.processedAt), "MMM dd, yyyy 'at' h:mm a") : "Unknown date"}`
                    : "No contract note uploaded for this customer"
                  }
                </CardDescription>
              </CardHeader>
              <CardContent>
                {customerData.contractNote?.hasContract ? (
                  <div className="space-y-4">
                    {/* Contract File Info */}
                    <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <FileText className="h-4 w-4 text-green-600" />
                          <span className="text-sm font-medium text-green-800">
                            {customerData.contractNote?.filename || "contract.pdf"}
                          </span>
                        </div>
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => {
                            console.log('=== PDF PREVIEW BUTTON CLICKED ===');
                            console.log('Contract Note Data:', customerData.contractNote);
                            console.log('Filename to be used:', customerData.contractNote?.filename || `${customerData.customerNo}_contract_note.pdf`);
                            setIsPDFPreviewOpen(true);
                          }}
                          className="text-xs bg-white hover:bg-gray-50"
                        >
                          Preview
                        </Button>
                      </div>
                      <p className="text-xs text-green-600">
                        Uploaded: {customerData.contractNote?.uploadedAt ? format(parseISO(customerData.contractNote.uploadedAt), "MMM dd, yyyy 'at' h:mm a") : "Unknown date"}
                      </p>
                    </div>

                    {/* Extracted Contract Terms */}
                    <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
                      <div>
                        <p className="text-xs text-gray-500 uppercase tracking-wide">EMI Amount</p>
                        <p className="text-sm font-semibold">₹{customerData.contractNote?.extractedData?.emiAmount?.toLocaleString() || "0"}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500 uppercase tracking-wide">Due Day</p>
                        <p className="text-sm font-semibold">{customerData.contractNote?.extractedData?.dueDay || "N/A"}th of month</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500 uppercase tracking-wide">Late Fee</p>
                        <p className="text-sm font-semibold">{customerData.contractNote?.extractedData?.lateFeePercent || "0"}%</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500 uppercase tracking-wide">Interest Rate</p>
                        <p className="text-sm font-semibold">{customerData.contractNote?.extractedData?.interestRate || "0"}% p.a.</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500 uppercase tracking-wide">Loan Amount</p>
                        <p className="text-sm font-semibold">₹{customerData.contractNote?.extractedData?.loanAmount?.toLocaleString() || "0"}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500 uppercase tracking-wide">Tenure</p>
                        <p className="text-sm font-semibold">{customerData.contractNote?.extractedData?.tenureMonths || "0"} months</p>
                      </div>
                    </div>

                    {/* Contract Clauses */}
                    <div className="space-y-3">
                      <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                        <div className="flex items-start gap-2">
                          <Scale className="h-4 w-4 text-red-600 mt-0.5" />
                          <div>
                            <p className="text-sm font-medium text-red-800">Default Clause</p>
                            <p className="text-xs text-red-600 mt-1">
                              {customerData.contractNote?.extractedData?.defaultClause || "No default clause available"}
                            </p>
                          </div>
                        </div>
                      </div>
                      
                      {customerData.contractNote?.extractedData?.governingLaw && (
                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                          <div className="flex items-start gap-2">
                            <Scale className="h-4 w-4 text-blue-600 mt-0.5" />
                            <div>
                              <p className="text-sm font-medium text-blue-800">Governing Law</p>
                              <p className="text-xs text-blue-600 mt-1">
                                {customerData.contractNote?.extractedData?.governingLaw}
                              </p>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    <FileText className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                    <p className="text-sm">No contract note has been uploaded for this customer.</p>
                    <p className="text-xs mt-1">Upload a contract note in the Data Center to see extracted terms here.</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

      {/* Action Modal */}
      <Modal
        isOpen={isActionModalOpen}
        onClose={() => setIsActionModalOpen(false)}
        title={`${getAvailableActions(customerData.riskLevel).find(a => a.id === selectedAction)?.label}`}
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Additional Notes (Optional)
            </label>
            <textarea
              value={actionNote}
              onChange={(e) => setActionNote(e.target.value)}
              placeholder="Add any additional notes or comments..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={4}
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button
              variant="ghost"
              onClick={() => setIsActionModalOpen(false)}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button
              onClick={handleActionSubmit}
              disabled={isLoading}
              className={cn(
                selectedAction === "legal_review" ? "bg-red-600 hover:bg-red-700" : ""
              )}
            >
              {isLoading ? "Processing..." : "Confirm Action"}
            </Button>
          </div>
        </div>
      </Modal>

      {/* PDF Preview Modal */}
      {customerData.contractNote?.hasContract && (
        <PDFPreview
          isOpen={isPDFPreviewOpen}
          onClose={() => setIsPDFPreviewOpen(false)}
          filename={customerData.contractNote?.filename || `${customerData.customerNo}_contract_note.pdf`}
          title={`Contract Note - ${customerData.customerName}`}
        />
      )}
    </div>
  );
}


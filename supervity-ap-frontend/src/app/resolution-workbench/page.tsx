"use client";

import React, { useState, useMemo, useEffect } from "react";
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
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import {
  Loader2,
  Search,
  X,
  Scale,
  FileText,
  AlertTriangle,
  Clock,
  IndianRupee,
  Mail,
  MessageSquare,
  RefreshCw,
} from "lucide-react";
import toast from "react-hot-toast";
import { cn } from "@/lib/utils";
import { getLoanAccountsWithContracts } from "@/lib/collection-api";
import { getCustomerSuggestion, sendSuggestionEmail, type AISuggestion } from "@/lib/ai-suggestions-api";

// Type for escalated cases
interface EscalatedCase {
  id: number;
  customerNo: string;
  customerName: string;
  loanId: string;
  escalatedDate: string;
  escalatedBy: string;
  escalationReason: string;
  priority: "high" | "medium" | "low";
  status: "new" | "in_progress" | "pending_legal" | "resolved";
  totalOutstanding: number;
  daysOverdue: number;
  assignedTo?: string;
  lastAction?: string;
  lastActionDate?: string;
  cibilScore?: number | null;
  riskLevel?: string;
  aiSuggestion?: AISuggestion;
  isLoadingSuggestion?: boolean;
}

// Removed mock data - using real data from database

const STATUS_COLORS = {
  new: "bg-gray-100 text-gray-800",
  in_progress: "bg-blue-100 text-blue-800",
  pending_legal: "bg-orange-100 text-orange-800",
  resolved: "bg-green-100 text-green-800",
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



export default function ResolutionWorkbenchPage() {
  const [escalatedCases, setEscalatedCases] = useState<EscalatedCase[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [selectedCase, setSelectedCase] = useState<EscalatedCase | null>(null);
  const [isActionModalOpen, setIsActionModalOpen] = useState(false);
  const [actionNote, setActionNote] = useState("");
  const [actionType, setActionType] = useState("");
  const [expandedCases, setExpandedCases] = useState<Set<number>>(new Set());
  const [isEmailModalOpen, setIsEmailModalOpen] = useState(false);
  const [emailContent, setEmailContent] = useState("");
  const [emailSubject, setEmailSubject] = useState("");
  const [isSendingEmail, setIsSendingEmail] = useState(false);

  // Filter cases based on current filters
  const filteredCases = useMemo(() => {
    return escalatedCases.filter(escalatedCase => {
      const matchesSearch = !searchTerm || 
        escalatedCase.customerName.toLowerCase().includes(searchTerm.toLowerCase()) ||
        escalatedCase.customerNo.toLowerCase().includes(searchTerm.toLowerCase()) ||
        escalatedCase.loanId.toLowerCase().includes(searchTerm.toLowerCase());
      
      const matchesStatus = !statusFilter || escalatedCase.status === statusFilter;
      const matchesPriority = !priorityFilter || escalatedCase.priority === priorityFilter;
      
      return matchesSearch && matchesStatus && matchesPriority;
    });
  }, [escalatedCases, searchTerm, statusFilter, priorityFilter]);

  // Load escalated cases from database (all customers, filter by risk level)
  const loadData = async () => {
    setIsLoading(true);
    try {
      // Get all loan accounts from the database
      const accounts = await getLoanAccountsWithContracts({
        limit: 100, // Get more accounts to ensure we catch all
      });
      
      console.log('=== Resolution Workbench Debug ===');
      console.log('Total accounts loaded:', accounts.length);
      console.log('Accounts:', accounts.map(a => ({ 
        customerNo: a.customerNo, 
        name: a.customerName, 
        riskLevel: a.riskLevel,
        cibilScore: a.cibilScore 
      })));
      
      // Convert accounts that need resolution based on Risk Assessment (MODERATE, HIGH RISK, CRITICAL)
      const escalatedCases: EscalatedCase[] = accounts
        .filter(account => {
          const assessment = calculateRiskAssessment(
            account.cibilScore || null, 
            account.riskLevel || 'red', 
            account.daysOverdue
          );
          // Only include accounts that need resolution (exclude GOOD and EXCELLENT)
          return assessment.level === 'MODERATE' || assessment.level === 'HIGH RISK' || assessment.level === 'CRITICAL';
        })
        .map(account => ({
          id: account.id,
          customerNo: account.customerNo,
          customerName: account.customerName,
          loanId: account.loanId,
          escalatedDate: new Date().toISOString(),
          escalatedBy: "System Auto",
          escalationReason: account.alertSummary || "High-risk customer requiring attention",
          priority: account.totalOutstanding > 50000 ? "high" : "medium" as "high" | "medium" | "low",
          status: "new" as "new" | "in_progress" | "pending_legal" | "resolved",
          totalOutstanding: account.totalOutstanding,
          daysOverdue: account.daysOverdue,
          assignedTo: undefined,
          lastAction: undefined,
          lastActionDate: undefined,
          cibilScore: account.cibilScore,
          riskLevel: account.riskLevel,
        }));
      
      console.log('Escalated cases created:', escalatedCases.length);
      console.log('Escalated cases:', escalatedCases);
      
      setEscalatedCases(escalatedCases);
      // Only show toast for empty cases, not for successful loads to reduce noise
      if (escalatedCases.length === 0) {
        toast.error("No high-risk cases found. Please ensure customer data has been synced from Data Center.");
      }
    } catch (error: unknown) {
      console.error("Error loading escalated cases:", error);
      
      // Check if it's an authentication error
      const errorMessage = error instanceof Error ? error.message : "";
      if (errorMessage.includes('authenticated') || errorMessage.includes('401')) {
        toast.error("Authentication required. Please log in to view escalated cases.");
        // Redirect to login page after a delay
        setTimeout(() => {
          window.location.href = '/login';
        }, 2000);
      } else {
        toast.error("Failed to load escalated cases. Please check if the backend server is running and customer data has been synced.");
      }
      setEscalatedCases([]);
    } finally {
      setIsLoading(false);
    }
  };

  // Load data on initial load
  useEffect(() => {
    loadData();
  }, []);

  // Load AI suggestion for a specific case
  const loadAISuggestion = async (caseId: number) => {
    setEscalatedCases(prev => prev.map(c => 
      c.id === caseId ? { ...c, isLoadingSuggestion: true } : c
    ));

    try {
      const suggestion = await getCustomerSuggestion(caseId);
      setEscalatedCases(prev => prev.map(c => 
        c.id === caseId ? { ...c, aiSuggestion: suggestion, isLoadingSuggestion: false } : c
      ));
    } catch (error: unknown) {
      console.error("Error loading AI suggestion:", error);
      toast.error("Failed to load AI suggestion");
      setEscalatedCases(prev => prev.map(c => 
        c.id === caseId ? { ...c, isLoadingSuggestion: false } : c
      ));
    }
  };

  // Toggle case expansion and load AI suggestion if not already loaded
  const toggleCaseExpansion = (caseId: number) => {
    const newExpanded = new Set(expandedCases);
    if (newExpanded.has(caseId)) {
      newExpanded.delete(caseId);
    } else {
      newExpanded.add(caseId);
      // Load AI suggestion if not already loaded
      const caseData = escalatedCases.find(c => c.id === caseId);
      if (caseData && !caseData.aiSuggestion && !caseData.isLoadingSuggestion) {
        loadAISuggestion(caseId);
      }
    }
    setExpandedCases(newExpanded);
  };

  // Handle email sending
  const handleSendEmail = async (caseData: EscalatedCase, actionType: string) => {
    if (!caseData.aiSuggestion) {
      toast.error("AI suggestion not available");
      return;
    }

    setSelectedCase(caseData);
    setEmailSubject(caseData.aiSuggestion.suggestion.email_subject || `Payment Reminder - ${caseData.customerNo}`);
    setEmailContent(caseData.aiSuggestion.suggestion.email_content || "");
    setActionType(actionType);
    setIsEmailModalOpen(true);
  };

  // Send email with AI-generated content
  const sendEmail = async () => {
    if (!selectedCase) return;

    setIsSendingEmail(true);
    try {
      await sendSuggestionEmail(
        selectedCase.id,
        actionType,
        emailContent
      );
      
      toast.success("Email sent successfully!");
      setIsEmailModalOpen(false);
      
      // Update case status
      setEscalatedCases(prev => prev.map(c => 
        c.id === selectedCase.id 
          ? { ...c, status: "in_progress", lastAction: `Email sent: ${actionType}`, lastActionDate: new Date().toISOString() }
          : c
      ));
    } catch (error: unknown) {
      console.error("Error sending email:", error);
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      toast.error("Failed to send email: " + errorMessage);
    } finally {
      setIsSendingEmail(false);
    }
  };

  const handleActionClick = (escalatedCase: EscalatedCase, action: string) => {
    setSelectedCase(escalatedCase);
    setActionType(action);
    setActionNote("");
    setIsActionModalOpen(true);
  };



  const handleActionSubmit = async () => {
    if (!selectedCase || !actionType) return;
    
    setIsLoading(true);
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      // Update the case based on action type
      setEscalatedCases(prev => prev.map(escalatedCase => 
        escalatedCase.id === selectedCase.id 
          ? {
              ...escalatedCase,
              status: actionType === "resolve" ? "resolved" : "in_progress",
              lastAction: actionNote || `${actionType} action taken`,
              lastActionDate: new Date().toISOString(),
              assignedTo: actionType === "assign_legal" ? "Legal Team" : escalatedCase.assignedTo,
            }
          : escalatedCase
      ));
      
      const actionLabels: Record<string, string> = {
        assign_legal: "Case assigned to legal team",
        initiate_legal: "Legal proceedings initiated",
        contact_customer: "Customer contacted",
        schedule_meeting: "Meeting scheduled",
        resolve: "Case resolved successfully",
      };
      
      toast.success(actionLabels[actionType] || "Action completed");
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
          <div>
            <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
              <Scale className="h-8 w-8 text-orange-600" />
              Resolution Workbench
            </h1>
            <p className="text-gray-600 mt-1">Manage escalated loan collection cases requiring legal or senior management review</p>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Total Cases</p>
                  <p className="text-2xl font-bold text-gray-900">{escalatedCases.length}</p>
                </div>
                <FileText className="h-8 w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">High Priority</p>
                  <p className="text-2xl font-bold text-red-600">
                    {escalatedCases.filter(c => c.priority === "high").length}
                  </p>
                </div>
                <AlertTriangle className="h-8 w-8 text-red-600" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">In Progress</p>
                  <p className="text-2xl font-bold text-blue-600">
                    {escalatedCases.filter(c => c.status === "in_progress").length}
                  </p>
                </div>
                <Clock className="h-8 w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Total Outstanding</p>
                  <p className="text-2xl font-bold text-green-600">
                    {formatCurrency(escalatedCases.reduce((sum, c) => sum + c.totalOutstanding, 0))}
                  </p>
                </div>
                <IndianRupee className="h-8 w-8 text-green-600" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Escalated Cases Table */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Escalated Cases</CardTitle>
                <CardDescription>
                  Accounts requiring resolution based on Risk Assessment (MODERATE, HIGH RISK, and CRITICAL cases)
                  <br />
                  <span className="text-blue-600 font-medium">
                    Data automatically loads from database. Only accounts needing resolution appear here.
                  </span>
                </CardDescription>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={loadData}
                  disabled={isLoading}
                  className="text-xs"
                  title="Refresh Escalated Cases"
                >
                  <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
                  Refresh
                </Button>
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
              
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="px-3 py-2 border rounded-md text-sm"
                >
                  <option value="">All Statuses</option>
                  <option value="new">New</option>
                  <option value="in_progress">In Progress</option>
                  <option value="pending_legal">Pending Legal</option>
                  <option value="resolved">Resolved</option>
                </select>

                <select
                  value={priorityFilter}
                  onChange={(e) => setPriorityFilter(e.target.value)}
                  className="px-3 py-2 border rounded-md text-sm"
                >
                  <option value="">All Priorities</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>

                {(searchTerm || statusFilter || priorityFilter) && (
                <Button
                  variant="ghost"
                  size="sm"
                    onClick={() => {
                      setSearchTerm("");
                      setStatusFilter("");
                      setPriorityFilter("");
                    }}
                    className="text-sm"
                  >
                    <X className="mr-2 h-4 w-4" /> Clear
                </Button>
                )}
              </div>
            </div>

            {/* Cases Table */}
            <div className="border rounded-lg overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-48">Customer Name</TableHead>
                    <TableHead className="w-24">Risk Assessment</TableHead>
                    <TableHead className="w-32">Case Status</TableHead>
                    <TableHead className="w-32">AI Suggestion</TableHead>
                    <TableHead className="w-24">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                                    {isLoading ? (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center py-8">
                        <Loader2 className="h-6 w-6 animate-spin mx-auto" />
                        <p className="mt-2 text-gray-500">Loading escalated cases...</p>
                      </TableCell>
                    </TableRow>
                  ) : filteredCases.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center py-8">
                        <Scale className="h-12 w-12 text-gray-300 mx-auto mb-4" />
                        <h3 className="text-lg font-medium text-gray-900 mb-2">No escalated cases found</h3>
                        <p className="text-gray-500">No cases match your current filters.</p>
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredCases.map((escalatedCase) => (
                      <React.Fragment key={escalatedCase.id}>
                        <TableRow className="hover:bg-gray-50">
                          <TableCell className="font-medium">
                            <div>
                              <div className="truncate text-sm font-medium" style={{ maxWidth: '180px' }}>
                                {escalatedCase.customerName}
                              </div>
                              <div className="text-xs text-gray-500 truncate" style={{ maxWidth: '180px' }}>
                                {escalatedCase.customerNo} • {escalatedCase.loanId}
                              </div>
                              <div className="text-xs text-gray-500 truncate" style={{ maxWidth: '180px' }}>
                                {formatCurrency(escalatedCase.totalOutstanding)} • {escalatedCase.daysOverdue}d overdue
                              </div>
                            </div>
                          </TableCell>
                          <TableCell className="text-center">
                            {(() => {
                              const assessment = calculateRiskAssessment(
                                escalatedCase.cibilScore || null, 
                                escalatedCase.riskLevel || 'red', 
                                escalatedCase.daysOverdue
                              );
                              return (
                                <span className={cn("text-xs font-bold px-2 py-1 rounded uppercase tracking-wide", assessment.color)}>
                                  {assessment.level}
                                </span>
                              );
                            })()}
                          </TableCell>
                          <TableCell>
                            <Badge className={`${STATUS_COLORS[escalatedCase.status]} text-xs`}>
                              {escalatedCase.status.replace(/_/g, " ")}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-sm">
                            {escalatedCase.isLoadingSuggestion ? (
                              <div className="flex items-center gap-2">
                                <Loader2 className="h-4 w-4 animate-spin" />
                                <span className="text-xs text-gray-500">Loading AI suggestion...</span>
                              </div>
                            ) : escalatedCase.aiSuggestion ? (
                              <div className="space-y-1">
                                <div className="text-xs font-medium text-blue-600">
                                  {escalatedCase.aiSuggestion.suggestion.recommended_action}
                                </div>
                                <div className="text-xs text-gray-500">
                                  Priority: {escalatedCase.aiSuggestion.suggestion.priority_level}
                                </div>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => toggleCaseExpansion(escalatedCase.id)}
                                  className="h-6 text-xs p-1"
                                >
                                  {expandedCases.has(escalatedCase.id) ? "Hide Details" : "View Details"}
                                </Button>
                              </div>
                            ) : (
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => toggleCaseExpansion(escalatedCase.id)}
                                className="h-6 text-xs p-1"
                              >
                                Get AI Suggestion
                              </Button>
                            )}
                          </TableCell>
                          <TableCell>
                            <div className="flex gap-1">
                              {escalatedCase.aiSuggestion && (
                                <Button
                                  size="sm"
                                  variant="primary"
                                  onClick={() => handleSendEmail(escalatedCase, escalatedCase.aiSuggestion!.suggestion.recommended_action)}
                                  className="h-7 text-xs px-2"
                                >
                                  <Mail className="h-3 w-3 mr-1" />
                                  Email
                                </Button>
                              )}
                              <Button
                                size="sm"
                                variant="secondary"
                                onClick={() => {
                                  if (escalatedCase.status === "new") {
                                    handleActionClick(escalatedCase, "assign_legal");
                                  } else {
                                    handleActionClick(escalatedCase, "resolve");
                                  }
                                }}
                                className="h-7 text-xs px-2"
                              >
                                {escalatedCase.status === "new" ? "Assign" : "View"}
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                        
                        {/* Expanded AI Suggestion Details */}
                        {expandedCases.has(escalatedCase.id) && escalatedCase.aiSuggestion && (
                          <TableRow className="bg-blue-50">
                            <TableCell colSpan={5} className="p-4">
                              <div className="space-y-3">
                                <div className="flex items-center gap-2">
                                  <MessageSquare className="h-4 w-4 text-blue-600" />
                                  <span className="font-medium text-blue-900">AI Recommendation</span>
                                  <Badge className="bg-blue-100 text-blue-800 text-xs">
                                    {Math.round(escalatedCase.aiSuggestion.confidence_score * 100)}% confidence
                                  </Badge>
                                </div>
                                
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                  <div>
                                    <h4 className="text-sm font-medium text-gray-900 mb-2">Risk Assessment</h4>
                                    <p className="text-sm text-gray-700">{escalatedCase.aiSuggestion.suggestion.risk_assessment}</p>
                                  </div>
                                  
                                  <div>
                                    <h4 className="text-sm font-medium text-gray-900 mb-2">Strategy</h4>
                                    <p className="text-sm text-gray-700">{escalatedCase.aiSuggestion.suggestion.strategy}</p>
                                  </div>
                                </div>
                                
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                  <div>
                                    <h4 className="text-sm font-medium text-gray-900 mb-1">Timeline</h4>
                                    <p className="text-sm text-gray-600">{escalatedCase.aiSuggestion.suggestion.suggested_timeline}</p>
                                  </div>
                                  
                                  <div>
                                    <h4 className="text-sm font-medium text-gray-900 mb-1">Success Probability</h4>
                                    <p className="text-sm text-gray-600">{escalatedCase.aiSuggestion.suggestion.success_probability}</p>
                                  </div>
                                  
                                  <div>
                                    <h4 className="text-sm font-medium text-gray-900 mb-1">Alternative Actions</h4>
                                    <div className="flex flex-wrap gap-1">
                                      {escalatedCase.aiSuggestion.suggestion.alternative_actions?.map((action, idx) => (
                                        <Badge key={idx} className="bg-gray-100 text-gray-700 text-xs">
                                          {action}
                                        </Badge>
                                      ))}
                                    </div>
                                  </div>
                                </div>
                                
                                {escalatedCase.aiSuggestion.suggestion.notes && (
                                  <div>
                                    <h4 className="text-sm font-medium text-gray-900 mb-1">Additional Notes</h4>
                                    <p className="text-sm text-gray-600">{escalatedCase.aiSuggestion.suggestion.notes}</p>
                                  </div>
                                )}
                                
                                <div className="flex gap-2 pt-2">
                                  <Button
                                    size="sm"
                                    variant="primary"
                                    onClick={() => handleSendEmail(escalatedCase, escalatedCase.aiSuggestion!.suggestion.recommended_action)}
                                    className="text-xs"
                                  >
                                    <Mail className="h-3 w-3 mr-1" />
                                    Send AI-Generated Email
                                  </Button>
                                  
                                  {escalatedCase.aiSuggestion.suggestion.alternative_actions?.map((action, idx) => (
                                    <Button
                                      key={idx}
                                      size="sm"
                                      variant="ghost"
                                      onClick={() => handleSendEmail(escalatedCase, action)}
                                      className="text-xs"
                                    >
                                      <Mail className="h-3 w-3 mr-1" />
                                      {action}
                                    </Button>
                                  ))}
                                </div>
                              </div>
                            </TableCell>
                          </TableRow>
                        )}
                      </React.Fragment>
                    ))
                  )}
                </TableBody>
              </Table>
        </div>
          </CardContent>
        </Card>

        {/* Action Modal */}
        <Modal
          isOpen={isActionModalOpen}
          onClose={() => setIsActionModalOpen(false)}
          title={`Action: ${actionType.replace(/_/g, " ").toUpperCase()}`}
        >
          <div className="space-y-4">
            {selectedCase && (
              <div className="bg-gray-50 p-4 rounded-lg">
                <h4 className="font-medium text-gray-900 mb-2">Case Details</h4>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <span className="text-gray-500">Customer:</span> {selectedCase.customerName}
                  </div>
                  <div>
                    <span className="text-gray-500">Loan ID:</span> {selectedCase.loanId}
                  </div>
                  <div>
                    <span className="text-gray-500">Outstanding:</span> {formatCurrency(selectedCase.totalOutstanding)}
                  </div>
                  <div>
                    <span className="text-gray-500">Days Overdue:</span> {selectedCase.daysOverdue}
                  </div>
                </div>
              </div>
            )}
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Action Notes
              </label>
              <textarea
                value={actionNote}
                onChange={(e) => setActionNote(e.target.value)}
                placeholder="Enter notes about the action taken..."
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
                  actionType === "resolve" ? "bg-green-600 hover:bg-green-700" : ""
                )}
              >
                {isLoading ? "Processing..." : "Confirm Action"}
              </Button>
            </div>
          </div>
        </Modal>

        {/* Email Modal */}
        <Modal
          isOpen={isEmailModalOpen}
          onClose={() => setIsEmailModalOpen(false)}
          title="Send AI-Generated Email"
        >
          <div className="space-y-4">
            {selectedCase && (
              <div className="bg-gray-50 p-4 rounded-lg">
                <h4 className="font-medium text-gray-900 mb-2">Customer Details</h4>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <span className="text-gray-500">Customer:</span> {selectedCase.customerName}
                  </div>
                  <div>
                    <span className="text-gray-500">Customer No:</span> {selectedCase.customerNo}
                  </div>
                  <div>
                    <span className="text-gray-500">Outstanding:</span> {formatCurrency(selectedCase.totalOutstanding)}
                  </div>
                  <div>
                    <span className="text-gray-500">Action:</span> {actionType}
                  </div>
                </div>
              </div>
            )}
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Email Subject
              </label>
              <input
                type="text"
                value={emailSubject}
                onChange={(e) => setEmailSubject(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Email subject..."
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Email Content
              </label>
              <textarea
                value={emailContent}
                onChange={(e) => setEmailContent(e.target.value)}
                placeholder="AI-generated email content will appear here..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows={8}
              />
            </div>
            
            <div className="flex justify-end gap-2">
              <Button
                variant="ghost"
                onClick={() => setIsEmailModalOpen(false)}
                disabled={isSendingEmail}
              >
                Cancel
              </Button>
              <Button
                onClick={sendEmail}
                disabled={isSendingEmail || !emailContent.trim()}
                className="bg-blue-600 hover:bg-blue-700"
              >
                {isSendingEmail ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    Sending...
                  </>
                ) : (
                  <>
                    <Mail className="h-4 w-4 mr-2" />
                    Send Email
                  </>
                )}
              </Button>
            </div>
          </div>
        </Modal>
      </div>
        </div>
  );
}

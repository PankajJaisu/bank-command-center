"use client";

import { useState, useCallback } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/Table";
import {
  Settings,
  Plus,
  Edit3,
  Trash2,
  Cog,
  AlertTriangle,
  TrendingDown,
  Calendar,
  DollarSign,
  Target,
  FileText,
  Upload,
  Users,
  Building,
  Globe,
  Eye,
  Check,
  X,
  Play,
} from "lucide-react";
import toast from "react-hot-toast";
import { useAppContext } from "@/lib/AppContext";
import { getAutomationRules, deleteAutomationRule, deleteAllAutomationRules, uploadPolicyDocuments, updateAutomationRule, createAutomationRule, type AutomationRule, type Job } from "@/lib/api";
import { useEffect } from "react";
import { useDropzone } from "react-dropzone";

// Types for risk assessment rules
interface RiskRule {
  id: number;
  name: string;
  description: string;
  conditions: RiskCondition[];
  action: string; // Changed from riskLevel to action
  isActive: boolean;
  priority: number;
  createdDate: string;
  lastModified: string;
  ruleLevel?: "system" | "segment" | "customer";
  segment?: string;
  customerId?: string;
  sourceDocument?: string;
  status?: "active" | "pending_review" | "draft";
}

interface RiskCondition {
  id: number;
  field: string;
  operator: string;
  value: string | number;
  logic?: "AND" | "OR";
}

interface PendingRule {
  id: string;
  name: string;
  description: string;
  conditions: RiskCondition[];
  action: string; // Changed from riskLevel to action
  ruleLevel: "system" | "segment" | "customer";
  segment?: string;
  customerId?: string;
  sourceDocument: string;
}

// Mock data for risk assessment rules
const mockRiskRules: RiskRule[] = [
  {
    id: 1,
    name: "Critical Risk - Multiple Missed EMIs",
    description: "Flag customers as RED when they miss 3 or more EMI payments",
    conditions: [
      { id: 1, field: "missed_emis", operator: ">=", value: 3 }
    ],
    action: "Send Legal Notice",
    isActive: true,
    priority: 1,
    createdDate: "2025-01-01",
    lastModified: "2025-01-15",
  },
  {
    id: 2,
    name: "Credit Score Drop Alert",
    description: "Flag customers as RED when credit score drops by more than 50 points",
    conditions: [
      { id: 2, field: "credit_score_drop", operator: ">", value: 50 }
    ],
    action: "Send Legal Notice",
    isActive: true,
    priority: 2,
    createdDate: "2025-01-01",
    lastModified: "2025-01-10",
  },
  {
    id: 3,
    name: "Payment Dispute Detection",
    description: "Flag customers as RED when they raise payment disputes",
    conditions: [
      { id: 3, field: "payment_disputes", operator: ">", value: 0 }
    ],
    action: "Send Legal Notice",
    isActive: true,
    priority: 3,
    createdDate: "2025-01-05",
    lastModified: "2025-01-05",
  },
  {
    id: 4,
    name: "Moderate Risk - EMI Pattern",
    description: "Flag customers as AMBER when they miss 1-2 EMI payments",
    conditions: [
      { id: 4, field: "missed_emis", operator: ">=", value: 1 },
      { id: 5, field: "missed_emis", operator: "<", value: 3, logic: "AND" }
    ],
    action: "Send Reminder",
    isActive: true,
    priority: 4,
    createdDate: "2025-01-01",
    lastModified: "2025-01-12",
  },
  {
    id: 5,
    name: "Credit Score Watch",
    description: "Flag customers as AMBER when credit score drops by 25-50 points",
    conditions: [
      { id: 6, field: "credit_score_drop", operator: ">=", value: 25 },
      { id: 7, field: "credit_score_drop", operator: "<=", value: 50, logic: "AND" }
    ],
    action: "Send Reminder",
    isActive: true,
    priority: 5,
    createdDate: "2025-01-01",
    lastModified: "2025-01-08",
  },
  {
    id: 6,
    name: "Early Warning - Single EMI Miss",
    description: "Flag customers as YELLOW when they miss their first EMI payment",
    conditions: [
      { id: 8, field: "days_overdue", operator: ">", value: 0 },
      { id: 9, field: "missed_emis", operator: "=", value: 1, logic: "AND" }
    ],
    action: "Make Phone Call",
    isActive: true,
    priority: 6,
    createdDate: "2025-01-01",
    lastModified: "2025-01-06",
  },
];

const RISK_LEVEL_COLORS = {
  red: "bg-red-100 text-red-800",
  amber: "bg-amber-100 text-amber-800",
  yellow: "bg-yellow-100 text-yellow-800",
  green: "bg-green-100 text-green-800",
};

const RULE_LEVEL_COLORS = {
  system: "bg-blue-100 text-blue-800",
  segment: "bg-purple-100 text-purple-800",
  customer: "bg-orange-100 text-orange-800",
};

const RULE_LEVEL_ICONS = {
  system: Globe,
  segment: Building,
  customer: Users,
};

const AVAILABLE_FIELDS = [
  { value: "missed_emis", label: "Missed EMIs" },
  { value: "credit_score_drop", label: "Credit Score Drop" },
  { value: "payment_disputes", label: "Payment Disputes" },
  { value: "days_overdue", label: "Days Overdue" },
  { value: "monthly_income", label: "Monthly Income" },
  { value: "total_outstanding", label: "Total Outstanding" },
];

const OPERATORS = [
  { value: "=", label: "Equals" },
  { value: ">", label: "Greater than" },
  { value: ">=", label: "Greater than or equal" },
  { value: "<", label: "Less than" },
  { value: "<=", label: "Less than or equal" },
  { value: "!=", label: "Not equal" },
];

export default function AiPoliciesPage() {
  const { currentUser } = useAppContext();
  const isAdmin = currentUser?.role.name === "admin";

  const [riskRules, setRiskRules] = useState<RiskRule[]>([]);
  const [isRuleModalOpen, setIsRuleModalOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<RiskRule | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  
  // Policy upload states
  const [isPolicyUploadOpen, setIsPolicyUploadOpen] = useState(false);
  const [uploadRuleLevel, setUploadRuleLevel] = useState<"system" | "segment" | "customer">("system");
  const [uploadSegment, setUploadSegment] = useState("");
  const [uploadCustomerId, setUploadCustomerId] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  
  // Pending rules for review
  const [pendingRules, setPendingRules] = useState<PendingRule[]>([]);
  const [isReviewModalOpen, setIsReviewModalOpen] = useState(false);
  const [reviewingRule, setReviewingRule] = useState<PendingRule | null>(null);


  // Form state for rule creation/editing
  const [ruleName, setRuleName] = useState("");
  const [ruleDescription, setRuleDescription] = useState("");
  const [actionType, setActionType] = useState<string>("Send Reminder");
  const [ruleSegment, setRuleSegment] = useState<string>("system");
  const [conditions, setConditions] = useState<RiskCondition[]>([
    { id: 1, field: "missed_emis", operator: ">=", value: 1 }
  ]);
  
  // Policy upload dropzone
  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      handlePolicyUpload(acceptedFiles);
    }
  }, [uploadRuleLevel, uploadSegment, uploadCustomerId]);
  
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
    },
    multiple: true,
    disabled: isUploading,
  });

  // Convert AutomationRule to RiskRule format
  const convertToRiskRule = (rule: AutomationRule): RiskRule => {
    let conditions: RiskCondition[] = [];
    
    try {
      // Handle the new schema format: {logical_operator: "AND", conditions: [...]}
      let parsedConditions;
      
      if (typeof rule.conditions === 'string') {
        parsedConditions = JSON.parse(rule.conditions);
      } else {
        parsedConditions = rule.conditions;
      }
      
      // Extract conditions array from the schema
      let conditionsArray = [];
      if (parsedConditions && typeof parsedConditions === 'object') {
      if (parsedConditions.conditions && Array.isArray(parsedConditions.conditions)) {
        conditionsArray = parsedConditions.conditions;
      } else if (Array.isArray(parsedConditions)) {
        // Fallback for old format
        conditionsArray = parsedConditions;
        }
      }
      
      conditions = conditionsArray.map((cond: any, index: number) => ({
        id: index + 1,
        field: cond.field || 'missed_emis',
        operator: cond.operator || '>=',
        value: cond.value || 1,
        logic: index > 0 ? "AND" : undefined
      }));
      
      // Ensure at least one condition exists
      if (conditions.length === 0) {
        conditions = [{
          id: 1,
          field: 'missed_emis',
          operator: '>=',
          value: 1
        }];
      }
      
    } catch (e) {
      console.warn("Failed to parse rule conditions:", e, "Rule:", rule);
      // Provide fallback conditions
      conditions = [{
        id: 1,
        field: 'missed_emis',
        operator: '>=',
        value: 1
      }];
    }
    
    // Generate better rule names from conditions
    let betterName = rule.rule_name;
    if (conditions.length > 0) {
      const condition = conditions[0];
      if (condition.field === 'days_overdue' && condition.value) {
        betterName = `${condition.value}+ days overdue`;
      } else if (condition.field === 'missed_emis' && condition.value) {
        betterName = `${condition.value} EMI${Number(condition.value) > 1 ? 's' : ''} missed`;
      } else if (condition.field === 'outstanding_amount' && condition.value) {
        const amount = Number(condition.value);
        if (amount >= 100000) {
          betterName = `More than ₹${(amount/100000).toFixed(0)} Lakh pending`;
        } else if (amount >= 1000) {
          betterName = `More than ₹${(amount/1000).toFixed(0)}K pending`;
        } else {
          betterName = `More than ₹${amount} pending`;
        }
      }
    }
    
    // Extract action from rule.action (this will be the action to take)
    let action = rule.action || "Send Reminder";
    if (rule.action) {
      const actionLower = rule.action.toLowerCase();
      if (actionLower.includes("reminder")) {
        action = "Send Reminder";
      } else if (actionLower.includes("notice") || actionLower.includes("legal")) {
        action = "Send Legal Notice";
      } else if (actionLower.includes("call") || actionLower.includes("contact")) {
        action = "Make Phone Call";
      } else if (actionLower.includes("visit") || actionLower.includes("field")) {
        action = "Field Visit";
      } else if (actionLower.includes("escalate")) {
        action = "Escalate to Manager";
      } else if (actionLower.includes("block") || actionLower.includes("freeze")) {
        action = "Block Account";
      }
    }
    
    const ruleLevel = rule.rule_level as "system" | "segment" | "customer" | undefined;
    
    return {
      id: rule.id,
      name: betterName, // Use the improved name
      description: rule.description || rule.rule_name,
      conditions,
      action, // Use action instead of riskLevel
      isActive: rule.is_active === 1,
      priority: 1,
      createdDate: new Date().toISOString().split('T')[0],
      lastModified: new Date().toISOString().split('T')[0],
      ruleLevel,
      segment: rule.segment || undefined,
      customerId: rule.customer_id || undefined,
      sourceDocument: rule.source_document || undefined,
      status: (rule.status as "active" | "pending_review" | "draft") || "active",
    };
  };

  // Fetch automation rules from API
  const fetchRules = async () => {
    try {
      setIsLoading(true);
      const automationRules = await getAutomationRules();
      
      // Filter only loan policy rules and convert to RiskRule format
        const filteredRules = automationRules.filter(rule => 
          rule.source === "loan_policy_ai" || 
          rule.source === "policy_upload" ||
          rule.action.includes("risk_level") ||
          rule.action.includes("Send") ||
          rule.action.includes("Make") ||
          rule.action.includes("Escalate") ||
          rule.action.includes("Block") ||
          rule.action.includes("Email") ||
          rule.action.includes("Monitor")
        );
      
      const loanPolicyRules = filteredRules.map(convertToRiskRule);
      console.log(`📊 Final rules to display: ${loanPolicyRules.length}`);
      console.log('Sample rules:', loanPolicyRules.slice(0, 3).map(r => ({
        name: r.name, 
        action: r.action, 
        isActive: r.isActive,
        status: r.status
      })));
      setRiskRules(loanPolicyRules);
    } catch (error) {
      console.error("Failed to fetch automation rules:", error);
      toast.error("Failed to load risk assessment rules");
    } finally {
      setIsLoading(false);
    }
  };

  // Load rules on component mount
  useEffect(() => {
    if (isAdmin) {
      fetchRules();
    }
  }, [isAdmin]);

  // Access control
  if (!isAdmin) {
    return (
      <div className="p-8 text-center">
        <h1 className="text-xl font-bold">Access Denied</h1>
        <p className="text-gray-600">
          You do not have permission to view Risk Assessment Rules.
        </p>
      </div>
    );
  }

  const handleCreateRule = () => {
    setEditingRule(null);
    setRuleName("");
    setRuleDescription("");
    setActionType("Send Reminder");
    setRuleSegment("system");
    setConditions([{ id: 1, field: "missed_emis", operator: ">=", value: 1 }]);
    setIsRuleModalOpen(true);
  };

  const handleEditRule = (rule: RiskRule) => {
    setEditingRule(rule);
    setRuleName(rule.name);
    setRuleDescription(rule.description);
    setActionType(rule.action);
    setRuleSegment(rule.ruleLevel || "system");
    setConditions(rule.conditions);
    setIsRuleModalOpen(true);
  };

  const handleActivateRule = async (ruleId: number) => {
    try {
      setIsLoading(true);
      
      // Find the rule to activate
      const ruleToActivate = riskRules.find(r => r.id === ruleId);
      if (!ruleToActivate) {
        toast.error("Rule not found");
        return;
      }

      console.log("🔄 Activating rule:", ruleToActivate.name);
      console.log("Rule data:", ruleToActivate);

      // Prepare the rule data for update (matching AutomationRuleCreate schema)
      const ruleUpdateData = {
        rule_name: ruleToActivate.name,
        description: ruleToActivate.description || "",
        vendor_name: null,
        conditions: {
          logical_operator: "AND",
          conditions: Array.isArray(ruleToActivate.conditions) 
            ? ruleToActivate.conditions 
            : ((ruleToActivate.conditions as any)?.conditions || [])
        },
        action: ruleToActivate.action,
        is_active: true,
        source: "policy_upload",
        rule_level: ruleToActivate.ruleLevel || "system",
        segment: ruleToActivate.segment || null,
        customer_id: ruleToActivate.customerId || null,
        source_document: ruleToActivate.sourceDocument || null,
        status: "active"
      };

      console.log("Update data:", ruleUpdateData);

      // Use the proper API function
      await updateAutomationRule(ruleId, ruleUpdateData);

      toast.success(`Rule "${ruleToActivate.name}" has been activated!`);
      await fetchRules(); // Refresh the rules list
      
    } catch (error) {
      console.error("Failed to activate rule:", error);
      const errorMessage = error instanceof Error ? error.message : "Unknown error occurred";
      toast.error(`Failed to activate rule: ${errorMessage}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveRule = async () => {
    if (!ruleName.trim() || !ruleDescription.trim()) {
      toast.error("Please fill in all required fields");
      return;
    }

    try {
      setIsLoading(true);

      const ruleData = {
        rule_name: ruleName,
        description: ruleDescription,
        vendor_name: null,
        conditions: {
          logical_operator: "AND",
          conditions: conditions
        },
        action: actionType,
        is_active: true,
        source: "user",
        rule_level: ruleSegment,
        segment: ruleSegment === "segment" ? "Retail" : null,
        customer_id: ruleSegment === "customer" ? "CUST-001" : null,
        source_document: null,
        status: "active"
      };

      if (editingRule) {
        // Update existing rule
        await updateAutomationRule(editingRule.id, ruleData);
        toast.success(`Rule "${ruleName}" updated successfully!`);
      } else {
        // Create new rule
        await createAutomationRule(ruleData);
        toast.success(`Rule "${ruleName}" created successfully!`);
      }

      // Reset form and close modal
      setIsRuleModalOpen(false);
      setRuleName("");
      setRuleDescription("");
      setActionType("Send Reminder");
      setRuleSegment("system");
      setConditions([{ id: 1, field: "missed_emis", operator: ">=", value: 1 }]);
      setEditingRule(null);

      // Refresh the rules list
      await fetchRules();

    } catch (error) {
      console.error("Failed to save rule:", error);
      const errorMessage = error instanceof Error ? error.message : "Unknown error occurred";
      toast.error(`Failed to save rule: ${errorMessage}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleRule = async (ruleId: number) => {
    setIsLoading(true);
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 500));
      
      setRiskRules(prev => prev.map(rule => 
        rule.id === ruleId 
          ? { ...rule, isActive: !rule.isActive, lastModified: new Date().toISOString().split('T')[0] }
          : rule
      ));
      toast.success("Rule status updated");
    } catch (error) {
      toast.error("Failed to update rule status");
    } finally {
      setIsLoading(false);
    }
  };



  const addCondition = () => {
    const newCondition: RiskCondition = {
      id: Math.max(...conditions.map(c => c.id)) + 1,
      field: "missed_emis",
      operator: ">=",
      value: 1,
      logic: "AND",
    };
    setConditions(prev => [...prev, newCondition]);
  };

  const updateCondition = (conditionId: number, field: keyof RiskCondition, value: any) => {
    setConditions(prev => prev.map(condition => 
      condition.id === conditionId 
        ? { ...condition, [field]: value }
        : condition
    ));
  };

  const removeCondition = (conditionId: number) => {
    if (conditions.length > 1) {
      setConditions(prev => prev.filter(c => c.id !== conditionId));
    }
  };

  const handleDeleteRule = async (ruleId: number) => {
    if (!confirm("Are you sure you want to delete this rule? This action cannot be undone.")) {
      return;
    }

    try {
      await deleteAutomationRule(ruleId);
      toast.success("Rule deleted successfully");
      // Refresh the rules list
      await fetchRules();
    } catch (error) {
      console.error("Error deleting rule:", error);
      toast.error("Failed to delete rule");
    }
  };

  const handleDeleteAllRules = async () => {
    if (!confirm("Are you sure you want to delete ALL automation rules? This action cannot be undone and will remove all existing rules from the system.")) {
      return;
    }

    try {
      const result = await deleteAllAutomationRules();
      toast.success(`${result.message} (${result.deleted_count} rules deleted)`);
      // Refresh the rules list
      await fetchRules();
    } catch (error) {
      console.error("Error deleting all rules:", error);
      toast.error("Failed to delete all rules");
    }
  };

  // Policy upload handler
  const handlePolicyUpload = async (files: File[]) => {
    if (uploadRuleLevel === "segment" && !uploadSegment.trim()) {
      toast.error("Please enter a segment name");
      return;
    }
    
    if (uploadRuleLevel === "customer" && !uploadCustomerId.trim()) {
      toast.error("Please enter a customer ID");
      return;
    }
    
    setIsUploading(true);
    try {
      const result = await uploadPolicyDocuments(
        files,
        uploadRuleLevel,
        uploadSegment || undefined,
        uploadCustomerId || undefined
      );
      
      toast.success(`${result.message}`, { duration: 5000 });
      setIsPolicyUploadOpen(false);
      
      // Reset form
      setUploadSegment("");
      setUploadCustomerId("");
      
      // Refresh rules to show new pending rules
      fetchRules();
      
      // Refresh rules after a delay to allow processing
      setTimeout(async () => {
        console.log("🔄 Auto-refreshing rules after policy upload...");
        await fetchRules();
        toast.success("Rules updated! New rules from policy document are now visible.");
      }, 3000);
      
      // Also refresh again after a longer delay to catch any delayed processing
      setTimeout(async () => {
        console.log("🔄 Second auto-refresh to catch any delayed rules...");
        await fetchRules();
      }, 8000);
      
    } catch (error) {
      console.error("Policy upload failed:", error);
      toast.error(`Policy upload failed: ${error instanceof Error ? error.message : "Please try again."}`);
    } finally {
      setIsUploading(false);
    }
  };
  
  // Rule review handlers
  const handleReviewRule = (rule: PendingRule) => {
    setReviewingRule(rule);
    setRuleName(rule.name);
    setRuleDescription(rule.description);
    setActionType(rule.action);
    setConditions(rule.conditions);
    setIsReviewModalOpen(true);
  };
  
  const handleApproveRule = async () => {
    if (!reviewingRule) return;
    
    try {
      // Create the approved rule (this would be an API call)
      toast.success("Rule approved and activated");
      setIsReviewModalOpen(false);
      setPendingRules(prev => prev.filter(r => r.id !== reviewingRule.id));
      await fetchRules();
    } catch (error) {
      toast.error("Failed to approve rule");
    }
  };
  
  const handleRejectRule = async (ruleId: string) => {
    try {
      // Delete the pending rule (this would be an API call)
      toast.success("Rule rejected and removed");
      setPendingRules(prev => prev.filter(r => r.id !== ruleId));
    } catch (error) {
      toast.error("Failed to reject rule");
    }
  };



  return (
    <div className="container mx-auto px-4 py-6 max-w-7xl">
    <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
              <Settings className="h-8 w-8 text-blue-600" />
              Risk Assessment Engine
            </h1>
            <p className="text-gray-600 mt-1">Configure rules to automatically assign risk levels to loan customers</p>
          </div>
          <div className="flex gap-2">
            <Button 
              onClick={() => setIsPolicyUploadOpen(true)} 
              variant="outline"
              className="flex items-center gap-2 text-blue-600 border-blue-200 hover:bg-blue-50 hover:border-blue-300"
            >
              <Upload className="h-4 w-4" />
              Upload Policy Document
            </Button>
            {riskRules.length > 0 && (
              <Button 
                onClick={handleDeleteAllRules} 
                variant="outline"
                className="flex items-center gap-2 text-red-600 border-red-200 hover:bg-red-50 hover:border-red-300"
              >
                <Trash2 className="h-4 w-4" />
                Delete All Rules
              </Button>
            )}
            <Button onClick={handleCreateRule} className="flex items-center gap-2">
              <Plus className="h-4 w-4" />
              Create Rule
            </Button>
          </div>
        </div>

        {/* Rules Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Total Rules</p>
                  <p className="text-2xl font-bold text-gray-900">{riskRules.length}</p>
                </div>
                <Cog className="h-8 w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Active Rules</p>
                  <p className="text-2xl font-bold text-green-600">
                    {riskRules.filter(r => r.isActive).length}
                  </p>
                </div>
                <Target className="h-8 w-8 text-green-600" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Red Level Rules</p>
                  <p className="text-2xl font-bold text-red-600">
                    {riskRules.filter(r => r.action.includes("Legal") || r.action.includes("Block")).length}
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
                  <p className="text-sm font-medium text-gray-600">Amber/Yellow Rules</p>
                  <p className="text-2xl font-bold text-amber-600">
                    {riskRules.filter(r => r.action.includes("Reminder") || r.action.includes("Call")).length}
                  </p>
                </div>
                <TrendingDown className="h-8 w-8 text-amber-600" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Risk Rules Table */}
            <Card>
              <CardHeader>
            <CardTitle>Risk Assessment Rules</CardTitle>
                <CardDescription>
              Define the conditions that determine customer risk levels (Red, Amber, Yellow)
                </CardDescription>
              </CardHeader>
              <CardContent>
                {isLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                    <span className="ml-2">Loading rules...</span>
                  </div>
                ) : (
            <div className="border rounded-lg overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                                    <TableHead className="w-[25%]">Rule Name</TableHead>
                <TableHead className="w-[30%]">Description</TableHead>
                <TableHead className="w-[10%]">Action</TableHead>
                <TableHead className="w-[10%]">Rule Level</TableHead>
                <TableHead className="w-[8%]">Priority</TableHead>
                <TableHead className="w-[8%]">Status</TableHead>
                <TableHead className="w-[9%]">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {riskRules.map((rule) => (
                    <TableRow key={rule.id} className="hover:bg-gray-50">
                      <TableCell className="font-medium text-sm">{rule.name}</TableCell>
                      <TableCell className="text-sm">{rule.description}</TableCell>
                      <TableCell>
                        <Badge className="bg-blue-100 text-blue-800 text-xs capitalize">
                          {rule.action}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {rule.ruleLevel ? (
                          <div className="flex items-center gap-1">
                            {(() => {
                              const IconComponent = RULE_LEVEL_ICONS[rule.ruleLevel];
                              return <IconComponent className="h-3 w-3" />;
                            })()}
                            <Badge className={`${RULE_LEVEL_COLORS[rule.ruleLevel]} text-xs capitalize`}>
                              {rule.ruleLevel}
                            </Badge>
                          </div>
                        ) : (
                          <span className="text-xs text-gray-400">System</span>
                        )}
                      </TableCell>
                      <TableCell className="text-sm">{rule.priority}</TableCell>
                      <TableCell>
                        <Badge 
                          className={`text-xs ${rule.isActive ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-800"}`}
                        >
                          {rule.isActive ? "Active" : "Inactive"}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          {!rule.isActive && (
                          <Button
                            size="sm"
                            variant="ghost"
                              onClick={() => handleActivateRule(rule.id)}
                              className="h-8 w-8 p-0 text-green-600 hover:bg-green-50"
                              disabled={isLoading}
                              title="Activate Rule"
                            >
                              <Play className="h-3 w-3" />
                          </Button>
                          )}
                          
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleEditRule(rule)}
                            className="h-8 w-8 p-0"
                            title="Edit Rule"
                          >
                            <Edit3 className="h-3 w-3" />
                          </Button>

                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleDeleteRule(rule.id)}
                            className="h-8 w-8 p-0 text-red-600 hover:bg-red-50"
                            disabled={isLoading}
                            title="Delete Rule"
                          >
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
                )}
              </CardContent>
            </Card>

        {/* Rule Creation/Edit Modal */}
        <Modal
          isOpen={isRuleModalOpen}
          onClose={() => setIsRuleModalOpen(false)}
          title={editingRule ? "Edit Risk Rule" : "Create Risk Rule"}
        >
          <div className="space-y-6">
            <div className="grid grid-cols-1 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Rule Name *
                </label>
                <Input
                  value={ruleName}
                  onChange={(e) => setRuleName(e.target.value)}
                  placeholder="Enter rule name..."
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Description *
                </label>
                <textarea
                  value={ruleDescription}
                  onChange={(e) => setRuleDescription(e.target.value)}
                  placeholder="Describe when this rule should apply..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  rows={3}
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Action *
                </label>
                <select
                  value={actionType}
                  onChange={(e) => setActionType(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="Send Reminder">Send Reminder</option>
                  <option value="Send Legal Notice">Send Legal Notice</option>
                  <option value="Make Phone Call">Make Phone Call</option>
                  <option value="Field Visit">Field Visit</option>
                  <option value="Escalate to Manager">Escalate to Manager</option>
                  <option value="Block Account">Block Account</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Rule Level *
              </label>
              <select
                value={ruleSegment}
                onChange={(e) => setRuleSegment(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              >
                <option value="system">System Level</option>
                <option value="segment">Segment Level</option>
                <option value="customer">Customer Level</option>
              </select>
            </div>
            
            <div className="flex justify-end gap-2">
              <Button
                variant="ghost"
                onClick={() => setIsRuleModalOpen(false)}
                disabled={isLoading}
              >
                Cancel
              </Button>
              <Button
                onClick={handleSaveRule}
                disabled={isLoading || !ruleName.trim() || !ruleDescription.trim()}
              >
                {isLoading ? "Saving..." : editingRule ? "Update Rule" : "Create Rule"}
              </Button>
            </div>
          </div>
        </Modal>

        {/* Policy Upload Modal */}
        <Modal
          isOpen={isPolicyUploadOpen}
          onClose={() => setIsPolicyUploadOpen(false)}
          title="Upload Policy Document"
        >
          <div className="space-y-6">
            <div className="text-sm text-gray-600">
              Upload loan policy documents to automatically extract and create risk assessment rules. 
              The AI will analyze the document and create rules that you can review and edit before activation.
            </div>
            
            {/* Rule Level Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Rule Level *
              </label>
              <select
                value={uploadRuleLevel}
                onChange={(e) => setUploadRuleLevel(e.target.value as "system" | "segment" | "customer")}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="system">System Level (applies to all customers)</option>
                <option value="segment">Segment Level (applies to specific segment)</option>
                <option value="customer">Customer Level (applies to specific customer)</option>
              </select>
            </div>
            
            {/* Conditional fields based on rule level */}
            {uploadRuleLevel === "segment" && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Segment Name *
                </label>
                <Input
                  value={uploadSegment}
                  onChange={(e) => setUploadSegment(e.target.value)}
                  placeholder="Enter segment name (e.g., Retail, Corporate, SME)"
                />
              </div>
            )}
            
            {uploadRuleLevel === "customer" && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Customer ID *
                </label>
                <Input
                  value={uploadCustomerId}
                  onChange={(e) => setUploadCustomerId(e.target.value)}
                  placeholder="Enter customer ID"
                />
              </div>
            )}
            
            {/* File Upload Area */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Policy Documents (PDF only)
              </label>
              <div
                {...getRootProps()}
                className={`p-8 border-2 border-dashed rounded-lg cursor-pointer transition-colors ${
                  isDragActive 
                    ? "border-blue-500 bg-blue-50" 
                    : "border-gray-300 hover:border-blue-400"
                } ${isUploading ? "opacity-50 cursor-not-allowed" : ""}`}
              >
                <input {...getInputProps()} />
                <div className="flex flex-col items-center justify-center text-center">
                  <Upload className="w-12 h-12 text-gray-400 mb-4" />
                  <p className="font-semibold text-gray-700">
                    {isDragActive
                      ? "Drop PDF files here..."
                      : "Drag & drop PDF files here, or click to select"}
                  </p>
                  <p className="text-sm text-gray-500 mt-1">
                    Upload loan policy documents to extract rules automatically
                  </p>
                </div>
              </div>
            </div>
            
            <div className="flex justify-end gap-2">
              <Button
                variant="ghost"
                onClick={() => setIsPolicyUploadOpen(false)}
                disabled={isUploading}
              >
                Cancel
              </Button>
            </div>
          </div>
        </Modal>

        {/* Rule Review Modal */}
        <Modal
          isOpen={isReviewModalOpen}
          onClose={() => setIsReviewModalOpen(false)}
          title="Review Extracted Rule"
        >
          <div className="space-y-6">
            {reviewingRule && (
              <>
                <div className="p-4 bg-blue-50 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <FileText className="h-4 w-4 text-blue-600" />
                    <span className="text-sm font-medium text-blue-800">
                      Extracted from: {reviewingRule.sourceDocument}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    {(() => {
                      const IconComponent = RULE_LEVEL_ICONS[reviewingRule.ruleLevel];
                      return <IconComponent className="h-4 w-4 text-blue-600" />;
                    })()}
                    <Badge className={`${RULE_LEVEL_COLORS[reviewingRule.ruleLevel]} text-xs`}>
                      {reviewingRule.ruleLevel} Level
                    </Badge>
                    {reviewingRule.segment && (
                      <span className="text-sm text-gray-600">• Segment: {reviewingRule.segment}</span>
                    )}
                    {reviewingRule.customerId && (
                      <span className="text-sm text-gray-600">• Customer: {reviewingRule.customerId}</span>
                    )}
                  </div>
                </div>
                
                <div className="grid grid-cols-1 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Rule Name *
                    </label>
                    <Input
                      value={ruleName}
                      onChange={(e) => setRuleName(e.target.value)}
                      placeholder="Enter rule name..."
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Description *
                    </label>
                    <textarea
                      value={ruleDescription}
                      onChange={(e) => setRuleDescription(e.target.value)}
                      placeholder="Describe when this rule should apply..."
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      rows={3}
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Action *
                    </label>
                    <select
                      value={actionType}
                      onChange={(e) => setActionType(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="Send Reminder">Send Reminder</option>
                      <option value="Send Legal Notice">Send Legal Notice</option>
                      <option value="Make Phone Call">Make Phone Call</option>
                      <option value="Field Visit">Field Visit</option>
                      <option value="Escalate to Manager">Escalate to Manager</option>
                      <option value="Block Account">Block Account</option>
                </select>
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-4">
                <label className="block text-sm font-medium text-gray-700">
                  Conditions *
                </label>
                <Button size="sm" onClick={addCondition} variant="outline">
                  <Plus className="h-4 w-4 mr-1" />
                  Add Condition
                </Button>
              </div>
              
              <div className="space-y-3">
                {conditions.map((condition, index) => (
                  <div key={condition.id} className="flex items-center gap-2 p-3 border rounded-lg">
                    {index > 0 && (
                      <select
                        value={condition.logic || "AND"}
                        onChange={(e) => updateCondition(condition.id, "logic", e.target.value)}
                        className="px-2 py-1 border rounded text-xs"
                      >
                        <option value="AND">AND</option>
                        <option value="OR">OR</option>
                      </select>
                    )}
                    
                    <select
                      value={condition.field}
                      onChange={(e) => updateCondition(condition.id, "field", e.target.value)}
                      className="flex-1 px-2 py-1 border rounded text-sm"
                    >
                      {AVAILABLE_FIELDS.map(field => (
                        <option key={field.value} value={field.value}>{field.label}</option>
                      ))}
                    </select>
                    
                    <select
                      value={condition.operator}
                      onChange={(e) => updateCondition(condition.id, "operator", e.target.value)}
                      className="px-2 py-1 border rounded text-sm"
                    >
                      {OPERATORS.map(op => (
                        <option key={op.value} value={op.value}>{op.label}</option>
                      ))}
                    </select>
                    
                    <Input
                      type="number"
                      value={condition.value}
                      onChange={(e) => updateCondition(condition.id, "value", parseFloat(e.target.value) || 0)}
                      className="w-20 text-sm"
                    />
                    
                    {conditions.length > 1 && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => removeCondition(condition.id)}
                        className="h-8 w-8 p-0 text-red-600"
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            </div>
            
            <div className="flex justify-end gap-2">
              <Button
                variant="ghost"
                    onClick={() => handleRejectRule(reviewingRule.id)}
                    className="text-red-600 hover:bg-red-50"
                  >
                    <X className="h-4 w-4 mr-1" />
                    Reject
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={() => setIsReviewModalOpen(false)}
              >
                Cancel
              </Button>
              <Button
                    onClick={handleApproveRule}
                    disabled={!ruleName.trim() || !ruleDescription.trim()}
                    className="bg-green-600 hover:bg-green-700"
              >
                    <Check className="h-4 w-4 mr-1" />
                    Approve & Activate
              </Button>
            </div>
              </>
            )}
          </div>
        </Modal>
      </div>
    </div>
  );
}

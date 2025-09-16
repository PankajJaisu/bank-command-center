"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { 
  User, 
  FileText, 
  DollarSign, 
  Calendar, 
  AlertTriangle, 
  CheckCircle,
  Info,
  Phone,
  Mail,
  MapPin,
  CreditCard,
  Building
} from "lucide-react";
import { getCustomer, getCustomerContractTerms } from "@/lib/api";
import toast from "react-hot-toast";

interface ContractTerms {
  emi_amount?: number;
  due_day?: number;
  late_fee_percent?: number;
  default_clause?: string;
  governing_law?: string;
  interest_rate?: number;
  loan_amount?: number;
  tenure_months?: number;
}

interface CBSData {
  emi_amount?: number;
  due_day?: number;
  outstanding_amount?: number;
  risk_level?: string;
  last_payment_date?: string;
}

interface CustomerProfileData {
  customer_id: number;
  customer_no: string;
  customer_name: string;
  contract_terms: ContractTerms;
  cbs_data: CBSData;
}

interface Customer {
  id: number;
  customer_no: string;
  name: string;
  email?: string;
  phone?: string;
  address?: string;
  cbs_risk_level?: string;
  cbs_emi_amount?: number;
  cbs_due_day?: number;
  cbs_outstanding_amount?: number;
  cbs_last_payment_date?: string;
  contract_note?: {
    contract_emi_amount?: number;
    contract_due_day?: number;
    contract_late_fee_percent?: number;
    contract_default_clause?: string;
    contract_governing_law?: string;
    contract_interest_rate?: number;
    contract_loan_amount?: number;
    contract_tenure_months?: number;
  };
}

interface CustomerProfileProps {
  customerId: number;
}

export function CustomerProfile({ customerId }: CustomerProfileProps) {
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [contractTerms, setContractTerms] = useState<CustomerProfileData | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchCustomerData = async () => {
    try {
      setLoading(true);
      const [customerResponse, contractResponse] = await Promise.all([
        getCustomer(customerId),
        getCustomerContractTerms(customerId),
      ]);

      setCustomer(customerResponse);
      setContractTerms(contractResponse);
    } catch (error) {
      console.error("Error fetching customer data:", error);
      toast.error("Failed to load customer information");
    } finally {
      setLoading(false);
    }
  };

  const getRiskLevelColor = (riskLevel?: string) => {
    switch (riskLevel) {
      case "RED":
        return "bg-red-100 text-red-800 border-red-200";
      case "AMBER":
        return "bg-yellow-100 text-yellow-800 border-yellow-200";
      case "GREEN":
        return "bg-green-100 text-green-800 border-green-200";
      default:
        return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

  const formatCurrency = (amount?: number) => {
    if (!amount) return "N/A";
    return `₹${amount.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return "N/A";
    return new Date(dateString).toLocaleDateString("en-IN");
  };

  const hasDataMismatch = (cbsValue?: number, contractValue?: number) => {
    if (!cbsValue || !contractValue) return false;
    return Math.abs(cbsValue - contractValue) > 0.01;
  };

  useEffect(() => {
    fetchCustomerData();
  }, [customerId]);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse">
          <div className="h-32 bg-gray-200 rounded-lg mb-6"></div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="h-64 bg-gray-200 rounded-lg"></div>
            <div className="h-64 bg-gray-200 rounded-lg"></div>
          </div>
        </div>
      </div>
    );
  }

  if (!customer || !contractTerms) {
    return (
      <Card>
        <CardContent className="p-8 text-center">
          <AlertTriangle className="h-12 w-12 text-yellow-500 mx-auto mb-4" />
          <p className="text-gray-600">Customer information not found</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Customer Header */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-blue-100 rounded-lg">
                <User className="h-8 w-8 text-blue-600" />
              </div>
              <div>
                <CardTitle className="text-2xl">{customer.name}</CardTitle>
                <CardDescription className="text-lg">
                  Customer No: {customer.customer_no}
                </CardDescription>
                <div className="flex items-center gap-2 mt-2">
                  {customer.cbs_risk_level && (
                    <Badge 
                      variant="outline" 
                      className={getRiskLevelColor(customer.cbs_risk_level)}
                    >
                      Risk Level: {customer.cbs_risk_level}
                    </Badge>
                  )}
                </div>
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {customer.email && (
              <div className="flex items-center gap-2">
                <Mail className="h-4 w-4 text-gray-500" />
                <span className="text-sm">{customer.email}</span>
              </div>
            )}
            {customer.phone && (
              <div className="flex items-center gap-2">
                <Phone className="h-4 w-4 text-gray-500" />
                <span className="text-sm">{customer.phone}</span>
              </div>
            )}
            {customer.address && (
              <div className="flex items-center gap-2">
                <MapPin className="h-4 w-4 text-gray-500" />
                <span className="text-sm">{customer.address}</span>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Key Contract Terms */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-green-600" />
              Key Contract Terms
            </CardTitle>
            <CardDescription>
              Terms extracted from the contract document
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {Object.keys(contractTerms.contract_terms).length === 0 ? (
              <div className="text-center py-4">
                <Info className="h-8 w-8 text-gray-400 mx-auto mb-2" />
                <p className="text-gray-500 text-sm">No contract terms available</p>
              </div>
            ) : (
              <>
                {/* EMI Amount */}
                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-2">
                    <DollarSign className="h-4 w-4 text-green-600" />
                    <span className="font-medium">EMI Amount</span>
                    {hasDataMismatch(customer.cbs_emi_amount, contractTerms.contract_terms.emi_amount) && (
                      <AlertTriangle className="h-4 w-4 text-red-500" title="Mismatch with CBS data" />
                    )}
                  </div>
                  <span className="font-mono">
                    {formatCurrency(contractTerms.contract_terms.emi_amount)}
                  </span>
                </div>

                {/* Due Day */}
                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-blue-600" />
                    <span className="font-medium">Due Day</span>
                    {hasDataMismatch(customer.cbs_due_day, contractTerms.contract_terms.due_day) && (
                      <AlertTriangle className="h-4 w-4 text-red-500" title="Mismatch with CBS data" />
                    )}
                  </div>
                  <span className="font-mono">
                    {contractTerms.contract_terms.due_day ? `${contractTerms.contract_terms.due_day}th of month` : "N/A"}
                  </span>
                </div>

                {/* Late Fee */}
                {contractTerms.contract_terms.late_fee_percent && (
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-orange-600" />
                      <span className="font-medium">Late Fee</span>
                    </div>
                    <span className="font-mono">{contractTerms.contract_terms.late_fee_percent}%</span>
                  </div>
                )}

                {/* Interest Rate */}
                {contractTerms.contract_terms.interest_rate && (
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center gap-2">
                      <CreditCard className="h-4 w-4 text-purple-600" />
                      <span className="font-medium">Interest Rate</span>
                    </div>
                    <span className="font-mono">{contractTerms.contract_terms.interest_rate}% p.a.</span>
                  </div>
                )}

                {/* Loan Amount */}
                {contractTerms.contract_terms.loan_amount && (
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center gap-2">
                      <Building className="h-4 w-4 text-indigo-600" />
                      <span className="font-medium">Loan Amount</span>
                    </div>
                    <span className="font-mono">{formatCurrency(contractTerms.contract_terms.loan_amount)}</span>
                  </div>
                )}

                {/* Tenure */}
                {contractTerms.contract_terms.tenure_months && (
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center gap-2">
                      <Calendar className="h-4 w-4 text-teal-600" />
                      <span className="font-medium">Tenure</span>
                    </div>
                    <span className="font-mono">{contractTerms.contract_terms.tenure_months} months</span>
                  </div>
                )}

                {/* Default Clause */}
                {contractTerms.contract_terms.default_clause && (
                  <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                    <div className="flex items-start gap-2 mb-2">
                      <AlertTriangle className="h-4 w-4 text-red-600 mt-0.5" />
                      <span className="font-medium text-red-800">Default Clause</span>
                    </div>
                    <p className="text-sm text-red-700">{contractTerms.contract_terms.default_clause}</p>
                  </div>
                )}

                {/* Governing Law */}
                {contractTerms.contract_terms.governing_law && (
                  <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                    <div className="flex items-center gap-2 mb-1">
                      <Building className="h-4 w-4 text-blue-600" />
                      <span className="font-medium text-blue-800">Governing Law</span>
                    </div>
                    <p className="text-sm text-blue-700">{contractTerms.contract_terms.governing_law}</p>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>

        {/* CBS Data */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Building className="h-5 w-5 text-blue-600" />
              CBS Data
            </CardTitle>
            <CardDescription>
              Current banking system information
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* EMI Amount */}
            <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
              <div className="flex items-center gap-2">
                <DollarSign className="h-4 w-4 text-blue-600" />
                <span className="font-medium">EMI Amount</span>
              </div>
              <span className="font-mono">{formatCurrency(customer.cbs_emi_amount)}</span>
            </div>

            {/* Due Day */}
            <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
              <div className="flex items-center gap-2">
                <Calendar className="h-4 w-4 text-blue-600" />
                <span className="font-medium">Due Day</span>
              </div>
              <span className="font-mono">
                {customer.cbs_due_day ? `${customer.cbs_due_day}th of month` : "N/A"}
              </span>
            </div>

            {/* Outstanding Amount */}
            <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
              <div className="flex items-center gap-2">
                <CreditCard className="h-4 w-4 text-blue-600" />
                <span className="font-medium">Outstanding</span>
              </div>
              <span className="font-mono">{formatCurrency(customer.cbs_outstanding_amount)}</span>
            </div>

            {/* Last Payment */}
            <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
              <div className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-blue-600" />
                <span className="font-medium">Last Payment</span>
              </div>
              <span className="font-mono">{formatDate(customer.cbs_last_payment_date)}</span>
            </div>

            {/* Risk Level */}
            <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-blue-600" />
                <span className="font-medium">Risk Level</span>
              </div>
              <Badge 
                variant="outline" 
                className={getRiskLevelColor(customer.cbs_risk_level)}
              >
                {customer.cbs_risk_level || "UNKNOWN"}
              </Badge>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

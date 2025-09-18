"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/Tabs";
import { Textarea } from "@/components/ui/Textarea";
import { Input } from "@/components/ui/Input";
import {
  User,
  Phone,
  Mail,
  Calendar,
  AlertCircle,
  CheckCircle,
  Clock,
  FileText,
  CreditCard,
  TrendingDown,
  Save,
  Send,
} from "lucide-react";
import { format } from "date-fns";
import toast from "react-hot-toast";

interface CustomerAccount {
  id: number;
  customerNo: string;
  customerName: string;
  loanId: string;
  amountDue: number;
  daysOverdue: number;
  riskLevel: string;
  lastContactDate: string;
  nextPaymentDue: string;
  totalOutstanding: number;
  contactInfo: {
    phone: string;
    email: string;
    address: string;
  };
  loanDetails: {
    loanType: string;
    emiAmount: number;
    tenure: number;
    interestRate: number;
  };
  paymentHistory: Array<{
    date: string;
    amount: number;
    status: string;
  }>;
}

interface CollectionWorkbenchProps {
  accountId?: string;
}

export const CollectionWorkbench = ({ accountId }: CollectionWorkbenchProps) => {
  const [account, setAccount] = useState<CustomerAccount | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("overview");
  const [notes, setNotes] = useState("");
  const [contactNotes, setContactNotes] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  // Mock data - replace with actual API call
  const mockAccount: CustomerAccount = {
    id: 1,
    customerNo: "CUST-8801",
    customerName: "Rajesh Kumar",
    loanId: "LN-78001",
    amountDue: 15000,
    daysOverdue: 15,
    riskLevel: "amber",
    lastContactDate: "2025-09-10",
    nextPaymentDue: "2025-09-20",
    totalOutstanding: 185000,
    contactInfo: {
      phone: "+91 98765 43210",
      email: "rajesh.kumar@email.com",
      address: "123 MG Road, Bangalore, Karnataka 560001"
    },
    loanDetails: {
      loanType: "Personal Loan",
      emiAmount: 15000,
      tenure: 24,
      interestRate: 12.5
    },
    paymentHistory: [
      { date: "2025-08-15", amount: 15000, status: "paid" },
      { date: "2025-07-15", amount: 15000, status: "paid" },
      { date: "2025-06-15", amount: 15000, status: "paid" },
    ]
  };

  useEffect(() => {
    // Simulate API call
    setTimeout(() => {
      setAccount(mockAccount);
      setIsLoading(false);
    }, 1000);
  }, [accountId]);

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

  const handleSaveNotes = async () => {
    setIsSaving(true);
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      toast.success("Notes saved successfully");
    } catch (error) {
      toast.error("Failed to save notes");
    } finally {
      setIsSaving(false);
    }
  };

  const handleContactAction = async (action: string) => {
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      toast.success(`${action} logged successfully`);
      setContactNotes("");
    } catch (error) {
      toast.error(`Failed to log ${action}`);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading customer account...</p>
        </div>
      </div>
    );
  }

  if (!account) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-gray-900 mb-2">Account Not Found</h3>
        <p className="text-gray-600">The requested customer account could not be found.</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{account.customerName}</h1>
            <div className="flex items-center gap-4 mt-2 text-sm text-gray-600">
              <span>Customer: {account.customerNo}</span>
              <span>Loan: {account.loanId}</span>
              <Badge className={getRiskBadgeColor(account.riskLevel)}>
                {account.riskLevel.toUpperCase()} RISK
              </Badge>
            </div>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-red-600">
              ₹{account.amountDue.toLocaleString()}
            </div>
            <div className="text-sm text-gray-600">
              {account.daysOverdue} days overdue
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="contact">Contact & Actions</TabsTrigger>
          <TabsTrigger value="payment-history">Payment History</TabsTrigger>
          <TabsTrigger value="notes">Notes & Documentation</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Account Summary */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CreditCard className="h-5 w-5" />
                  Account Summary
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between">
                  <span className="text-gray-600">Total Outstanding:</span>
                  <span className="font-semibold">₹{account.totalOutstanding.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">EMI Amount:</span>
                  <span className="font-semibold">₹{account.loanDetails.emiAmount.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Next Payment Due:</span>
                  <span className="font-semibold">{format(new Date(account.nextPaymentDue), 'MMM dd, yyyy')}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Loan Type:</span>
                  <span className="font-semibold">{account.loanDetails.loanType}</span>
                </div>
              </CardContent>
            </Card>

            {/* Contact Information */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <User className="h-5 w-5" />
                  Contact Information
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-3">
                  <Phone className="h-4 w-4 text-gray-400" />
                  <span>{account.contactInfo.phone}</span>
                </div>
                <div className="flex items-center gap-3">
                  <Mail className="h-4 w-4 text-gray-400" />
                  <span>{account.contactInfo.email}</span>
                </div>
                <div className="flex items-start gap-3">
                  <User className="h-4 w-4 text-gray-400 mt-1" />
                  <span className="text-sm">{account.contactInfo.address}</span>
                </div>
                <div className="flex items-center gap-3">
                  <Calendar className="h-4 w-4 text-gray-400" />
                  <span className="text-sm">Last Contact: {format(new Date(account.lastContactDate), 'MMM dd, yyyy')}</span>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="contact" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Quick Actions */}
            <Card>
              <CardHeader>
                <CardTitle>Quick Actions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <Button 
                  className="w-full justify-start" 
                  variant="outline"
                  onClick={() => handleContactAction("Phone Call")}
                >
                  <Phone className="h-4 w-4 mr-2" />
                  Log Phone Call
                </Button>
                <Button 
                  className="w-full justify-start" 
                  variant="outline"
                  onClick={() => handleContactAction("Email Sent")}
                >
                  <Mail className="h-4 w-4 mr-2" />
                  Send Email Reminder
                </Button>
                <Button 
                  className="w-full justify-start" 
                  variant="outline"
                  onClick={() => handleContactAction("SMS Sent")}
                >
                  <Send className="h-4 w-4 mr-2" />
                  Send SMS
                </Button>
              </CardContent>
            </Card>

            {/* Contact Notes */}
            <Card>
              <CardHeader>
                <CardTitle>Contact Notes</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <Textarea
                  placeholder="Enter contact notes or follow-up details..."
                  value={contactNotes}
                  onChange={(e) => setContactNotes(e.target.value)}
                  className="min-h-[120px]"
                />
                <Button 
                  onClick={() => handleContactAction("Contact Note")}
                  disabled={!contactNotes.trim()}
                  className="w-full"
                >
                  <Save className="h-4 w-4 mr-2" />
                  Save Contact Notes
                </Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="payment-history" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Payment History</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {account.paymentHistory.map((payment, index) => (
                  <div key={index} className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className={`h-3 w-3 rounded-full ${
                        payment.status === 'paid' ? 'bg-green-500' : 'bg-red-500'
                      }`} />
                      <div>
                        <div className="font-medium">{format(new Date(payment.date), 'MMM dd, yyyy')}</div>
                        <div className="text-sm text-gray-600 capitalize">{payment.status}</div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-semibold">₹{payment.amount.toLocaleString()}</div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="notes" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Account Notes & Documentation</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Textarea
                placeholder="Add notes about this customer account, collection strategy, or important details..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className="min-h-[200px]"
              />
              <Button 
                onClick={handleSaveNotes}
                disabled={isSaving || !notes.trim()}
              >
                <Save className="h-4 w-4 mr-2" />
                {isSaving ? "Saving..." : "Save Notes"}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

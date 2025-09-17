"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Textarea } from "@/components/ui/Textarea";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { User, Phone, Mail, Bot, AlertTriangle, ArrowLeft, Send } from "lucide-react";
import toast from "react-hot-toast";
import { logWorkbenchAction, escalateCaseByEmail, type WorkbenchCase } from "@/lib/collection-api";

interface CollectionWorkbenchProps {
  customerNo: string;
  onClose: () => void;
}

export const CollectionWorkbench = ({ customerNo, onClose }: CollectionWorkbenchProps) => {
  const [customer, setCustomer] = useState<WorkbenchCase | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  
  // Modals state
  const [isLogActionModalOpen, setIsLogActionModalOpen] = useState(false);
  const [isEscalateModalOpen, setIsEscalateModalOpen] = useState(false);

  // Forms state
  const [actionNote, setActionNote] = useState("");
  const [escalationEmail, setEscalationEmail] = useState({
      to: "legal-collections@bank.com", // Default internal team
      subject: "",
      body: ""
  });

  useEffect(() => {
    const fetchCustomer = async () => {
      setIsLoading(true);
      try {
        // For now, we'll simulate fetching customer data
        // In a real implementation, you'd call an API to get full customer details
        const mockCustomer: WorkbenchCase = {
          id: 1,
          customer_no: customerNo,
          name: "Loading...",
          segment: null,
          risk_level: null,
          ai_suggested_action: null,
          cbs_outstanding_amount: null,
          email: null,
          phone: null,
          address: null,
          cbs_emi_amount: null,
          pending_amount: null,
          emi_pending: null,
        };
        
        setCustomer(mockCustomer);
        
        // Pre-populate escalation email template
        setEscalationEmail(prev => ({
            ...prev,
            subject: `Action Required: Case ${customerNo} - Customer Review`,
            body: `Hi Team,\n\nPlease review the following case:\n\nCustomer: ${customerNo}\nRisk Level: High/Medium\n\nPlease advise on the next steps.\n\nThanks,\n[Your Name]`
        }));
      } catch {
        toast.error("Failed to load customer details.");
        onClose();
      } finally {
        setIsLoading(false);
      }
    };
    fetchCustomer();
  }, [customerNo, onClose]);

  const handleLogAction = async () => {
    if (!actionNote.trim()) {
        toast.error("Action note cannot be empty.");
        return;
    }
    try {
        await logWorkbenchAction(customerNo, "Manual Action", actionNote);
        toast.success("Action logged successfully.");
        onClose(); // Close detail view and refresh list
    } catch {
        toast.error("Failed to log action.");
    }
  };

  const handleSendEscalation = async () => {
    try {
        await escalateCaseByEmail(customerNo, {
            to_email: escalationEmail.to,
            subject: escalationEmail.subject,
            body: escalationEmail.body,
        });
        toast.success(`Escalation email sent to ${escalationEmail.to}`);
        onClose(); // Close detail view and refresh list
    } catch {
        toast.error("Failed to send escalation email.");
    }
  };

  if (isLoading || !customer) {
    return <div className="p-6">Loading customer details...</div>;
  }

  return (
    <div className="space-y-6">
        <Button variant="ghost" onClick={onClose}>
            <ArrowLeft className="h-4 w-4 mr-2" /> Back to Queue
        </Button>
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left Column: Customer & AI Info */}
            <div className="lg:col-span-2 space-y-6">
                <Card>
                    <CardHeader>
                        <CardTitle>{customer.name || customerNo}</CardTitle>
                        <CardDescription>
                            Customer No: {customer.customer_no} | Segment: {customer.segment || "N/A"}
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="flex items-center gap-2">
                                <User className="h-4 w-4 text-gray-500" />
                                <span className="text-sm">
                                    Risk Level: <Badge className={
                                        customer.risk_level === "High" ? "bg-red-100 text-red-800" :
                                        customer.risk_level === "Medium" ? "bg-yellow-100 text-yellow-800" :
                                        "bg-gray-100 text-gray-800"
                                    }>{customer.risk_level || "Unknown"}</Badge>
                                </span>
                            </div>
                            <div className="flex items-center gap-2">
                                <Mail className="h-4 w-4 text-gray-500" />
                                <span className="text-sm">{customer.email || "No email"}</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <Phone className="h-4 w-4 text-gray-500" />
                                <span className="text-sm">{customer.phone || "No phone"}</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <AlertTriangle className="h-4 w-4 text-gray-500" />
                                <span className="text-sm">
                                    Outstanding: ₹{customer.cbs_outstanding_amount?.toLocaleString('en-IN') || 'N/A'}
                                </span>
                            </div>
                        </div>
                        
                        {customer.address && (
                            <div className="pt-2 border-t">
                                <p className="text-sm text-gray-600">
                                    <strong>Address:</strong> {customer.address}
                                </p>
                            </div>
                        )}
                    </CardContent>
                </Card>
                
                <Card className="border-blue-400 bg-blue-50">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-blue-800">
                            <Bot className="h-6 w-6" /> AI Suggested Action
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <p className="text-lg font-semibold text-blue-900">
                            {customer.ai_suggested_action || "No specific action suggested"}
                        </p>
                        <p className="text-sm text-blue-700 mt-2">
                            This recommendation is based on the customer's risk profile, payment history, and current outstanding amount.
                        </p>
                    </CardContent>
                </Card>
            </div>

            {/* Right Column: Action Panel */}
            <div className="space-y-6">
                <Card>
                    <CardHeader>
                        <CardTitle>Action Panel</CardTitle>
                        <CardDescription>
                            Choose how to handle this case
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                        <Button 
                            className="w-full" 
                            onClick={() => setIsLogActionModalOpen(true)}
                        >
                            Log Manual Action
                        </Button>
                        <Button 
                            className="w-full" 
                            variant="outline" 
                            onClick={() => setIsEscalateModalOpen(true)}
                        >
                            <Mail className="h-4 w-4 mr-2"/> Escalate via Email
                        </Button>
                    </CardContent>
                </Card>
                
                {/* Quick Stats */}
                <Card>
                    <CardHeader>
                        <CardTitle className="text-sm">Quick Stats</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                        <div className="flex justify-between text-sm">
                            <span>EMI Amount:</span>
                            <span>₹{customer.cbs_emi_amount?.toLocaleString('en-IN') || 'N/A'}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                            <span>Pending Amount:</span>
                            <span>₹{customer.pending_amount?.toLocaleString('en-IN') || 'N/A'}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                            <span>EMIs Pending:</span>
                            <span>{customer.emi_pending || 'N/A'}</span>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>

        {/* Log Action Modal */}
        <Modal 
            isOpen={isLogActionModalOpen} 
            onClose={() => setIsLogActionModalOpen(false)} 
            title="Log Manual Action"
        >
            <div className="space-y-4">
                <div>
                    <label className="block text-sm font-medium mb-2">
                        Action Description
                    </label>
                    <Textarea 
                        placeholder="Describe the action taken (e.g., 'Called customer, promised to pay by Friday')..." 
                        value={actionNote} 
                        onChange={e => setActionNote(e.target.value)} 
                        rows={5} 
                    />
                </div>
                <Button onClick={handleLogAction} className="w-full">
                    Save Action
                </Button>
            </div>
        </Modal>

        {/* Escalate Email Modal */}
        <Modal 
            isOpen={isEscalateModalOpen} 
            onClose={() => setIsEscalateModalOpen(false)} 
            title="Escalate to Internal Team"
        >
            <div className="space-y-4">
                <div>
                    <label className="block text-sm font-medium mb-2">To</label>
                    <Input 
                        value={escalationEmail.to} 
                        onChange={e => setEscalationEmail({...escalationEmail, to: e.target.value})} 
                        placeholder="email@company.com"
                    />
                </div>
                <div>
                    <label className="block text-sm font-medium mb-2">Subject</label>
                    <Input 
                        value={escalationEmail.subject} 
                        onChange={e => setEscalationEmail({...escalationEmail, subject: e.target.value})} 
                        placeholder="Email subject"
                    />
                </div>
                <div>
                    <label className="block text-sm font-medium mb-2">Body</label>
                    <Textarea 
                        value={escalationEmail.body} 
                        onChange={e => setEscalationEmail({...escalationEmail, body: e.target.value})} 
                        rows={10}
                        placeholder="Email body..."
                    />
                </div>
                <Button onClick={handleSendEscalation} className="w-full">
                    <Send className="h-4 w-4 mr-2"/> Send Escalation Email
                </Button>
            </div>
        </Modal>
    </div>
  );
};
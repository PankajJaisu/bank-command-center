"use client";
import {
  type AuditLog,
  type ComparisonData,
  getInvoiceAuditLog,
  addInvoiceComment,
  requestVendorResponse,
  requestInternalResponse,
  draftVendorEmail,
} from "@/lib/api";
import { useEffect, useState } from "react";
import { Button } from "../ui/Button";
import { Textarea } from "../ui/Textarea";
import toast from "react-hot-toast";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../ui/Card";
import { Mail, Loader2, Users, History } from "lucide-react";
import { AuditTrailItem } from "./AuditTrailItem";
import { ConfirmCommunicationModal } from "./ConfirmCommunicationModal";

interface WorkflowAuditTabProps {
  invoiceDbId: number;
  onActionComplete: () => void;
  comparisonData: ComparisonData | null;
}

export const WorkflowAuditTab = ({
  invoiceDbId,
  onActionComplete,
  comparisonData,
}: WorkflowAuditTabProps) => {
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [internalComment, setInternalComment] = useState("");

  // Enhanced state for modals and email workflow
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [modalState, setModalState] = useState<{
    type: "vendor" | "internal" | null;
    isOpen: boolean;
  }>({ type: null, isOpen: false });
  const [messageContent, setMessageContent] = useState("");
  const [isDrafting, setIsDrafting] = useState(false);
  const [recipientEmail, setRecipientEmail] = useState("");

  useEffect(() => {
    const fetchAuditLogs = async () => {
      setIsLoading(true);
      try {
        const logs = await getInvoiceAuditLog(invoiceDbId);
        setAuditLogs(logs);
      } catch {
        toast.error("Failed to load audit history");
      } finally {
        setIsLoading(false);
      }
    };
    fetchAuditLogs();
  }, [invoiceDbId]);

  const generateSuggestion = async (type: "price" | "quantity") => {
    if (!comparisonData) return;

    // Extract vendor email if available from the comparison data structure
    const vendorContact =
      comparisonData.vendor_name || "vendor.email@example.com";
    setRecipientEmail(vendorContact);

    setIsDrafting(true);
    setModalState({ type: "vendor", isOpen: true });
    setMessageContent("");

    try {
      const emailData = await draftVendorEmail(invoiceDbId.toString(), type);
      setMessageContent(emailData.draft_email);
    } catch {
      toast.error(`Failed to generate ${type} query`);
      setModalState({ type: null, isOpen: false });
    } finally {
      setIsDrafting(false);
    }
  };

  const handleOpenModal = (type: "vendor" | "internal") => {
    setMessageContent("");
    setIsDrafting(false);
    if (type === "vendor") {
      setRecipientEmail(comparisonData?.vendor_name || "");
    }
    setModalState({ type, isOpen: true });
  };

  const handleConfirmSend = async () => {
    setIsSubmitting(true);
    try {
      if (modalState.type === "vendor") {
        await requestVendorResponse(invoiceDbId, messageContent);
        toast.success("Message sent to vendor successfully!");
      } else if (modalState.type === "internal") {
        await requestInternalResponse(invoiceDbId, messageContent);
        toast.success("Sent for internal review successfully!");
      }
      setModalState({ type: null, isOpen: false });
      setMessageContent("");
      onActionComplete();
    } catch {
      toast.error("Failed to send message");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAddComment = async () => {
    if (!internalComment.trim()) return;
    setIsSubmitting(true);
    try {
      await addInvoiceComment(invoiceDbId, internalComment);
      setInternalComment("");
      toast.success("Internal note added successfully!");
      // Refresh audit logs
      const logs = await getInvoiceAuditLog(invoiceDbId);
      setAuditLogs(logs);
    } catch {
      toast.error("Failed to add note");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading)
    return (
      <div className="p-4 flex justify-center">
        <Loader2 className="animate-spin" />
      </div>
    );

  return (
    <>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 p-4 h-full">
        {/* Left Column: Communication */}
        <div className="space-y-6 overflow-y-auto pr-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Mail className="w-5 h-5 text-purple-accent" />
                Email Vendor
              </CardTitle>
              <CardDescription>
                Draft a message to the vendor about an issue.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Button
                onClick={() => handleOpenModal("vendor")}
                disabled={!!isSubmitting}
                className="w-full"
              >
                <Mail className="mr-2 h-4 w-4" />
                Compose Email to Vendor
              </Button>
              <div className="text-sm text-gray-500 text-center">
                or use a quick start:
              </div>
              <div className="flex gap-2 justify-center">
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => generateSuggestion("price")}
                >
                  Suggest Price Query
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => generateSuggestion("quantity")}
                >
                  Suggest Qty Query
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Users className="w-5 h-5 text-cyan-accent" />
                Workflow Actions
              </CardTitle>
              <CardDescription>
                Route this to another team for review or add an internal note.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Button
                onClick={() => handleOpenModal("internal")}
                disabled={!!isSubmitting}
                className="w-full"
              >
                <Users className="mr-2 h-4 w-4" />
                Send for Internal Review
              </Button>
              <div className="mt-4 border-t pt-4">
                <Textarea
                  value={internalComment}
                  onChange={(e) => setInternalComment(e.target.value)}
                  placeholder="Add a quick internal note... (this will be logged)"
                />
                <Button
                  onClick={handleAddComment}
                  disabled={isSubmitting || !internalComment.trim()}
                  size="sm"
                  className="mt-2"
                >
                  {isSubmitting && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  Add Note
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Audit History */}
        <div className="flex flex-col h-full border rounded-lg bg-white">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <History className="w-5 h-5" />
              Audit History
            </CardTitle>
            <CardDescription>
              A complete log of all automated and manual actions taken on this
              invoice.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex-grow flex flex-col min-h-0">
            <div className="flex-grow overflow-y-auto pr-2">
              {auditLogs.length > 0 ? (
                auditLogs.map((log, index) => (
                  <AuditTrailItem
                    key={log.id}
                    log={log}
                    isLast={index === auditLogs.length - 1}
                  />
                ))
              ) : (
                <div className="flex items-center justify-center h-full text-gray-500">
                  <div className="text-center">
                    <History className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p>No activity recorded yet</p>
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </div>
      </div>

      {/* Enhanced Communication Modal */}
      <ConfirmCommunicationModal
        isOpen={modalState.isOpen}
        onClose={() => setModalState({ type: null, isOpen: false })}
        onConfirm={handleConfirmSend}
        isSubmitting={!!isSubmitting}
        isDrafting={isDrafting}
        title={
          modalState.type === "vendor"
            ? "Review and Send Email"
            : "Send for Internal Review"
        }
        description={
          modalState.type === "vendor"
            ? "Review the message below before sending it to the vendor. You can edit the content and recipient as needed."
            : "This will route the invoice to another team member for review. Add any context that would be helpful."
        }
        message={messageContent}
        onMessageChange={setMessageContent}
        recipient={modalState.type === "vendor" ? recipientEmail : undefined}
        onRecipientChange={
          modalState.type === "vendor" ? setRecipientEmail : undefined
        }
      />
    </>
  );
};

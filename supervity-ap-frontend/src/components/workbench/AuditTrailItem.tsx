"use client";
import { useState } from "react";
import { type AuditLog } from "@/lib/api";

import { Button } from "@/components/ui/Button";
import {
  CheckCircle,
  XCircle,
  Edit3,
  Mail,
  Users,
  Bot,
  Info,
  Copy,
  Check,
  MessageSquare,
} from "lucide-react";
import { format } from "date-fns";
import toast from "react-hot-toast";

const getIconForAction = (action: string) => {
  const lowerAction = action.toLowerCase();
  if (
    lowerAction.includes("succeeded") ||
    lowerAction.includes("approved") ||
    lowerAction.includes("matched")
  )
    return <CheckCircle className="w-5 h-5 text-green-success" />;
  if (lowerAction.includes("failed") || lowerAction.includes("rejected"))
    return <XCircle className="w-5 h-5 text-pink-destructive" />;
  if (
    lowerAction.includes("updated") ||
    lowerAction.includes("applied") ||
    lowerAction.includes("edit")
  )
    return <Edit3 className="w-5 h-5 text-purple-accent" />;
  if (lowerAction.includes("vendor"))
    return <Mail className="w-5 h-5 text-cyan-accent" />;
  if (lowerAction.includes("internal review"))
    return <Users className="w-5 h-5 text-cyan-accent" />;
  if (lowerAction.includes("comment"))
    return <MessageSquare className="w-5 h-5 text-gray-500" />;
  if (lowerAction.includes("engine"))
    return <Bot className="w-5 h-5 text-blue-primary" />;
  return <Info className="w-5 h-5 text-gray-500" />;
};

interface AuditTrailItemProps {
  log: AuditLog;
  isLast: boolean;
}

export const AuditTrailItem = ({ log, isLast }: AuditTrailItemProps) => {
  const [showDetails, setShowDetails] = useState(false);
  const [hasCopied, setHasCopied] = useState(false);

  const handleCopy = () => {
    if (log.details) {
      navigator.clipboard.writeText(JSON.stringify(log.details, null, 2));
      setHasCopied(true);
      toast.success("Details copied to clipboard!");
      setTimeout(() => setHasCopied(false), 2000);
    }
  };

  return (
    <div className="relative pl-10 pb-6">
      <div className="absolute left-2 top-0.5 transform -translate-x-1/2">
        <div className="w-5 h-5 rounded-full bg-white flex items-center justify-center border-2 border-gray-300">
          {getIconForAction(log.action)}
        </div>
      </div>
      {!isLast && (
        <div className="absolute left-2 top-2 h-full w-0.5 bg-gray-300" />
      )}

      <div>
        <p className="font-semibold text-gray-800">{log.action}</p>
        <p className="text-xs text-gray-500">
          by <span className="font-medium text-gray-700">{log.user}</span> on{" "}
          {format(new Date(log.timestamp), "MMM d, h:mm a")}
        </p>
        {log.summary && (
          <p className="text-sm text-gray-600 mt-1 italic">
            &ldquo;{log.summary}&rdquo;
          </p>
        )}

        {log.details && Object.keys(log.details).length > 0 && (
          <div className="mt-2">
            <Button
              variant="link"
              size="sm"
              onClick={() => setShowDetails(!showDetails)}
              className="p-0 h-auto text-xs"
            >
              {showDetails ? "Hide Details" : "Show Details"}
            </Button>
            {showDetails && (
              <div className="relative mt-1">
                <pre className="bg-gray-50 p-3 rounded border text-xs overflow-x-auto text-gray-dark font-mono">
                  {JSON.stringify(log.details, null, 2)}
                </pre>
                <Button
                  variant="ghost"
                  size="sm"
                  className="absolute top-2 right-2 p-1 h-auto"
                  onClick={handleCopy}
                >
                  {hasCopied ? (
                    <Check className="w-4 h-4 text-green-success" />
                  ) : (
                    <Copy className="w-4 h-4 text-gray-500" />
                  )}
                </Button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

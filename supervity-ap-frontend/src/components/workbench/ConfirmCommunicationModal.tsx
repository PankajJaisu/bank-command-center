"use client";

import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { Textarea } from "@/components/ui/Textarea";
import { Input } from "../ui/Input";
import { Loader2, Send } from "lucide-react";

interface ConfirmCommunicationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  isSubmitting: boolean;
  isDrafting?: boolean;
  title: string;
  description: string;
  message: string;
  onMessageChange: (value: string) => void;
  recipient?: string;
  onRecipientChange?: (value: string) => void;
}

export const ConfirmCommunicationModal = ({
  isOpen,
  onClose,
  onConfirm,
  isSubmitting,
  isDrafting = false,
  title,
  description,
  message,
  onMessageChange,
  recipient,
  onRecipientChange,
}: ConfirmCommunicationModalProps) => {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title}>
      <div className="space-y-4">
        <p className="text-sm text-gray-600">{description}</p>

        {/* Recipient field for vendor emails */}
        {recipient !== undefined && onRecipientChange && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              To:
            </label>
            <Input
              type="email"
              value={recipient}
              onChange={(e) => onRecipientChange(e.target.value)}
              placeholder="vendor.email@example.com"
            />
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Message
          </label>
          {isDrafting ? (
            <div className="flex items-center justify-center p-8 bg-gray-50 rounded-md">
              <Loader2 className="w-6 h-6 animate-spin mr-2" />
              <span className="text-sm text-gray-600">
                Generating message...
              </span>
            </div>
          ) : (
            <Textarea
              value={message}
              onChange={(e) => onMessageChange(e.target.value)}
              rows={6}
              placeholder="Type your message here..."
            />
          )}
        </div>

        <div className="flex justify-end space-x-2 pt-4">
          <Button
            variant="secondary"
            onClick={onClose}
            disabled={isSubmitting || isDrafting}
          >
            Cancel
          </Button>
          <Button
            onClick={onConfirm}
            disabled={
              isSubmitting ||
              isDrafting ||
              !message.trim() ||
              (recipient !== undefined && !recipient.trim())
            }
          >
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Sending...
              </>
            ) : (
              <>
                <Send className="mr-2 h-4 w-4" />
                Send Message
              </>
            )}
          </Button>
        </div>
      </div>
    </Modal>
  );
};

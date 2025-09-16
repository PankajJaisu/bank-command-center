"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { type CopilotResponse, postToCopilot } from "@/lib/api";
import { useAppContext } from "@/lib/AppContext";
import { Bot, User, Loader2, Zap, X, Send } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Textarea } from "@/components/ui/Textarea";
import { BotMessageRenderer } from "./BotMessageRenderer";
import toast from "react-hot-toast";
import { cn } from "@/lib/utils";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "../ui/Card";

interface Message {
  sender: "user" | "bot";
  content: string;
  data?: unknown;
  uiAction?: string;
}

// --- NEW TYPE for history entries ---
interface HistoryEntry {
  role: "user" | "model";
  parts: { text: string }[];
}

const suggestionChips = [
  "Show me a KPI summary",
  "Find all invoices that need review",
  "What's our payment forecast?",
  "Are there any urgent notifications?",
];

interface AIChatOverlayProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AIChatOverlay = ({ isOpen, onClose }: AIChatOverlayProps) => {
  const [isMounted, setIsMounted] = useState(false);
  const { currentInvoiceId } = useAppContext();
  const [messages, setMessages] = useState<Message[]>([
    {
      sender: "bot",
      content:
        "Hello! I'm the Supervity AI Bank Collection Manager. How can I assist you today?",
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  useEffect(() => {
    if (isOpen && isMounted) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen, isMounted]);

  const handleSendMessage = async (messageText?: string) => {
    const textToSend = messageText || input;
    if (!textToSend.trim() || isLoading) return;

    // --- START NEW LOGIC: Prepare history ---
    // Convert UI messages to the format the backend expects
    const history: HistoryEntry[] = messages.slice(1).map((msg) => ({
      // slice(1) to skip the initial greeting
      role: msg.sender === "user" ? "user" : "model",
      parts: [{ text: msg.content }],
    }));
    // --- END NEW LOGIC ---

    const userMessage: Message = { sender: "user", content: textToSend };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      // --- MODIFIED API CALL: Send the history along with the message ---
      const response: CopilotResponse = await postToCopilot({
        message: textToSend,
        current_invoice_id: currentInvoiceId,
        history: history, // Pass the conversation history
      });
      // --- END MODIFICATION ---

      const botMessage: Message = {
        sender: "bot",
        content: response.responseText,
        data: response.data,
        uiAction: response.uiAction,
      };
      setMessages((prev) => [...prev, botMessage]);

      if (response.uiAction === "SHOW_TOAST_SUCCESS") {
        toast.success(response.responseText);
      }
    } catch (error) {
      const errorMessage: Message = {
        sender: "bot",
        content: "Sorry, I encountered an error. Please try again.",
      };
      setMessages((prev) => [...prev, errorMessage]);
      toast.error(
        `Failed to get response: ${error instanceof Error ? error.message : "Please try again"}`,
      );
    } finally {
      setIsLoading(false);
    }
  };

  if (!isMounted) {
    return null;
  }

  return (
    <>
      {/* Backdrop */}
      <div
        className={cn(
          "fixed inset-0 bg-black/30 z-40 transition-opacity backdrop-blur-sm",
          isOpen ? "opacity-100" : "opacity-0 pointer-events-none",
        )}
        onClick={onClose}
      />

      {/* Chat Panel */}
      <div
        className={cn(
          "fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2",
          "z-50 w-[90vw] max-w-3xl h-[85vh] max-h-[800px]",
          "bg-gray-bg rounded-xl shadow-2xl flex flex-col",
          "transition-all duration-300 ease-in-out",
          isOpen
            ? "opacity-100 scale-100"
            : "opacity-0 scale-95 pointer-events-none",
        )}
      >
        <Card className="h-full flex flex-col border-0 shadow-none bg-transparent">
          <CardHeader className="flex-row items-center justify-between border-b bg-white rounded-t-xl">
            <div>
              <CardTitle>AI Bank Collection Manager</CardTitle>
              {currentInvoiceId && (
                <CardDescription className="text-purple-accent font-medium">
                  Context: Invoice {currentInvoiceId}
                </CardDescription>
              )}
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="p-1 h-auto rounded-full"
            >
              <X className="w-5 h-5" />
            </Button>
          </CardHeader>

          <CardContent className="flex-grow p-6 overflow-y-auto">
            <div className="space-y-6">
              {messages.map((msg, index) => (
                <div
                  key={index}
                  className={`flex items-start gap-3 ${msg.sender === "user" ? "justify-end" : ""}`}
                >
                  {msg.sender === "bot" && (
                    <div className="w-8 h-8 rounded-full bg-blue-primary/10 flex items-center justify-center shrink-0">
                      <Bot className="w-5 h-5 text-blue-primary" />
                    </div>
                  )}
                  <div
                    className={`p-3 rounded-xl max-w-lg shadow-sm ${msg.sender === "user" ? "bg-blue-primary text-white" : "bg-white border text-gray-dark"}`}
                  >
                    <BotMessageRenderer
                      content={msg.content}
                      uiAction={msg.uiAction}
                      data={msg.data}
                    />
                  </div>
                  {msg.sender === "user" && (
                    <div className="w-8 h-8 rounded-full bg-gray-light flex items-center justify-center shrink-0">
                      <User className="w-5 h-5 text-gray-dark" />
                    </div>
                  )}
                </div>
              ))}
              {isLoading && (
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-full bg-blue-primary/10 flex items-center justify-center shrink-0">
                    <Bot className="w-5 h-5 text-blue-primary" />
                  </div>
                  <div className="p-3 rounded-xl bg-white border text-gray-dark flex items-center shadow-sm">
                    <Loader2 className="w-5 h-5 animate-spin mr-2" />
                    <span>Thinking...</span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          </CardContent>

          <div className="p-4 border-t bg-white rounded-b-xl">
            {messages.length <= 1 && !isLoading && (
              <div className="flex flex-wrap gap-2 mb-3">
                {suggestionChips.map((chip) => (
                  <button
                    key={chip}
                    onClick={() => handleSendMessage(chip)}
                    className="flex items-center gap-2 text-sm text-purple-accent bg-purple-accent/10 px-3 py-1 rounded-full hover:bg-purple-accent/20 transition-colors"
                  >
                    <Zap className="w-3 h-3" />
                    {chip}
                  </button>
                ))}
              </div>
            )}
            <div className="relative">
              <Textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
                placeholder="Ask about KPIs, invoices, or vendors... (Press Enter to send)"
                className="flex-grow resize-none pr-24"
                rows={1}
              />
              <Button
                onClick={() => handleSendMessage()}
                disabled={isLoading || !input.trim()}
                size="sm"
                className="absolute right-2 bottom-2"
              >
                Send <Send className="ml-2 w-4 h-4" />
              </Button>
            </div>
          </div>
        </Card>
      </div>
    </>
  );
};

"use client";
import { useState, useRef, useEffect } from "react";
import { type CopilotResponse, postToCopilot } from "@/lib/api";
import { useAppContext } from "@/lib/AppContext";
import { Bot, User, Loader2, Zap } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Textarea } from "@/components/ui/Textarea";
import { BotMessageRenderer } from "./BotMessageRenderer";
import toast from "react-hot-toast";

interface Message {
  sender: "user" | "bot";
  content: string;
  data?: unknown | null;
  uiAction?: string;
}

const suggestionChips = [
  "Show me a KPI summary",
  "Find all invoices that need review",
  "What's our payment forecast for the next 30 days?",
  "Are there any urgent notifications?",
];

export default function CopilotChatInterface() {
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
  const messagesEndRef = useRef<null | HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages]);

  const handleSendMessage = async (messageText?: string) => {
    const textToSend = messageText || input;
    if (!textToSend.trim() || isLoading) return;

    const userMessage: Message = { sender: "user", content: textToSend };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response: CopilotResponse = await postToCopilot({
        message: textToSend,
        current_invoice_id: currentInvoiceId,
      });
      const botMessage: Message = {
        sender: "bot",
        content: response.responseText,
        data: response.data,
        uiAction: response.uiAction,
      };
      setMessages((prev) => [...prev, botMessage]);

      if (response.uiAction === "SHOW_TOAST_SUCCESS") {
        // Use a unique ID to prevent duplicate toasts
        toast.success(response.responseText, { id: `copilot-${Date.now()}` });
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

  return (
    <div className="flex flex-col h-full bg-white">
      {currentInvoiceId && (
        <div className="p-2 text-center text-sm bg-purple-accent/10 text-purple-accent font-semibold border-b">
          Context: Currently viewing Invoice <strong>{currentInvoiceId}</strong>
        </div>
      )}
      <div className="flex-grow p-6 overflow-y-auto">
        <div className="space-y-6">
          {messages.map((msg, index) => (
            <div
              key={index}
              className={`flex items-start gap-4 ${msg.sender === "user" ? "justify-end" : ""}`}
            >
              {msg.sender === "bot" && (
                <div className="w-8 h-8 rounded-full bg-blue-primary/10 flex items-center justify-center shrink-0">
                  <Bot className="w-5 h-5 text-blue-primary" />
                </div>
              )}
              <div
                className={`p-4 rounded-lg max-w-2xl ${msg.sender === "user" ? "bg-blue-primary text-white" : "bg-gray-bg border"}`}
              >
                {msg.sender === "bot" ? (
                  <BotMessageRenderer
                    content={msg.content}
                    uiAction={msg.uiAction}
                    data={msg.data}
                  />
                ) : (
                  <p>{msg.content}</p>
                )}
              </div>
              {msg.sender === "user" && (
                <div className="w-8 h-8 rounded-full bg-gray-light flex items-center justify-center shrink-0">
                  <User className="w-5 h-5 text-gray-dark" />
                </div>
              )}
            </div>
          ))}
          {isLoading && (
            <div className="flex items-start gap-4">
              <div className="w-8 h-8 rounded-full bg-blue-primary/10 flex items-center justify-center shrink-0">
                <Bot className="w-5 h-5 text-blue-primary" />
              </div>
              <div className="p-4 rounded-lg bg-gray-bg border text-gray-dark flex items-center">
                <Loader2 className="w-5 h-5 animate-spin" />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>
      <div className="p-4 border-t bg-white">
        {messages.length <= 2 && (
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
        <div className="flex gap-4">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
              }
            }}
            placeholder="Ask about KPIs, invoices, or vendors..."
            className="flex-grow resize-none"
          />
          <Button
            onClick={() => handleSendMessage()}
            disabled={isLoading || !input.trim()}
          >
            Send
          </Button>
        </div>
      </div>
    </div>
  );
}

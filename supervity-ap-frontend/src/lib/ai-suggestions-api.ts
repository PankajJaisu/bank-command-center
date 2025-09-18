// AI Suggestions API functions
// This file contains API functions for AI-powered customer suggestions and email functionality

import { z } from "zod";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Schemas for AI suggestions
export const AISuggestionSchema = z.object({
  customer_id: z.number(),
  customer_name: z.string(),
  suggestion: z.object({
    risk_assessment: z.string(),
    recommended_action: z.string(),
    strategy: z.string(),
    priority_level: z.enum(["high", "medium", "low"]),
    suggested_timeline: z.string(),
    specific_action_steps: z.array(z.string()).optional(),
    applied_rule: z.string().optional(),
  }),
  generated_at: z.string(),
});

export const EmailContentSchema = z.object({
  customer_id: z.number(),
  action_type: z.string(),
  email_content: z.object({
    subject: z.string(),
    body: z.string(),
  }),
  generated_at: z.string(),
});

export const CustomerContractSummarySchema = z.object({
  customer: z.object({
    id: z.number(),
    customer_no: z.string(),
    name: z.string(),
    cibil_score: z.number().nullable(),
    risk_level: z.string().nullable(),
    outstanding_amount: z.number().nullable(),
    pending_amount: z.number().nullable(),
    emi_pending: z.number().nullable(),
    days_overdue: z.number().nullable(),
    segment: z.string().nullable(),
    email: z.string().nullable(),
    phone: z.string().nullable(),
  }),
  contract_note: z.object({
    id: z.number(),
    emi_amount: z.number().nullable(),
    due_day: z.number().nullable(),
    late_fee_percent: z.number().nullable(),
    loan_amount: z.number().nullable(),
    tenure_months: z.number().nullable(),
    interest_rate: z.number().nullable(),
    filename: z.string().nullable(),
  }).nullable(),
  applicable_rules_count: z.number(),
  has_contract_note: z.boolean(),
});

export type AISuggestion = z.infer<typeof AISuggestionSchema>;
export type EmailContent = z.infer<typeof EmailContentSchema>;
export type CustomerContractSummary = z.infer<typeof CustomerContractSummarySchema>;

// API Functions
export async function getCustomerSuggestion(customerId: number): Promise<AISuggestion> {
  const token = localStorage.getItem("token");
  
  const response = await fetch(`${API_BASE_URL}/api/ai-suggestions/suggestions/${customerId}`, {
    method: "GET",
    headers: {
      "Authorization": `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to get customer suggestion: ${response.status}`);
  }

  const data = await response.json();
  return AISuggestionSchema.parse(data);
}

export async function generateEmailContent(
  customerId: number,
  actionType: string,
  customMessage?: string
): Promise<EmailContent> {
  const token = localStorage.getItem("token");
  
  const response = await fetch(`${API_BASE_URL}/api/ai-suggestions/email/generate`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      customer_id: customerId,
      action_type: actionType,
      custom_message: customMessage,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to generate email content: ${response.status}`);
  }

  const data = await response.json();
  return EmailContentSchema.parse(data);
}

export async function sendSuggestionEmail(
  customerId: number,
  actionType: string,
  customMessage?: string,
  recipientEmail?: string
): Promise<{ message: string; customer_id: number; recipient_email: string; action_type: string; email_subject: string }> {
  const token = localStorage.getItem("token");
  
  const response = await fetch(`${API_BASE_URL}/api/ai-suggestions/email/send`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      customer_id: customerId,
      action_type: actionType,
      custom_message: customMessage,
      recipient_email: recipientEmail,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to send email: ${response.status}`);
  }

  return await response.json();
}

export async function getBatchSuggestions(
  riskLevel: "red" | "amber" | "yellow",
  limit: number = 10
): Promise<{
  risk_level: string;
  total_customers: number;
  successful_suggestions: number;
  suggestions: AISuggestion[];
}> {
  const token = localStorage.getItem("token");
  
  const response = await fetch(`${API_BASE_URL}/api/ai-suggestions/suggestions/batch/${riskLevel}?limit=${limit}`, {
    method: "GET",
    headers: {
      "Authorization": `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to get batch suggestions: ${response.status}`);
  }

  const data = await response.json();
  return {
    ...data,
    suggestions: data.suggestions.map((suggestion: any) => AISuggestionSchema.parse(suggestion)),
  };
}

export async function getCustomerContractSummary(customerId: number): Promise<CustomerContractSummary> {
  const token = localStorage.getItem("token");
  
  const response = await fetch(`${API_BASE_URL}/api/ai-suggestions/customer/${customerId}/contract-summary`, {
    method: "GET",
    headers: {
      "Authorization": `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to get customer contract summary: ${response.status}`);
  }

  const data = await response.json();
  return CustomerContractSummarySchema.parse(data);
}

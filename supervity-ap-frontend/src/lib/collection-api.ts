// Collection Cell API functions
// This file contains API functions specific to the Collection Cell/AR functionality

import { z } from "zod";

// Collection Cell specific schemas
export const LoanAccountSchema = z.object({
  id: z.number(),
  customerId: z.number(), // NEW: Customer ID for database linking
  customerNo: z.string(),
  customerName: z.string(),
  loanId: z.string(),
  nextPaymentDueDate: z.string(),
  amountDue: z.number().nullable().transform(val => val ?? 0),
  daysOverdue: z.number().nullable().transform(val => val ?? 0),
  lastPaymentDate: z.string().nullable(),
  collectionStatus: z.enum(['pending', 'contacted', 'promise_to_pay', 'disputed', 'cleared']),
  reconciliationStatus: z.enum(['cleared', 'in_transit', 'unreconciled']),
  lastContactNote: z.string().nullable(),
  totalOutstanding: z.number().nullable().transform(val => val ?? 0),
  principalBalance: z.number().nullable().transform(val => val ?? 0),
  interestAccrued: z.number().nullable().transform(val => val ?? 0),
  collectorName: z.string().optional(),
  riskLevel: z.enum(['red', 'amber', 'yellow']),
  alertSummary: z.string(),
  lastContactDate: z.string(),
  // NEW: Contract note information
  hasContractNote: z.boolean().default(false),
  contractNoteId: z.number().nullable(),
  contractEmiAmount: z.number().nullable().transform(val => val ?? null),
  contractDueDay: z.number().nullable().transform(val => val ?? null),
  contractLateFeePercent: z.number().nullable().transform(val => val ?? null),
  contractFilename: z.string().nullable(),
  contractFilePath: z.string().nullable(),
  // Customer additional info
  cibilScore: z.number().nullable().transform(val => val ?? null),
  pendingAmount: z.number().nullable().transform(val => val ?? null),
  emi_pending: z.number().nullable().optional().transform(val => val ?? 0),
  segment: z.string().nullable().optional().transform(val => val ?? "Retail"),
  pendency: z.string().nullable().optional().transform(val => val ?? null),
});

export const CollectionKPIsSchema = z.object({
  totalReceivablesDue: z.number(),
  totalCollected: z.number(),
  delinquencyRate: z.number(),
  totalAmountOverdue: z.number(),
  accountsOverdue: z.number(),
  collectedCleared: z.number(),
  collectedInTransit: z.number(),
});

export const CollectionMetricsSchema = z.object({
  agingBuckets: z.object({
    current: z.number(),
    days1_30: z.number(),
    days31_60: z.number(),
    days61_90: z.number(),
    days90Plus: z.number(),
  }),
  collectionFunnel: z.object({
    totalDue: z.number(),
    paidByCustomer: z.number(),
    clearedByBank: z.number(),
  }),
  delinquencyTrend: z.array(z.object({
    month: z.string(),
    rate: z.number(),
  })),
});

export const ContactLogSchema = z.object({
  id: z.number(),
  loanAccountId: z.number(),
  contactDate: z.string(),
  contactType: z.enum(['phone', 'email', 'letter', 'in_person']),
  note: z.string(),
  collectorName: z.string(),
  followUpDate: z.string().nullable(),
});

// Type exports
export type LoanAccount = z.infer<typeof LoanAccountSchema>;
export type CollectionKPIs = z.infer<typeof CollectionKPIsSchema>;
export type CollectionMetrics = z.infer<typeof CollectionMetricsSchema>;
export type ContactLog = z.infer<typeof ContactLogSchema>;

// API base URL (consistent with main API)
const getApiBaseUrl = () => {
  if (typeof window === 'undefined' && !process.env.NEXT_PUBLIC_API_BASE_URL) {
    return "http://localhost:8000/api";
  }
  return process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api";
};

// Authenticated fetch wrapper
async function authenticatedFetch(url: string, options: RequestInit = {}) {
  const token = localStorage.getItem("authToken");
  return fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    },
  });
}

/**
 * Fetches loan accounts with contract information from the new backend endpoint
 */
export async function getLoanAccountsWithContracts(filters?: {
  status?: string;
  risk_level?: string;
  limit?: number;
  offset?: number;
}): Promise<LoanAccount[]> {
  const searchParams = new URLSearchParams();
  if (filters?.status) searchParams.set('status', filters.status);
  if (filters?.risk_level) searchParams.set('risk_level', filters.risk_level);
  if (filters?.limit) searchParams.set('limit', filters.limit.toString());
  if (filters?.offset) searchParams.set('offset', filters.offset.toString());

  const response = await authenticatedFetch(`${getApiBaseUrl()}/collection/loan-accounts?${searchParams}`);
  if (!response.ok) {
    throw new Error("Failed to fetch loan accounts with contracts");
  }
  const data = await response.json();
  return z.array(LoanAccountSchema).parse(data);
}

/**
 * Fetches all loan accounts with optional filtering (original mock function)
 */
export async function getLoanAccounts(filters?: {
  status?: string;
  collector?: string;
  overdue?: boolean;
  search?: string;
}): Promise<LoanAccount[]> {
  const params = new URLSearchParams();
  if (filters?.status) params.append("status", filters.status);
  if (filters?.collector) params.append("collector", filters.collector);
  if (filters?.overdue !== undefined) params.append("overdue", filters.overdue.toString());
  if (filters?.search) params.append("search", filters.search);

  const response = await authenticatedFetch(
    `${getApiBaseUrl()}/collection/accounts?${params.toString()}`
  );

  if (!response.ok) {
    throw new Error("Failed to fetch loan accounts");
  }

  const data = await response.json();
  return LoanAccountSchema.array().parse(data);
}

/**
 * Fetches collection KPIs for the dashboard
 */
export async function getCollectionKPIs(): Promise<CollectionKPIs> {
  const response = await authenticatedFetch(`${getApiBaseUrl()}/collection/kpis`);

  if (!response.ok) {
    throw new Error("Failed to fetch collection KPIs");
  }

  const data = await response.json();
  return CollectionKPIsSchema.parse(data);
}

/**
 * Fetches collection metrics for charts and analytics
 */
export async function getCollectionMetrics(): Promise<CollectionMetrics> {
  const response = await authenticatedFetch(`${getApiBaseUrl()}/collection/metrics`);

  if (!response.ok) {
    throw new Error("Failed to fetch collection metrics");
  }

  const data = await response.json();
  return CollectionMetricsSchema.parse(data);
}

/**
 * Logs a contact note for a loan account
 */
export async function logContact(
  loanAccountId: number,
  contactData: {
    contactType: 'phone' | 'email' | 'letter' | 'in_person';
    note: string;
    followUpDate?: string;
  }
): Promise<ContactLog> {
  const response = await authenticatedFetch(
    `${getApiBaseUrl()}/collection/accounts/${loanAccountId}/contact`,
    {
      method: "POST",
      body: JSON.stringify(contactData),
    }
  );

  if (!response.ok) {
    throw new Error("Failed to log contact");
  }

  const data = await response.json();
  return ContactLogSchema.parse(data);
}

/**
 * Updates the collection status of a loan account
 */
export async function updateCollectionStatus(
  loanAccountId: number,
  status: 'pending' | 'contacted' | 'promise_to_pay' | 'disputed' | 'cleared'
): Promise<void> {
  const response = await authenticatedFetch(
    `${getApiBaseUrl()}/collection/accounts/${loanAccountId}/status`,
    {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }
  );

  if (!response.ok) {
    throw new Error("Failed to update collection status");
  }
}

/**
 * Generates a dunning letter for a loan account
 */
export async function generateDunningLetter(loanAccountId: number): Promise<Blob> {
  const response = await authenticatedFetch(
    `${getApiBaseUrl()}/collection/accounts/${loanAccountId}/dunning-letter`,
    {
      method: "POST",
    }
  );

  if (!response.ok) {
    throw new Error("Failed to generate dunning letter");
  }

  return response.blob();
}

/**
 * Performs batch actions on multiple loan accounts
 */
export async function performBatchAction(
  accountIds: number[],
  action: 'mark_contacted' | 'generate_letters' | 'export_data'
): Promise<void> {
  const response = await authenticatedFetch(
    `${getApiBaseUrl()}/collection/batch-action`,
    {
      method: "POST",
      body: JSON.stringify({ accountIds, action }),
    }
  );

  if (!response.ok) {
    throw new Error("Failed to perform batch action");
  }
}

/**
 * Exports collection data in specified format
 */
export async function exportCollectionData(
  filters?: {
    status?: string;
    collector?: string;
    overdue?: boolean;
    format?: 'csv' | 'xlsx';
  }
): Promise<Blob> {
  const params = new URLSearchParams();
  if (filters?.status) params.append("status", filters.status);
  if (filters?.collector) params.append("collector", filters.collector);
  if (filters?.overdue !== undefined) params.append("overdue", filters.overdue.toString());
  if (filters?.format) params.append("format", filters.format);

  const response = await authenticatedFetch(
    `${getApiBaseUrl()}/collection/export?${params.toString()}`
  );

  if (!response.ok) {
    throw new Error("Failed to export collection data");
  }

  return response.blob();
}

/**
 * Gets contact history for a loan account
 */
export async function getContactHistory(loanAccountId: number): Promise<ContactLog[]> {
  const response = await authenticatedFetch(
    `${getApiBaseUrl()}/collection/accounts/${loanAccountId}/contacts`
  );

  if (!response.ok) {
    throw new Error("Failed to fetch contact history");
  }

  const data = await response.json();
  return ContactLogSchema.array().parse(data);
}

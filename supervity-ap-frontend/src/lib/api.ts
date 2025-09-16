import { z } from "zod";

// --- START OF FIX: Use the runtime environment variable ---
// This will be set by the deployment environment (e.g., Docker, Vercel, Kubernetes).
// It falls back to the local URL for development.
const getApiBaseUrl = (): string => {
  // Add safety check for SSG/SSR environments
  if (typeof window === 'undefined' && !process.env.NEXT_PUBLIC_API_BASE_URL) {
    return "http://localhost:8000/api";
  }
  return process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api";
};
// --- END OF FIX ---

// --- AUTHENTICATION HELPER ---
const getToken = () => typeof window !== 'undefined' ? localStorage.getItem('authToken') : null;

async function authenticatedFetch(url: string, options: RequestInit = {}): Promise<Response> {
    const token = getToken();
    const headers = new Headers(options.headers || {});
    if (token) {
        headers.set('Authorization', `Bearer ${token}`);
    }
    options.headers = headers;
    return fetch(url, options);
}

// --- NEW USER & ROLE SCHEMAS ---
export const RoleSchema = z.object({
  id: z.number(),
  name: z.string(),
});
export type Role = z.infer<typeof RoleSchema>;

export const UserSchema = z.object({
  id: z.number(),
  email: z.string(),
  full_name: z.string().nullable(),
  is_active: z.boolean(),
  is_approved: z.boolean(),
  role: RoleSchema,
});
export type User = z.infer<typeof UserSchema>;

// --- NEW PERMISSION POLICY SCHEMAS ---
export const PermissionPolicySchema = z.object({
  id: z.number(),
  user_id: z.number(),
  name: z.string(),
  conditions: z.record(z.any()), // JSON object for conditions
  is_active: z.boolean(),
});
export type PermissionPolicy = z.infer<typeof PermissionPolicySchema>;

export const PermissionPolicyCreateSchema = z.object({
  name: z.string(),
  conditions: z.record(z.any()), // JSON object for conditions
  is_active: z.boolean().default(true),
});
export type PermissionPolicyCreate = z.infer<typeof PermissionPolicyCreateSchema>;

export const UserWithVendorsSchema = UserSchema.extend({
  permission_policies: z.array(PermissionPolicySchema),
});
export type UserWithVendors = z.infer<typeof UserWithVendorsSchema>;

const AllUsersWithVendorsSchema = z.array(UserWithVendorsSchema);

// --- NEW DATE RANGE TYPE ---
export type DateRange = {
    from: string | null;
    to: string | null;
}

// Helper to build date and user query params
const buildDashboardQueryParams = (dateRange: DateRange, userId?: number) => {
    const params = new URLSearchParams();
    if (dateRange.from) params.append('start_date', dateRange.from);
    if (dateRange.to) params.append('end_date', dateRange.to);
    if (userId) params.append('for_user_id', String(userId));
    return params.toString();
}

// --- AUTH FUNCTIONS ---
export async function login(formData: FormData): Promise<{ access_token: string }> {
  const response = await fetch(`${getApiBaseUrl()}/auth/login`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Login failed');
  }
  return response.json();
}

export async function signup(payload: {email: string, password: string}): Promise<User> {
  const response = await fetch(`${getApiBaseUrl()}/auth/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Signup failed');
  }
  return UserSchema.parse(await response.json());
}

export async function getCurrentUser(): Promise<UserWithVendors> {
  const response = await authenticatedFetch(`${getApiBaseUrl()}/users/me`);

  if (!response.ok) {
    if (response.status === 401) localStorage.removeItem('authToken'); // Token is invalid
    throw new Error('Could not fetch user data.');
  }
  return UserWithVendorsSchema.parse(await response.json());
}

export async function getMatchingPolicies(invoiceDbId: number): Promise<string[]> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}/invoices/${invoiceDbId}/matching-policies`);
    if (!response.ok) {
        // Return empty array on error to prevent UI crash
        const error = await response.json().catch(() => ({ detail: "Failed to fetch matching policies" }));
        console.error(error.detail);
        return [];
    }
    return await response.json();
}

export async function getAllUsers(): Promise<UserWithVendors[]> {
  const response = await authenticatedFetch(`${getApiBaseUrl()}/users/`);

  if (!response.ok) throw new Error('Failed to fetch users.');
  return AllUsersWithVendorsSchema.parse(await response.json());
}

export async function approveUser(userId: number): Promise<User> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}/users/${userId}/approve`, {
        method: 'POST',
    });
    if (!response.ok) throw new Error('Failed to approve user.');
    return UserSchema.parse(await response.json());
}

export async function updateUserPolicies(userId: number, policies: PermissionPolicyCreate[]): Promise<UserWithVendors> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}/users/${userId}/policies`, {
        method: 'PUT',
        headers: { 
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(policies)
    });
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to update user policies.');
    }
    return UserWithVendorsSchema.parse(await response.json());
}

export async function getAllVendorNames(): Promise<string[]> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}/config/all-vendor-names`);
    if (!response.ok) throw new Error("Failed to fetch vendor names");
    return await response.json();
}

// --- START NEW JOB SUMMARY SCHEMA ---
const JobResultSchema = z.object({
  filename: z.string(),
  status: z.enum(['success', 'error']),
  message: z.string(),
  extracted_id: z.string().optional().nullable(),
  document_type: z.string().optional().nullable(), // NEW: Add document type field
});
export type JobResult = z.infer<typeof JobResultSchema>;
// --- END NEW JOB SUMMARY SCHEMA ---

// Define schemas for API responses using Zod for type safety
export const JobSchema = z.object({
  id: z.number(),
  status: z.enum(['pending', 'processing', 'completed', 'failed', 'matching']),
  created_at: z.string(),
  completed_at: z.string().nullable(),
  total_files: z.number(),
  processed_files: z.number(),
  summary: z.array(JobResultSchema).nullable(),
});
export type Job = z.infer<typeof JobSchema>;

const AllJobsResponseSchema = z.array(JobSchema);

/**
 * Uploads an array of files to the backend.
 * @param files - The array of File objects to upload.
 * @returns The created job object.
 */
export async function uploadDocuments(files: File[]): Promise<Job> {
  const formData = new FormData();
  files.forEach(file => {
    formData.append("files", file);
  });

  const response = await authenticatedFetch(`${getApiBaseUrl()}/documents/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to upload documents");
  }
  
  const data = await response.json();
  return JobSchema.parse(data);
}

/**
 * Upload policy documents and create rules at specified level
 * @param files - The array of PDF files to upload
 * @param ruleLevel - The level at which rules should be created (system, segment, customer)
 * @param segment - The segment name (required if ruleLevel is 'segment')
 * @param customerId - The customer ID (required if ruleLevel is 'customer')
 * @returns The created job object
 */
export async function uploadPolicyDocuments(
  files: File[], 
  ruleLevel: 'system' | 'segment' | 'customer',
  segment?: string,
  customerId?: string
): Promise<Job> {
  const formData = new FormData();
  files.forEach(file => {
    formData.append("files", file);
  });

  // Build query parameters
  const params = new URLSearchParams({
    rule_level: ruleLevel,
  });
  
  if (segment) params.append('segment', segment);
  if (customerId) params.append('customer_id', customerId);

  const response = await authenticatedFetch(`${getApiBaseUrl()}/documents/upload-policy?${params}`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to upload policy documents");
  }

  const data = await response.json();
  return JobSchema.parse(data);
}

/**
 * Triggers a sync of the loan_document folder in the sample data directory on the backend.
 * @returns The created job object.
 */
export async function syncSampleData(): Promise<Job> {
  const response = await authenticatedFetch(`${getApiBaseUrl()}/documents/sync-sample-data`, {
    method: "POST",
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to start sample data sync");
  }
  
  const data = await response.json();
  return JobSchema.parse(data);
}

/**
 * Fetches the status of a specific job.
 * @param jobId - The ID of the job to fetch.
 * @returns The job object with updated status.
 */
export async function getJobStatus(jobId: number): Promise<Job> {
  const response = await authenticatedFetch(`${getApiBaseUrl()}/documents/jobs/${jobId}`);
  if (!response.ok) {
    throw new Error("Failed to fetch job status");
  }
  const data = await response.json();
  return JobSchema.parse(data);
}

/**
 * Fetches a list of recent jobs.
 * @returns An array of job objects.
 */
export async function getAllJobs(): Promise<Job[]> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}/documents/jobs`);
    if (!response.ok) {
        throw new Error("Failed to fetch jobs");
    }
    const data = await response.json();
    return AllJobsResponseSchema.parse(data);
}

// Define MatchTraceStepSchema first as it's used in multiple schemas
export const MatchTraceStepSchema = z.object({
  step: z.string(),
  status: z.enum(['PASS', 'FAIL', 'INFO']),
  message: z.string(),
  details: z.record(z.unknown()).optional().nullable(),
});
export type MatchTraceStep = z.infer<typeof MatchTraceStepSchema>;

// --- START: MODIFIED INVOICE SUMMARY SCHEMA ---
export const InvoiceSummarySchema = z.object({
    id: z.number(),
    invoice_id: z.string(),
    vendor_name: z.string().nullable(),
    grand_total: z.number().nullable(),
    status: z.string(),
    invoice_date: z.string().nullable(),
    sla_status: z.string().optional().nullable(),
    review_category: z.string().optional().nullable(),
    hold_until: z.string().optional().nullable(), // The DB sends a string, not a Date object
});
export type InvoiceSummary = z.infer<typeof InvoiceSummarySchema>;
// --- END: MODIFIED INVOICE SUMMARY SCHEMA ---
const AllInvoicesSummarySchema = z.array(InvoiceSummarySchema);

// This is the schema we will use for Payment Center and Invoice Explorer
export type Invoice = InvoiceSummary;

// ADD NEW SUGGESTION SCHEMA
export const SuggestionSchema = z.object({
  message: z.string(),
  action: z.string(),
  confidence: z.number(),
});
export type Suggestion = z.infer<typeof SuggestionSchema>;

// ADD THIS NEW SCHEMA for the editable field definition
export const PoEditableFieldSchema = z.object({
  field_name: z.string(),
  display_name: z.string(),
});
export type PoEditableField = z.infer<typeof PoEditableFieldSchema>;

// --- MAKE SCHEMAS MORE RESILIENT TO NULL/UNDEFINED VALUES ---
export const PoLineItemSchema = z.object({
  description: z.string().optional().nullable(),
  ordered_qty: z.number().optional().nullable(),
  unit_price: z.number().optional().nullable(),
  unit: z.string().optional().nullable(),
  normalized_qty: z.number().optional().nullable(),
  normalized_unit: z.string().optional().nullable(),
  normalized_unit_price: z.number().optional().nullable(),
  po_number: z.string().optional().nullable(),
  po_db_id: z.number().optional().nullable(),
}).passthrough();
export type PoLineItem = z.infer<typeof PoLineItemSchema>;

export const InvoiceLineItemSchema = z.object({
  description: z.string().optional().nullable(),
  quantity: z.number().optional().nullable(),
  unit_price: z.number().optional().nullable(),
  line_total: z.number().optional().nullable(),
  unit: z.string().optional().nullable(),
  normalized_qty: z.number().optional().nullable(),
  normalized_unit: z.string().optional().nullable(),
}).passthrough();
export type InvoiceLineItem = z.infer<typeof InvoiceLineItemSchema>;

const GrnLineItemSchema = z.object({
  description: z.string().optional().nullable(),
  received_qty: z.number().optional().nullable(),
  unit: z.string().optional().nullable(),
  normalized_qty: z.number().optional().nullable(),
  normalized_unit: z.string().optional().nullable(),
  grn_number: z.string().optional().nullable(),
}).passthrough();

export const DocumentPathSchema = z.object({
  file_path: z.string().nullable(),
});
export type DocumentPath = z.infer<typeof DocumentPathSchema>;

export const PoHeaderSchema = z.object({
    id: z.number(),
    po_number: z.string(),
    order_date: z.string().nullable(),
    po_grand_total: z.number().nullable(),
    line_items: z.array(PoLineItemSchema).optional().nullable(),
});
export type PoHeader = z.infer<typeof PoHeaderSchema>;

// --- NEW INVOICE HEADER DATA SCHEMA ---
export const InvoiceHeaderDataSchema = z.object({
  invoice_id: z.string().nullable(),
  vendor_name: z.string().nullable(),
  vendor_address: z.string().nullable(),
  buyer_name: z.string().nullable(),
  buyer_address: z.string().nullable(),
  shipping_address: z.string().nullable(),
  billing_address: z.string().nullable(),
  invoice_date: z.string().nullable(),
  due_date: z.string().nullable(),
  payment_terms: z.string().nullable(),
  subtotal: z.number().nullable(),
  tax: z.number().nullable(),
  grand_total: z.number().nullable(),
  other_header_fields: z.record(z.unknown()).nullable(),
  metadata: z.record(z.unknown()).nullable(),
});
export type InvoiceHeaderData = z.infer<typeof InvoiceHeaderDataSchema>;
// --- END NEW SCHEMA ---

// This is the new schema for the main workbench data endpoint
export const ComparisonDataSchema = z.object({
  invoice_id: z.string(),
  invoice_header_data: InvoiceHeaderDataSchema.nullable(), // ADD THIS LINE
  vendor_name: z.string().nullable(),
  grand_total: z.number().nullable(),
  line_item_comparisons: z.array(z.object({
    invoice_line: InvoiceLineItemSchema.nullable(),
    po_line: PoLineItemSchema.nullable(),
    grn_line: GrnLineItemSchema.nullable(),
    po_number: z.string().nullable(),
    grn_number: z.string().nullable(),
  })),
  related_pos: z.array(PoHeaderSchema),
  related_grns: z.array(z.record(z.unknown())),
  related_documents: z.object({
      invoice: DocumentPathSchema.nullable(),
      po: DocumentPathSchema.nullable(),
      grn: DocumentPathSchema.nullable(),
  }),
  // This new field provides all documents for the switcher
  all_related_documents: z.object({
    pos: z.array(z.object({ 
        id: z.number(), // Add ID
        file_path: z.string().nullable(), 
        po_number: z.string(),
        data: z.record(z.unknown()) // Add data payload
    })),
    grns: z.array(z.object({ 
        id: z.number(), // Add ID
        file_path: z.string().nullable(), 
        grn_number: z.string(),
        data: z.record(z.unknown()) // Add data payload
    })),
  }),
  match_trace: z.array(MatchTraceStepSchema),
  invoice_notes: z.string().nullable(),
  invoice_status: z.string(),
  gl_code: z.string().nullable().optional(),
  suggestion: SuggestionSchema.nullable(),
  po_editable_fields: z.array(PoEditableFieldSchema).optional(), // ADD THIS LINE
});
export type ComparisonData = z.infer<typeof ComparisonDataSchema>;

// More specific schemas for document data
export const InvoiceDataSchema = z.object({
  invoice_number: z.string().optional(),
  po_number: z.string().optional(),
  vendor_name: z.string().optional(),
  grand_total: z.number().optional(),
  invoice_date: z.string().optional(),
}).passthrough(); // Allow additional fields

export const ExceptionSchema = z.object({
  type: z.string(),
  message: z.string(),
  severity: z.enum(['LOW', 'MEDIUM', 'HIGH']).optional(),
  field: z.string().optional(),
}).passthrough();

// --- NEW COLLABORATION SCHEMAS ---
export const CommentSchema = z.object({
    id: z.number(),
    text: z.string(),
    user: z.string(),
    created_at: z.string(),
});
export type Comment = z.infer<typeof CommentSchema>;
const AllCommentsSchema = z.array(CommentSchema);

export const AuditLogSchema = z.object({
  id: z.number(),
  timestamp: z.string(),
  user: z.string(),
  action: z.string(),
  summary: z.string().nullable(),
  details: z.record(z.unknown()).nullable(),
});
export type AuditLog = z.infer<typeof AuditLogSchema>;
const AllAuditLogsSchema = z.array(AuditLogSchema);

// --- NEW INVOICE FUNCTIONS ---

/**
 * Gets a list of invoices, filterable by status.
 * @param status - The status to filter by (e.g., "needs_review").
 * @returns An array of invoice objects.
 */
export async function getInvoices(status: string): Promise<Invoice[]> {
  const response = await authenticatedFetch(`${getApiBaseUrl()}/invoices?status=${encodeURIComponent(status)}`);
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to fetch invoices");
  }
  const data = await response.json();
  return AllInvoicesSummarySchema.parse(data);
}

export async function getInvoiceByStringId(invoiceIdStr: string): Promise<InvoiceSummary> {
  const encodedInvoiceId = encodeURIComponent(invoiceIdStr);
  const response = await authenticatedFetch(`${getApiBaseUrl()}/invoices/by-string-id/${encodedInvoiceId}`);
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to fetch invoice by ID");
  }
  return InvoiceSummarySchema.parse(await response.json());
}

/**
 * Fetches the invoices processed in a specific job.
 * @param jobId The ID of the job.
 * @returns An array of invoice objects.
 */
export async function getInvoicesForJob(jobId: number): Promise<Invoice[]> {
  const response = await authenticatedFetch(`${getApiBaseUrl()}/documents/jobs/${jobId}/invoices`);
  if (!response.ok) {
    throw new Error("Failed to fetch invoices for job");
  }
  const data = await response.json();
  // We can parse it as summary, since that's all the UI component needs
  return AllInvoicesSummarySchema.parse(data);
}

/**
 * Updates the status of an invoice.
 * @param invoiceId - The string-based invoice ID (e.g., INV-AM-98008).
 * @param payload - The payload containing new_status and reason.
 * @returns Success confirmation.
 */
interface UpdateStatusPayload {
    new_status: string; // Changed from a literal type to string to accept any valid status
    reason: string;
    version: number; // Add version field for concurrency control
}

export async function updateInvoiceStatus(invoiceId: string, payload: UpdateStatusPayload): Promise<{ message: string }> {
    // The endpoint in invoices.py is /invoices/{invoice_id}/update-status, where invoice_id is a string
    const response = await authenticatedFetch(`${getApiBaseUrl()}/invoices/${invoiceId}/update-status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });

    if (!response.ok) {
        const error = await response.json();
        const errorMessage = error.detail || "Failed to update status";
        // Let's also check for the specific ID mismatch error
        if (typeof errorMessage === 'string' && errorMessage.includes("not found")) {
             throw new Error(`Invoice '${invoiceId}' not found. There might be an ID mismatch.`);
        }
        throw new Error(errorMessage);
    }
    
    return await response.json();
}

/**
 * Puts an invoice on hold for a specified number of days.
 * @param invoiceDbId The DATABASE ID of the invoice.
 * @param hold_days The number of days to hold for.
 */
export async function putInvoiceOnHold(invoiceDbId: number, hold_days: number): Promise<InvoiceSummary> {
  const response = await authenticatedFetch(`${getApiBaseUrl()}/invoices/${invoiceDbId}/hold`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ hold_days }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to put invoice on hold");
  }
  return InvoiceSummarySchema.parse(await response.json());
}

// --- NEW WORKBENCH & COLLABORATION FUNCTIONS ---

/**
 * Fetches the detailed line-item comparison data for the workbench.
 * @param invoiceDbId The DATABASE ID (number) of the invoice.
 * @returns The prepared comparison data.
 */
export async function getComparisonData(invoiceDbId: number): Promise<ComparisonData> {
  const response = await authenticatedFetch(`${getApiBaseUrl()}/invoices/${invoiceDbId}/comparison-data`);
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to fetch comparison data");
  }
  const data = await response.json();
  return ComparisonDataSchema.parse(data);
}

interface PoUpdatePayload {
    changes: Record<string, unknown>;
    version: number; // Version field for concurrency control
}

export async function updatePurchaseOrder(poDbId: number, payload: PoUpdatePayload): Promise<unknown> {
  const response = await authenticatedFetch(`${getApiBaseUrl()}/documents/purchase-orders/${poDbId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload), // Send the whole payload including version
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to update purchase order");
  }
  return await response.json();
}

export async function updateInvoiceNotes(invoiceDbId: number, notes: string): Promise<unknown> {
  const response = await authenticatedFetch(`${getApiBaseUrl()}/invoices/${invoiceDbId}/notes`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ notes }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to update notes");
  }
  return await response.json();
}

export async function updateGLCode(invoiceDbId: number, glCode: string): Promise<unknown> {
  const response = await authenticatedFetch(`${getApiBaseUrl()}/invoices/${invoiceDbId}/gl-code`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ gl_code: glCode }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to update GL code");
  }
  return await response.json();
}

/**
 * Creates a new Purchase Order from a non-PO invoice.
 * @param invoiceDbId The DATABASE ID of the source invoice.
 * @returns The newly created Purchase Order object.
 */
export async function createPoFromInvoice(invoiceDbId: number): Promise<unknown> {
  const response = await authenticatedFetch(`${getApiBaseUrl()}/documents/create-po-from-invoice/${invoiceDbId}`, {
    method: 'POST',
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to create Purchase Order");
  }
  return await response.json();
}

/**
 * Fetches all comments for an invoice.
 * @param invoiceDbId The DATABASE ID of the invoice.
 */
export async function getInvoiceComments(invoiceDbId: number): Promise<Comment[]> {
  const response = await authenticatedFetch(`${getApiBaseUrl()}/workflow/invoices/${invoiceDbId}/comments`);
  if (!response.ok) throw new Error("Failed to fetch comments");
  return AllCommentsSchema.parse(await response.json());
}

/**
 * Adds a new comment to an invoice.
 * @param invoiceDbId The DATABASE ID of the invoice.
 * @param text The content of the comment.
 */
export async function addInvoiceComment(invoiceDbId: number, text: string): Promise<Comment> {
  const response = await authenticatedFetch(`${getApiBaseUrl()}/workflow/invoices/${invoiceDbId}/comments`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
  if (!response.ok) throw new Error("Failed to add comment");
  return CommentSchema.parse(await response.json());
}

/**
 * Fetches the audit log for an invoice.
 * @param invoiceDbId The DATABASE ID of the invoice.
 */
export async function getInvoiceAuditLog(invoiceDbId: number): Promise<AuditLog[]> {
  const response = await authenticatedFetch(`${getApiBaseUrl()}/workflow/invoices/${invoiceDbId}/audit-log`);
  if (!response.ok) throw new Error("Failed to fetch audit log");
  return AllAuditLogsSchema.parse(await response.json());
}

/**
 * Fetches a PDF document file from the backend.
 * @param filename - The name of the file to fetch.
 * @returns The URL of the blob for the PDF viewer.
 */
export async function getDocumentFile(filename: string): Promise<string> {
  // Note: documents/file endpoint doesn't require authentication
  const response = await fetch(`${getApiBaseUrl()}/documents/file/${filename}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch file: ${filename}`);
  }
  const blob = await response.blob();
  return URL.createObjectURL(blob);
}

// --- NEW AI AP MANAGER SCHEMAS & FUNCTIONS ---
export const CopilotResponseSchema = z.object({
  responseText: z.string(),
  uiAction: z.string(),
  data: z.unknown().nullable(),
});
export type CopilotResponse = z.infer<typeof CopilotResponseSchema>;

interface ChatPayload {
    message: string;
    current_invoice_id?: string | null;
    history?: Array<{
        role: 'user' | 'model';
        parts: { text: string }[];
    }>;
}

/**
 * Sends a message to the Super Agent AI Bank Collection Manager.
 * @param payload - The message and optional context.
 * @returns A structured response for the UI to act upon.
 */
export async function postToCopilot(payload: ChatPayload): Promise<CopilotResponse> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}/copilot/chat`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Failed to get response from AI Bank Collection Manager.");
    }

    const data = await response.json();
    return CopilotResponseSchema.parse(data);
}

// --- NEW FUNCTION FOR DRAFTING EMAILS ---
interface EmailDraftResponse {
    draft_email: string;
}

export async function draftVendorEmail(invoiceId: string, reason: string): Promise<EmailDraftResponse> {
    const response = await postToCopilot({
        message: `Draft an email for invoice ${invoiceId} about the following issue: ${reason}`,
        current_invoice_id: invoiceId
    });

    if (response.uiAction === 'DISPLAY_MARKDOWN' && response.data && typeof (response.data as Record<string, unknown>).draft_email === 'string') {
        return { draft_email: (response.data as Record<string, unknown>).draft_email as string };
    }
    
    // Fallback if the AI didn't use the tool correctly
    return { draft_email: response.responseText };
}

// --- MODIFIED DASHBOARD SCHEMAS ---
export const KpiSchema = z.object({
  financial_optimization: z.object({
    discounts_captured: z.string(),
  }),
  operational_efficiency: z.object({
    touchless_invoice_rate_percent: z.number(),
    touchless_rate_change: z.number(), // ADD THIS
    avg_exception_handling_time_hours: z.number(),
    total_processed_invoices: z.number(),
    invoices_in_review_queue: z.number(),
  }),
  vendor_performance: z.object({
    top_vendors_by_exception_rate: z.record(z.string()),
  }),
});
export type Kpis = z.infer<typeof KpiSchema>;

export const SummarySchema = z.object({
    total_invoices: z.number(),
    requires_review: z.number(),
    auto_approved: z.number(),
    pending_match: z.number(),
    total_pos: z.number(),
    total_grns: z.number(),
    total_value_exceptions: z.number(),
});
export type Summary = z.infer<typeof SummarySchema>;

// --- MODIFIED FETCH FUNCTIONS ---
export async function getDashboardKpis(dateRange: DateRange, userId?: number): Promise<Kpis> {
    const query = buildDashboardQueryParams(dateRange, userId);
    const response = await authenticatedFetch(`${getApiBaseUrl()}/dashboard/kpis?${query}`);
    if (!response.ok) throw new Error("Failed to fetch KPIs");
    return KpiSchema.parse(await response.json());
}

export async function getDashboardSummary(dateRange: DateRange, userId?: number): Promise<Summary> {
    const query = buildDashboardQueryParams(dateRange, userId);
    const response = await authenticatedFetch(`${getApiBaseUrl()}/dashboard/summary?${query}`);
    if (!response.ok) throw new Error("Failed to fetch summary");
    return SummarySchema.parse(await response.json());
}

// Exception Summary Schema and Functions
export const ExceptionSummaryItemSchema = z.object({
    name: z.string(),
    count: z.number(),
});
export type ExceptionSummaryItem = z.infer<typeof ExceptionSummaryItemSchema>;
const ExceptionSummaryResponseSchema = z.array(ExceptionSummaryItemSchema);

export async function getExceptionSummary(dateRange: DateRange, userId?: number): Promise<ExceptionSummaryItem[]> {
    const query = buildDashboardQueryParams(dateRange, userId);
    const response = await authenticatedFetch(`${getApiBaseUrl()}/dashboard/exceptions?${query}`);
    if (!response.ok) {
        throw new Error("Failed to fetch exception summary");
    }
    const data = await response.json();
    return ExceptionSummaryResponseSchema.parse(data);
}

export const CostRoiMetricsSchema = z.object({
    total_return_for_period: z.number(),
    total_cost_for_period: z.number(),
});
export type CostRoiMetrics = z.infer<typeof CostRoiMetricsSchema>;

export async function getCostRoiMetrics(dateRange: DateRange, userId?: number): Promise<CostRoiMetrics> {
    const query = buildDashboardQueryParams(dateRange, userId);
    const response = await authenticatedFetch(`${getApiBaseUrl()}/dashboard/cost-roi?${query}`);
    if (!response.ok) {
        throw new Error("Failed to fetch cost ROI metrics");
    }
    const data = await response.json();
    return CostRoiMetricsSchema.parse(data);
}

// --- UPDATED SEARCH FUNCTION ---
export interface FilterCondition {
    field: string;
    operator: string;
    value: unknown;
}

interface SearchPayload {
    filters: FilterCondition[];
    search_term?: string;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
}

export async function searchInvoices(payload: SearchPayload): Promise<Invoice[]> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}/documents/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error("Failed to search invoices");
    // Use the same summary schema for search results
    return AllInvoicesSummarySchema.parse(await response.json());
}

// --- NEW QUEUE SUMMARY TYPES AND FUNCTION ---
export const QueueSummarySchema = z.object({
    total_count: z.number(),
    total_value: z.number(),
    avg_processing_time: z.union([z.number(), z.string()]).transform(val => 
        typeof val === 'string' ? parseFloat(val) : val
    ).nullable(),
    exception_count: z.number(),
    oldest_invoice_days: z.union([z.number(), z.string()]).transform(val => 
        typeof val === 'string' ? parseFloat(val) : val
    ).nullable(),
    // Add optional fields that the backend might send based on context
    exception_breakdown: z.record(z.string(), z.number()).optional(),
    average_age_days: z.union([z.number(), z.string()]).transform(val => 
        typeof val === 'string' ? parseFloat(val) : val
    ).optional(),
    potential_discounts: z.number().optional(),
});
export type QueueSummary = z.infer<typeof QueueSummarySchema>;

export async function getQueueSummary(statuses: string[]): Promise<QueueSummary> {
    const params = new URLSearchParams();
    statuses.forEach(status => params.append('statuses', status));
    
    const response = await authenticatedFetch(`${getApiBaseUrl()}/invoices/queue-summary?${params.toString()}`);
    
    if (!response.ok) {
        throw new Error('Failed to fetch queue summary');
    }
    
    return QueueSummarySchema.parse(await response.json());
}

// --- ADD NEW FUNCTIONS ---

export async function exportToCsv(payload: SearchPayload): Promise<void> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}/documents/export-csv`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });

    if (!response.ok) {
        throw new Error('Failed to export CSV');
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'invoice_export.csv';
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
}

export async function exportDocuments(payload: SearchPayload, format: 'csv' | 'xlsx' = 'csv'): Promise<void> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}/documents/export?export_format=${format}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Export failed');
    }

    // Handle the file download
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    
    // Extract filename from response headers or use default
    const contentDisposition = response.headers.get('Content-Disposition');
    let filename = `ap_export_${new Date().toISOString().slice(0, 10)}.${format === 'csv' ? 'zip' : 'xlsx'}`;
    if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
        if (filenameMatch) {
            filename = filenameMatch[1];
        }
    }
    
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
}

// Keep the old function for backward compatibility, but mark as deprecated
/** @deprecated Use exportDocuments instead */
export async function exportInvoices(payload: SearchPayload, format: 'csv' | 'xlsx' = 'csv'): Promise<void> {
    return exportDocuments(payload, format);
}

interface BatchUpdatePayload {
    invoice_ids: number[];
    new_status: string; // Changed to accept any valid status string
    reason?: string;
}

export async function batchUpdateInvoiceStatus(payload: BatchUpdatePayload): Promise<{ message: string }> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}/invoices/batch-update-status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Failed to perform bulk update");
    }
    return await response.json();
}

// --- NEW CONFIG & LEARNINGS SCHEMAS AND FUNCTIONS ---

export const VendorSettingSchema = z.object({
    id: z.number(),
    vendor_name: z.string(),
    price_tolerance_percent: z.number().nullable(),
    quantity_tolerance_percent: z.number().nullable(),
    contact_email: z.string().nullable(),
});
export type VendorSetting = z.infer<typeof VendorSettingSchema>;
const AllVendorSettingsSchema = z.array(VendorSettingSchema);
// ADD CREATE SCHEMA
export const VendorSettingCreateSchema = VendorSettingSchema.omit({ id: true });
export type VendorSettingCreate = z.infer<typeof VendorSettingCreateSchema>;

// --- NEW SCHEMA FOR VENDOR PERFORMANCE ---
export const VendorPerformanceSummarySchema = VendorSettingSchema.extend({
    total_invoices: z.number(),
    exception_rate: z.number(),
    avg_payment_time_days: z.number().nullable(),
});
export type VendorPerformanceSummary = z.infer<typeof VendorPerformanceSummarySchema>;
const AllVendorPerformanceSchema = z.array(VendorPerformanceSummarySchema);

export const AutomationRuleSchema = z.object({
    id: z.number(),
    rule_name: z.string(),
    description: z.string().nullable().optional(),
    vendor_name: z.string().nullable(),
    conditions: z.record(z.unknown()),
    action: z.string(),
    is_active: z.boolean().or(z.number()), // Backend uses 1/0, so we accept both
    source: z.string(),
    rule_level: z.string().nullable().optional(),
    segment: z.string().nullable().optional(),
    customer_id: z.string().nullable().optional(),
    source_document: z.string().nullable().optional(),
    status: z.string().nullable().optional(),
});
export type AutomationRule = z.infer<typeof AutomationRuleSchema>;
const AllAutomationRulesSchema = z.array(AutomationRuleSchema);
// ADD CREATE SCHEMA
export const AutomationRuleCreateSchema = AutomationRuleSchema.omit({ id: true });
export type AutomationRuleCreate = z.infer<typeof AutomationRuleCreateSchema>;

export const ExtractionFieldConfigSchema = z.object({
  id: z.number(),
  document_type: z.enum(["Invoice", "PurchaseOrder", "GoodsReceiptNote"]),
  field_name: z.string(),
  display_name: z.string(),
  is_enabled: z.boolean(),
  is_essential: z.boolean(),
  is_editable: z.boolean(),
});
export type ExtractionFieldConfig = z.infer<typeof ExtractionFieldConfigSchema>;
const AllExtractionFieldConfigsSchema = z.array(ExtractionFieldConfigSchema);

export const ExtractionFieldConfigUpdateSchema = z.object({
  id: z.number(),
  is_enabled: z.boolean(),
});
export type ExtractionFieldConfigUpdate = z.infer<typeof ExtractionFieldConfigUpdateSchema>;

export const LearnedHeuristicSchema = z.object({
    vendor_name: z.string(),
    exception_type: z.string(),
    learned_condition: z.record(z.unknown()),
    resolution_action: z.string(),
});
export type LearnedHeuristic = z.infer<typeof LearnedHeuristicSchema>;

export const AggregatedHeuristicSchema = LearnedHeuristicSchema.extend({
    id: z.string(),
    confidence_score: z.number(),
    trigger_count: z.number(),
    potential_impact: z.number(),
});
export type AggregatedHeuristic = z.infer<typeof AggregatedHeuristicSchema>;
const AllAggregatedHeuristicsSchema = z.array(AggregatedHeuristicSchema);

// --- VENDOR SETTINGS ---
export async function getVendorSettings(): Promise<VendorSetting[]> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}/config/vendor-settings`);
    if (!response.ok) throw new Error("Failed to fetch vendor settings");
    return AllVendorSettingsSchema.parse(await response.json());
}

export async function updateVendorSettings(settings: VendorSetting[]): Promise<VendorSetting[]> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}/config/vendor-settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
    });
    if (!response.ok) throw new Error("Failed to update vendor settings");
    return AllVendorSettingsSchema.parse(await response.json());
}

// --- NEW VENDOR SETTING CRUD FUNCTIONS ---

export async function createVendorSetting(settingData: VendorSettingCreate): Promise<VendorSetting> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}/config/vendor-settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settingData),
    });
    if (!response.ok) throw new Error("Failed to create vendor setting");
    return VendorSettingSchema.parse(await response.json());
}

export async function updateSingleVendorSetting(id: number, settingData: VendorSettingCreate): Promise<VendorSetting> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}/config/vendor-settings/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settingData),
    });
    if (!response.ok) throw new Error("Failed to update vendor setting");
    return VendorSettingSchema.parse(await response.json());
}

export async function deleteVendorSetting(id: number): Promise<void> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}/config/vendor-settings/${id}`, {
        method: 'DELETE',
    });
    if (!response.ok) throw new Error("Failed to delete vendor setting");
}

// --- NEW VENDOR PERFORMANCE FUNCTION ---
export async function getVendorPerformanceSummary(): Promise<VendorPerformanceSummary[]> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}/config/vendor-performance-summary`);
    if (!response.ok) throw new Error("Failed to fetch vendor performance");
    return AllVendorPerformanceSchema.parse(await response.json());
}

// --- AUTOMATION RULES ---
export async function getAutomationRules(): Promise<AutomationRule[]> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}/config/automation-rules`);
    if (!response.ok) throw new Error("Failed to fetch automation rules");
    return AllAutomationRulesSchema.parse(await response.json());
}

// --- NEW AUTOMATION RULE CRUD FUNCTIONS ---

export async function createAutomationRule(ruleData: AutomationRuleCreate): Promise<AutomationRule> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}/config/automation-rules`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(ruleData),
    });
    if (!response.ok) throw new Error("Failed to create automation rule");
    return AutomationRuleSchema.parse(await response.json());
}

export async function updateAutomationRule(id: number, ruleData: AutomationRuleCreate): Promise<AutomationRule> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}/config/automation-rules/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(ruleData),
    });
    if (!response.ok) throw new Error("Failed to update automation rule");
    return AutomationRuleSchema.parse(await response.json());
}

export async function deleteAutomationRule(id: number): Promise<void> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}/config/automation-rules/${id}`, {
        method: 'DELETE',
    });
    if (!response.ok) throw new Error("Failed to delete automation rule");
}

export async function deleteAllAutomationRules(): Promise<{
    message: string;
    deleted_count: number;
}> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}/config/automation-rules`, {
        method: 'DELETE',
    });
    if (!response.ok) throw new Error("Failed to delete all automation rules");
    return await response.json();
}

// --- LOAN POLICY LOADING ---
export async function loadLoanPolicies(): Promise<{
    success: boolean;
    message: string;
    rules_created?: number;
    output?: string;
    error?: string;
}> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}/config/load-loan-policies`, {
        method: 'POST',
    });
    if (!response.ok) throw new Error("Failed to load loan policies");
    return await response.json();
}

// --- SLA SCHEMAS AND FUNCTIONS ---

export const SLASchema = z.object({
  id: z.number(),
  name: z.string(),
  description: z.string().nullable(),
  conditions: z.record(z.unknown()),
  threshold_hours: z.number(),
  is_active: z.boolean(),
});
export type SLA = z.infer<typeof SLASchema>;
const AllSLAsSchema = z.array(SLASchema);

export const SLACreateSchema = SLASchema.omit({ id: true });
export type SLACreate = z.infer<typeof SLACreateSchema>;

export async function getSLAs(): Promise<SLA[]> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}/config/slas`);
    if (!response.ok) throw new Error("Failed to fetch SLAs");
    return AllSLAsSchema.parse(await response.json());
}

export async function createSLA(slaData: SLACreate): Promise<SLA> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}/config/slas`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(slaData),
    });
    if (!response.ok) throw new Error("Failed to create SLA");
    return SLASchema.parse(await response.json());
}

export async function updateSLA(id: number, slaData: SLACreate): Promise<SLA> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}/config/slas/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(slaData),
    });
    if (!response.ok) throw new Error("Failed to update SLA");
    return SLASchema.parse(await response.json());
}

export async function deleteSLA(id: number): Promise<void> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}/config/slas/${id}`, {
        method: 'DELETE',
    });
    if (!response.ok) throw new Error("Failed to delete SLA");
}

// --- EXTRACTION FIELD CONFIGURATIONS ---

export async function getExtractionFieldConfigurations(): Promise<ExtractionFieldConfig[]> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}/config/extraction-fields`);
    if (!response.ok) throw new Error("Failed to fetch extraction field configurations");
    return AllExtractionFieldConfigsSchema.parse(await response.json());
}

export async function updateExtractionFieldConfigurations(
    updates: ExtractionFieldConfigUpdate[]
): Promise<ExtractionFieldConfig[]> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}/config/extraction-fields`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
    });
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Failed to update field configurations");
    }
    return AllExtractionFieldConfigsSchema.parse(await response.json());
}

// --- LEARNED HEURISTICS ---
export async function getLearnedHeuristics(): Promise<AggregatedHeuristic[]> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}/learning/heuristics`);
    if (!response.ok) throw new Error("Failed to fetch learned heuristics");
    return AllAggregatedHeuristicsSchema.parse(await response.json());
}

// --- FIX PAYMENT CENTER FETCH ---
// The /payments/payable endpoint returns a full Invoice object, not a summary.
// Let's create a schema for it.
const PayableInvoiceSchema = z.object({
  id: z.number(),
  invoice_id: z.string(),
  vendor_name: z.string().nullable(),
  due_date: z.string().nullable(),
  grand_total: z.number().nullable(),
}).passthrough(); // Use passthrough() to ignore extra fields
const AllPayableInvoicesSchema = z.array(PayableInvoiceSchema);
export type PayableInvoice = z.infer<typeof PayableInvoiceSchema>;

export async function getPayableInvoices(): Promise<PayableInvoice[]> {
  const response = await authenticatedFetch(`${getApiBaseUrl()}/payments/payable`);
  if (!response.ok) throw new Error("Failed to fetch payable invoices");
  const data = await response.json();
  return AllPayableInvoicesSchema.parse(data);
}

export async function createPaymentBatch(invoiceIds: number[]): Promise<{ batch_id: string; processed_invoice_count: number }> {
  const response = await authenticatedFetch(`${getApiBaseUrl()}/payments/batches`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ invoice_ids: invoiceIds }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to create payment batch");
  }
  return await response.json();
}

export async function getInvoicesByCategory(category: string): Promise<Invoice[]> {
  const formattedCategory = category.toLowerCase().replace(/ /g, '_');
  const response = await authenticatedFetch(`${getApiBaseUrl()}/invoices/by-category?category=${formattedCategory}`);
  if (!response.ok) throw new Error("Failed to fetch invoices by category");
  return z.array(InvoiceSummarySchema).parse(await response.json());
}

// Add this new function at the end of the file
export async function batchMarkAsPaid(invoice_ids: number[]): Promise<{ message: string }> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}/invoices/batch-mark-as-paid`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ invoice_ids }),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Failed to mark invoices as paid");
    }
    return await response.json();
}

export async function requestVendorResponse(invoiceDbId: number, message: string): Promise<unknown> {
  const response = await authenticatedFetch(`${getApiBaseUrl()}/workflow/invoices/${invoiceDbId}/request-vendor-response`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to send to vendor");
  }
  return await response.json();
}

export async function requestInternalResponse(invoiceDbId: number, message: string): Promise<unknown> {
  const response = await authenticatedFetch(`${getApiBaseUrl()}/workflow/invoices/${invoiceDbId}/request-internal-response`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to send for internal review");
  }
  return await response.json();
}

export async function batchRematchInvoices(invoice_ids: number[]): Promise<{ message: string }> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}/invoices/batch-rematch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ invoice_ids }),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Failed to trigger re-match");
    }
    return await response.json();
}

export async function getActionQueue(userId?: number): Promise<InvoiceSummary[]> {
    const params = new URLSearchParams();
    if (userId) params.append('for_user_id', String(userId));
    const query = params.toString();
    const response = await authenticatedFetch(`${getApiBaseUrl()}/dashboard/action-queue?${query}`);
    if (!response.ok) {
        console.error("Failed to fetch action queue");
        return []; // Return empty array on failure instead of throwing
    }
    return AllInvoicesSummarySchema.parse(await response.json());
}

// --- NEW STRATEGIC DASHBOARD API ---
export interface DashboardData {
    financial_health?: {
        total_payable_value: number;
        days_payable_outstanding: number;
    };
    operational_metrics?: {
        total_processed: number;
        exception_rate: number;
    };
    workflow_bottlenecks?: Record<string, number>;
    team_performance?: Array<{
        name: string;
        invoices_processed: number;
    }>;
    exception_breakdown?: Array<{
        name: string;
        count: number;
    }>;
    personal_queue?: {
        needs_review: number;
        on_hold: number;
        pending_response: number;
    };
    my_performance?: {
        invoices_processed: number;
        team_average_processed: number;
    };
    recent_activity?: Array<{
        invoice_id: string;
        summary: string | null;
        timestamp: string;
    }>;
}

export async function getDashboardData(dateRange: DateRange): Promise<DashboardData> {
    const params = new URLSearchParams();
    if (dateRange.from) params.append('start_date', dateRange.from);
    if (dateRange.to) params.append('end_date', dateRange.to);
    
    const response = await authenticatedFetch(`${getApiBaseUrl()}/dashboard/data?${params}`);
    if (!response.ok) throw new Error('Failed to fetch dashboard data.');
    return response.json();
}

// --- START: ADD NEW SCHEMAS AND FUNCTIONS FOR INSIGHTS PAGE ---

export const UserActionPatternSchema = z.object({
  id: z.number(),
  pattern_type: z.string(),
  entity_name: z.string(),
  count: z.number(),
  last_detected: z.string(),
});
export type UserActionPattern = z.infer<typeof UserActionPatternSchema>;

export const LearnedPreferenceSchema = z.object({
  id: z.number(),
  preference_type: z.string(),
  context_key: z.string(),
  preference_value: z.string(),
});
export type LearnedPreference = z.infer<typeof LearnedPreferenceSchema>;

export async function getProcessHotspots(): Promise<UserActionPattern[]> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}/learning/process-hotspots`);
    if (!response.ok) throw new Error("Failed to fetch process hotspots");
    return z.array(UserActionPatternSchema).parse(await response.json());
}

export async function getMyPreferences(): Promise<LearnedPreference[]> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}/learning/my-preferences`);
    if (!response.ok) throw new Error("Failed to fetch learned preferences");
    return z.array(LearnedPreferenceSchema).parse(await response.json());
}

export async function deleteMyPreference(preferenceId: number): Promise<void> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}/learning/my-preferences/${preferenceId}`, {
        method: 'DELETE',
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Failed to delete preference" }));
      throw new Error(error.detail);
    }
}

// --- START: ADD NEW SCHEMAS AND FUNCTIONS FOR INSIGHTS EVIDENCE/DISMISS ---

export const HeuristicEvidenceSchema = z.object({
  invoice_id: z.string(),
  approval_date: z.string(),
  user: z.string(),
});
export type HeuristicEvidence = z.infer<typeof HeuristicEvidenceSchema>;

export async function dismissHeuristic(heuristicId: number): Promise<void> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}/learning/heuristics/${heuristicId}/dismiss`, {
        method: 'POST',
    });
    if (!response.ok) {
        throw new Error("Failed to dismiss heuristic");
    }
}

export async function getHeuristicEvidence(heuristicId: number): Promise<HeuristicEvidence[]> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}/learning/heuristics/${heuristicId}/evidence`);
    if (!response.ok) {
        throw new Error("Failed to fetch evidence for heuristic");
    }
    return z.array(HeuristicEvidenceSchema).parse(await response.json());
}

// --- END: ADD NEW SCHEMAS AND FUNCTIONS FOR INSIGHTS EVIDENCE/DISMISS ---

export async function updateUserRole(userId: number, roleName: string): Promise<UserWithVendors> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}/users/${userId}/role`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role_name: roleName }),
    });
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to update user role.');
    }
    return UserWithVendorsSchema.parse(await response.json());
}

// --- END: ADD NEW SCHEMAS AND FUNCTIONS ---

// --- NEW: Collection/Contract API Functions ---

// Generic API object for HTTP methods
export const api = {
  async get(url: string): Promise<any> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}${url}`);
    if (!response.ok) {
      throw new Error(`GET ${url} failed: ${response.statusText}`);
    }
    return response.json();
  },

  async post(url: string, data?: any): Promise<any> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}${url}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: data ? JSON.stringify(data) : undefined,
    });
    if (!response.ok) {
      throw new Error(`POST ${url} failed: ${response.statusText}`);
    }
    return response.json();
  },

  async put(url: string, data?: any): Promise<any> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}${url}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: data ? JSON.stringify(data) : undefined,
    });
    if (!response.ok) {
      throw new Error(`PUT ${url} failed: ${response.statusText}`);
    }
    return response.json();
  },

  async delete(url: string): Promise<any> {
    const response = await authenticatedFetch(`${getApiBaseUrl()}${url}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error(`DELETE ${url} failed: ${response.statusText}`);
    }
    if (response.status === 204) {
      return null; // No content
    }
    return response.json();
  },
};

// Collection-specific schemas
export const ContractTermsSchema = z.object({
  emi_amount: z.number().nullable(),
  due_day: z.number().nullable(),
  late_fee_percent: z.number().nullable(),
  default_clause: z.string().nullable(),
  governing_law: z.string().nullable(),
  interest_rate: z.number().nullable(),
  loan_amount: z.number().nullable(),
  tenure_months: z.number().nullable(),
});

export const CustomerSchema = z.object({
  id: z.number(),
  customer_no: z.string(),
  name: z.string(),
  email: z.string().nullable(),
  phone: z.string().nullable(),
  address: z.string().nullable(),
  cbs_emi_amount: z.number().nullable(),
  cbs_due_day: z.number().nullable(),
  cbs_last_payment_date: z.string().nullable(),
  cbs_outstanding_amount: z.number().nullable(),
  cbs_risk_level: z.string().nullable(),
  contract_note: z.object({
    contract_emi_amount: z.number().nullable(),
    contract_due_day: z.number().nullable(),
    contract_late_fee_percent: z.number().nullable(),
    contract_default_clause: z.string().nullable(),
    contract_governing_law: z.string().nullable(),
    contract_interest_rate: z.number().nullable(),
    contract_loan_amount: z.number().nullable(),
    contract_tenure_months: z.number().nullable(),
  }).nullable(),
});

export const DataIntegrityAlertSchema = z.object({
  id: z.number(),
  alert_type: z.string(),
  title: z.string(),
  description: z.string(),
  severity: z.enum(["high", "medium", "low"]),
  customer_name: z.string().optional(),
  cbs_value: z.string().nullable(),
  contract_value: z.string().nullable(),
  created_at: z.string(),
  is_resolved: z.boolean(),
  customer: CustomerSchema.nullable(),
});

export type ContractTerms = z.infer<typeof ContractTermsSchema>;
export type Customer = z.infer<typeof CustomerSchema>;
export type DataIntegrityAlert = z.infer<typeof DataIntegrityAlertSchema>;

// Collection API functions
export async function getCustomers(params?: {
  limit?: number;
  offset?: number;
  search?: string;
  risk_level?: string;
}): Promise<Customer[]> {
  const searchParams = new URLSearchParams();
  if (params?.limit) searchParams.set('limit', params.limit.toString());
  if (params?.offset) searchParams.set('offset', params.offset.toString());
  if (params?.search) searchParams.set('search', params.search);
  if (params?.risk_level) searchParams.set('risk_level', params.risk_level);

  const response = await authenticatedFetch(`${getApiBaseUrl()}/collection/customers?${searchParams}`);
  if (!response.ok) {
    throw new Error("Failed to fetch customers");
  }
  return z.array(CustomerSchema).parse(await response.json());
}

export async function getCustomer(customerId: number): Promise<Customer> {
  const response = await authenticatedFetch(`${getApiBaseUrl()}/collection/customers/${customerId}`);
  if (!response.ok) {
    throw new Error("Failed to fetch customer");
  }
  return CustomerSchema.parse(await response.json());
}

export async function getCustomerContractTerms(customerId: number): Promise<{
  customer_id: number;
  customer_no: string;
  customer_name: string;
  contract_terms: ContractTerms;
  cbs_data: any;
}> {
  const response = await authenticatedFetch(`${getApiBaseUrl()}/collection/customers/${customerId}/contract-terms`);
  if (!response.ok) {
    throw new Error("Failed to fetch customer contract terms");
  }
  return response.json();
}

export async function getDataIntegrityAlerts(params?: {
  limit?: number;
  offset?: number;
  severity?: string;
  resolved?: boolean;
}): Promise<DataIntegrityAlert[]> {
  const searchParams = new URLSearchParams();
  if (params?.limit) searchParams.set('limit', params.limit.toString());
  if (params?.offset) searchParams.set('offset', params.offset.toString());
  if (params?.severity) searchParams.set('severity', params.severity);
  if (params?.resolved !== undefined) searchParams.set('resolved', params.resolved.toString());

  const response = await authenticatedFetch(`${getApiBaseUrl()}/collection/data-integrity-alerts?${searchParams}`);
  if (!response.ok) {
    throw new Error("Failed to fetch data integrity alerts");
  }
  return z.array(DataIntegrityAlertSchema).parse(await response.json());
}

export async function resolveDataIntegrityAlert(alertId: number): Promise<{ message: string; alert_id: number }> {
  const response = await authenticatedFetch(`${getApiBaseUrl()}/collection/data-integrity-alerts/${alertId}/resolve`, {
    method: 'PUT',
  });
  if (!response.ok) {
    throw new Error("Failed to resolve alert");
  }
  return response.json();
}

export async function getCollectionDashboardSummary(): Promise<{
  data_integrity: {
    total_unresolved_alerts: number;
    high_priority_alerts: number;
    recent_alerts: Array<{
      id: number;
      type: string;
      title: string;
      customer_name: string;
      severity: string;
      created_at: string;
    }>;
  };
  customer_risk: Record<string, number>;
  contract_processing: {
    total_contracts_processed: number;
  };
}> {
  const response = await authenticatedFetch(`${getApiBaseUrl()}/collection/dashboard/summary`);
  if (!response.ok) {
    throw new Error("Failed to fetch dashboard summary");
  }
  return response.json();
}

export async function deleteCustomer(customerId: number): Promise<{ message: string }> {
  const response = await authenticatedFetch(`${getApiBaseUrl()}/collection/customers/${customerId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error("Failed to delete customer");
  }
  return response.json();
}

export async function clearAllCustomerData(): Promise<{ message: string; total_deleted: number }> {
  const response = await authenticatedFetch(`${getApiBaseUrl()}/collection/clear-all-data`, {
    method: "DELETE",
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(errorData.detail || `HTTP ${response.status}: Failed to clear data`);
  }
  return response.json();
}
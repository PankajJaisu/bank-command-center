# src/app/db/schemas.py
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Any, Dict, Union
from datetime import date, datetime
from app.db.models import DocumentStatus

# --- Base Schemas ---


class LineItem(BaseModel):
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    line_total: Optional[float] = None


class InvoiceBase(BaseModel):
    invoice_id: str
    vendor_name: Optional[str] = None
    related_po_numbers: Optional[List[str]] = []
    invoice_date: Optional[date] = None
    grand_total: Optional[float] = None
    line_items: Optional[List[Dict[str, Any]]] = []


class PurchaseOrderBase(BaseModel):
    po_number: str
    vendor_name: Optional[str] = None
    order_date: Optional[date] = None
    line_items: Optional[List[Any]] = []


class GoodsReceiptNoteBase(BaseModel):
    grn_number: str
    po_number: Optional[str] = None
    received_date: Optional[date] = None
    line_items: Optional[List[Any]] = []


class JobResult(BaseModel):
    filename: str
    status: str  # Using str for flexibility
    message: str
    extracted_id: Optional[str] = None
    document_type: Optional[str] = None  # NEW: Add document type field


class JobBase(BaseModel):
    status: Optional[str] = "processing"
    total_files: Optional[int] = 0
    processed_files: Optional[int] = 0
    summary: Optional[List[JobResult]] = None


class AuditLogBase(BaseModel):
    user: str
    action: str
    summary: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


# --- Create Schemas (for receiving data) ---


class InvoiceCreate(InvoiceBase):
    pass


class PurchaseOrderCreate(PurchaseOrderBase):
    pass


class GoodsReceiptNoteCreate(GoodsReceiptNoteBase):
    pass


class JobCreate(JobBase):
    pass


class AuditLogCreate(AuditLogBase):
    entity_type: str
    entity_id: str
    invoice_db_id: Optional[int] = None


class LearnedHeuristicBase(BaseModel):
    vendor_name: str
    exception_type: str
    learned_condition: Dict[str, Any]
    resolution_action: str


class LearnedHeuristicCreate(LearnedHeuristicBase):
    pass


class LearnedHeuristic(LearnedHeuristicBase):
    id: int
    trigger_count: int
    confidence_score: float
    last_applied_at: datetime

    class Config:
        from_attributes = True


# --- START: NEW LEARNED PREFERENCE SCHEMAS ---
class LearnedPreferenceBase(BaseModel):
    preference_type: str
    context_key: str
    preference_value: str


class LearnedPreferenceCreate(LearnedPreferenceBase):
    pass


class LearnedPreference(LearnedPreferenceBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class UserActionPatternBase(BaseModel):
    pattern_type: str
    entity_name: str
    count: int
    last_detected: datetime


class UserActionPattern(UserActionPatternBase):
    id: int
    user_id: Optional[int] = None

    class Config:
        from_attributes = True


# --- END: NEW LEARNED PREFERENCE SCHEMAS ---


class NotificationBase(BaseModel):
    type: str
    message: str
    related_entity_id: Optional[str] = None
    related_entity_type: Optional[str] = None
    proposed_action: Optional[Dict[str, Any]] = None


class Notification(NotificationBase):
    id: int
    is_read: int
    created_at: datetime

    class Config:
        from_attributes = True


# --- Full Schemas (for sending data) ---


class Invoice(InvoiceBase):
    id: int
    status: DocumentStatus

    class Config:
        from_attributes = True


# --- START: MODIFIED INVOICE SUMMARY SCHEMA ---
class InvoiceSummary(BaseModel):
    """A lightweight schema for invoice list views."""

    id: int
    invoice_id: str
    vendor_name: Optional[str] = None
    grand_total: Optional[float] = None
    status: DocumentStatus
    invoice_date: Optional[date] = None
    sla_status: Optional[str] = None
    review_category: Optional[str] = None  # Add this field
    hold_until: Optional[datetime] = None  # Add this field

    class Config:
        from_attributes = True


# --- END: MODIFIED INVOICE SUMMARY SCHEMA ---


class PurchaseOrder(PurchaseOrderBase):
    id: int

    class Config:
        from_attributes = True


class GoodsReceiptNote(GoodsReceiptNoteBase):
    id: int

    class Config:
        from_attributes = True


class Job(JobBase):
    id: int
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AuditLog(AuditLogBase):
    id: int
    timestamp: datetime
    entity_type: str
    entity_id: str
    summary: Optional[str] = None

    class Config:
        from_attributes = True


# --- NEW: User and Role Schemas ---


class RoleBase(BaseModel):
    name: str


class RoleCreate(RoleBase):
    pass


class Role(RoleBase):
    id: int

    class Config:
        from_attributes = True


# --- NEW: Permission Policy Schemas ---


class PermissionPolicyBase(BaseModel):
    name: str
    conditions: Dict[str, Any]
    is_active: bool = True


class PermissionPolicyCreate(PermissionPolicyBase):
    pass


class PermissionPolicy(PermissionPolicyBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True


# --- END NEW PERMISSION POLICY SCHEMAS ---


class UserBase(BaseModel):
    email: str
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int
    is_active: bool
    is_approved: bool
    role: Role

    class Config:
        from_attributes = True


class UserWithVendors(User):
    permission_policies: List[PermissionPolicy] = []  # Changed from assigned_vendors


class VendorAssignmentRequest(BaseModel):
    # This is now obsolete, but we can repurpose it for policies
    vendor_names: List[str]


class UserRoleUpdate(BaseModel):
    role_name: str


# --- END NEW SCHEMAS ---

# --- API Request/Response Schemas ---


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    current_invoice_id: Optional[str] = None
    history: Optional[List[Dict[str, Any]]] = None


class ToolCall(BaseModel):
    name: str
    args: dict


class ChatResponse(BaseModel):
    conversation_id: str
    response_text: str
    tool_calls: Optional[List[ToolCall]] = None


class UpdateInvoiceStatusRequest(BaseModel):
    new_status: DocumentStatus
    reason: Optional[str] = None
    version: int  # Add version field for concurrency control


# --- Search Schemas ---


class FilterCondition(BaseModel):
    field: str
    operator: str
    value: Any


class SearchRequest(BaseModel):
    filters: List[FilterCondition] = Field(default_factory=list)
    search_term: Optional[str] = None
    sort_by: str = "invoice_date"
    sort_order: str = "desc"


# --- Purchase Order Update Schema ---
class PurchaseOrderUpdateRequest(BaseModel):
    changes: Dict[str, Any]
    version: int  # Version must be provided for concurrency control


# --- NEW CONFIGURATION SCHEMAS ---


class VendorSettingBase(BaseModel):
    vendor_name: str
    price_tolerance_percent: Optional[float] = None
    quantity_tolerance_percent: Optional[float] = None
    contact_email: Optional[str] = None


class VendorSettingCreate(VendorSettingBase):
    pass


class VendorSettingUpdate(VendorSettingBase):
    id: int  # Required to identify which setting to update


class VendorSetting(VendorSettingBase):
    id: int

    class Config:
        from_attributes = True


class AutomationRuleBase(BaseModel):
    rule_name: str
    description: Optional[str] = None
    vendor_name: Optional[str] = None
    conditions: Dict[str, Any]
    action: str
    is_active: Union[bool, int] = True
    source: str = "user"
    
    @field_validator('conditions', mode='before')
    @classmethod
    def parse_conditions(cls, v):
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {}
        return v if isinstance(v, dict) else {}
    
    @field_validator('is_active', mode='before')
    @classmethod
    def parse_is_active(cls, v):
        # Convert boolean to integer for database compatibility
        if isinstance(v, bool):
            return 1 if v else 0
        return v


class AutomationRuleCreate(AutomationRuleBase):
    pass


class AutomationRule(AutomationRuleBase):
    id: int
    rule_level: Optional[str] = None
    segment: Optional[str] = None
    customer_id: Optional[str] = None
    source_document: Optional[str] = None
    status: Optional[str] = "active"

    class Config:
        from_attributes = True


# --- ADD NEW SLA SCHEMAS ---
class SLABase(BaseModel):
    name: str
    description: Optional[str] = None
    conditions: Dict[str, Any]
    threshold_hours: int
    is_active: bool = True


class SLACreate(SLABase):
    pass


class SLA(SLABase):
    id: int

    class Config:
        from_attributes = True


# --- END OF SLA SCHEMAS ---


# ADD THESE NEW SCHEMAS
class CommentBase(BaseModel):
    user: str = "System"
    text: str
    type: str = "internal"


class CommentCreate(CommentBase):
    pass


class Comment(CommentBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class BatchActionRequest(BaseModel):
    invoice_ids: List[int]


class BatchUpdateStatusRequest(BaseModel):
    invoice_ids: List[int]
    new_status: str
    reason: Optional[str] = None


# --- NEW: Contract Note and Loan Schemas ---

class ContractNoteBase(BaseModel):
    filename: str
    file_path: str
    contract_emi_amount: Optional[float] = None
    contract_due_day: Optional[int] = None
    contract_late_fee_percent: Optional[float] = None
    contract_default_clause: Optional[str] = None
    contract_governing_law: Optional[str] = None
    contract_interest_rate: Optional[float] = None
    contract_loan_amount: Optional[float] = None
    contract_tenure_months: Optional[int] = None


class ContractNoteCreate(ContractNoteBase):
    extracted_data: Optional[Dict[str, Any]] = None


class ContractNote(ContractNoteBase):
    id: int
    extracted_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CustomerBase(BaseModel):
    customer_no: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    cbs_emi_amount: Optional[float] = None
    cbs_due_day: Optional[int] = None
    cbs_last_payment_date: Optional[date] = None
    cbs_outstanding_amount: Optional[float] = None
    cbs_risk_level: Optional[str] = None
    contract_note_id: Optional[int] = None
    
    # New fields from customer data spreadsheet
    cibil_score: Optional[int] = None
    days_since_employment: Optional[int] = None
    employment_status: Optional[str] = None
    cbs_income_verification: Optional[str] = None
    salary_last_date: Optional[date] = None
    pending_amount: Optional[float] = None
    pendency: Optional[str] = None
    segment: Optional[str] = None
    emi_pending: Optional[int] = None  # Number of EMIs pending


class CustomerCreate(CustomerBase):
    pass


class Customer(CustomerBase):
    id: int
    created_at: datetime
    updated_at: datetime
    contract_note: Optional[ContractNote] = None

    class Config:
        from_attributes = True


class LoanBase(BaseModel):
    loan_id: str
    customer_id: int
    loan_amount: float
    emi_amount: float
    tenure_months: int
    interest_rate: float
    status: str = "active"
    outstanding_amount: Optional[float] = None
    last_payment_date: Optional[date] = None
    next_due_date: Optional[date] = None


class LoanCreate(LoanBase):
    pass


class Loan(LoanBase):
    id: int
    created_at: datetime
    updated_at: datetime
    customer: Optional[Customer] = None

    class Config:
        from_attributes = True


class DataIntegrityAlertBase(BaseModel):
    alert_type: str
    customer_id: int
    severity: str = "high"
    title: str
    description: str
    cbs_value: Optional[str] = None
    contract_value: Optional[str] = None


class DataIntegrityAlertCreate(DataIntegrityAlertBase):
    pass


class DataIntegrityAlert(DataIntegrityAlertBase):
    id: int
    is_resolved: bool = False
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    customer: Optional[Customer] = None

    class Config:
        from_attributes = True


# Contract OCR extraction response
class ContractOCRResponse(BaseModel):
    success: bool
    extracted_data: Dict[str, Any]
    contract_fields: Dict[str, Any]

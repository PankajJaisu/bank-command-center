# src/app/db/models.py
import enum
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Date,
    JSON,
    Enum,
    ForeignKey,
    DateTime,
    func,
    Boolean,
    Table,
    Text,
    Numeric,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import sqltypes


# Database-agnostic JSON type that uses JSONB for PostgreSQL, JSON for others
class DatabaseJSON(sqltypes.TypeDecorator):
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        else:
            return dialect.type_descriptor(JSON())


# Define standard string lengths for consistency and performance
class StringLength:
    SHORT = 100  # For codes, IDs, short names
    MEDIUM = 255  # For names, emails, file paths
    LONG = 1000  # For addresses, descriptions
    XLARGE = 5000  # For notes, large text fields


Base = declarative_base()

# --- NEW: User Authentication & Role Models ---


class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(
        String(StringLength.SHORT), unique=True, index=True
    )  # e.g., 'admin', 'ap_processor'
    users = relationship("User", back_populates="role")


# --- START: NEW PERMISSION POLICY SYSTEM ---
# Removed vendor_assignment_table - replaced with PermissionPolicy model
# for more flexible, rule-based permissions


class PermissionPolicy(Base):
    __tablename__ = "permission_policies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(StringLength.MEDIUM), nullable=False, default="Default Policy")
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # This will store the new, flexible JSON structure
    conditions = Column(DatabaseJSON, nullable=False)
    is_active = Column(Boolean, default=True)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(StringLength.MEDIUM), unique=True, index=True, nullable=False)
    hashed_password = Column(String(StringLength.MEDIUM), nullable=False)
    full_name = Column(String(StringLength.MEDIUM), nullable=True)
    is_active = Column(Boolean, default=True)
    is_approved = Column(Boolean, default=False)

    role_id = Column(Integer, ForeignKey("roles.id"))
    role = relationship("Role", back_populates="users")

    # New policy-based permission system
    permission_policies = relationship("PermissionPolicy", cascade="all, delete-orphan")


# --- END NEW MODELS ---


# --- NEW: Association table for Invoices and Purchase Orders ---
class InvoicePurchaseOrderAssociation(Base):
    __tablename__ = "invoice_po_association"
    invoice_id = Column(
        Integer, ForeignKey("invoices.id", ondelete="CASCADE"), primary_key=True
    )
    po_id = Column(
        Integer, ForeignKey("purchase_orders.id", ondelete="CASCADE"), primary_key=True
    )


# --- NEW: Association table for Invoices and GRNs ---
class InvoiceGRNAssociation(Base):
    __tablename__ = "invoice_grn_association"
    invoice_id = Column(
        Integer, ForeignKey("invoices.id", ondelete="CASCADE"), primary_key=True
    )
    grn_id = Column(
        Integer,
        ForeignKey("goods_receipt_notes.id", ondelete="CASCADE"),
        primary_key=True,
    )


class DocumentStatus(str, enum.Enum):
    ingested = "ingested"
    matching = "matching"
    needs_review = "needs_review"
    pending_vendor_response = "pending_vendor_response"
    pending_internal_response = "pending_internal_response"
    on_hold = "on_hold"
    matched = "matched"
    qa_approval = "qa_approval"  # --- ADD THIS LINE ---
    pending_payment = "pending_payment"
    paid = "paid"
    rejected = "rejected"


class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, default="processing")
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    total_files = Column(Integer, default=0)
    processed_files = Column(Integer, default=0)
    summary = Column(JSON, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user = Column(String, default="System")
    entity_type = Column(String, index=True)
    entity_id = Column(String, index=True)
    action = Column(String)
    summary = Column(String, nullable=True)
    details = Column(JSON, nullable=True)
    invoice_db_id = Column(
        Integer,
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    invoice = relationship("Invoice", back_populates="audit_logs")


class VendorSetting(Base):
    __tablename__ = "vendor_settings"
    id = Column(Integer, primary_key=True, index=True)
    vendor_name = Column(
        String(StringLength.MEDIUM), unique=True, index=True, nullable=False
    )
    price_tolerance_percent = Column(Float, nullable=True)
    quantity_tolerance_percent = Column(Float, nullable=True)
    contact_email = Column(String, nullable=True)
    bank_details = Column(JSON, nullable=True)

    # --- REMOVED: Old vendor assignment relationship ---
    # Now using flexible PermissionPolicy system instead


class LearnedHeuristic(Base):
    __tablename__ = "learned_heuristics"
    id = Column(Integer, primary_key=True, index=True)
    vendor_name = Column(String, index=True, nullable=False)
    exception_type = Column(String, index=True, nullable=False)
    learned_condition = Column(DatabaseJSON, nullable=False)
    resolution_action = Column(String, nullable=False)
    trigger_count = Column(Integer, default=1)
    confidence_score = Column(Float, default=0.1)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_applied_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    is_dismissed = Column(Boolean, default=False, nullable=False)


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, index=True, nullable=False)
    message = Column(String, nullable=False)
    related_entity_id = Column(String, nullable=True)
    related_entity_type = Column(String, nullable=True)
    proposed_action = Column(JSON, nullable=True)
    is_read = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class AutomationRule(Base):
    __tablename__ = "automation_rules"
    id = Column(Integer, primary_key=True, index=True)
    rule_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)  # Add description field for sophisticated rule descriptions
    source = Column(String, default="user")
    vendor_name = Column(String, index=True, nullable=True)
    conditions = Column(JSON, nullable=False)
    action = Column(String, nullable=False)
    is_active = Column(Integer, default=1)
    
    # New fields for policy upload and rule management
    rule_level = Column(String, nullable=True)  # system, segment, customer
    segment = Column(String, nullable=True)  # segment name if rule_level is 'segment'
    customer_id = Column(String, nullable=True)  # customer ID if rule_level is 'customer'
    source_document = Column(String, nullable=True)  # original policy document filename
    status = Column(String, default="active")  # active, pending_review, draft


class SLA(Base):
    __tablename__ = "slas"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    # Conditions define which invoices this SLA applies to
    conditions = Column(JSON, nullable=False)
    # Threshold in hours after which the SLA is considered breached
    threshold_hours = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)


# --- START: NEW MODEL FOR INSIGHT GENERATION ---
class UserActionPattern(Base):
    __tablename__ = "user_action_patterns"
    id = Column(Integer, primary_key=True, index=True)
    pattern_type = Column(
        String, index=True, nullable=False
    )  # e.g., 'MANUAL_PO_CREATION'
    entity_name = Column(String, index=True, nullable=False)  # e.g., Vendor Name
    count = Column(Integer, default=1, nullable=False)
    last_detected = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Optional: link to a user if the pattern is user-specific
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User")


# --- START: NEW MODEL FOR CONVERSATIONAL LEARNING ---
class LearnedPreference(Base):
    __tablename__ = "learned_preferences"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    preference_type = Column(
        String, index=True, nullable=False
    )  # e.g., 'PREFERRED_VENDOR_CONTACT'
    context_key = Column(
        String, index=True, nullable=False
    )  # e.g., Vendor Name "Acme Inc"
    preference_value = Column(String, nullable=False)  # e.g., "john.doe@acme.com"
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User")


# --- END: NEW MODEL FOR CONVERSATIONAL LEARNING ---
# --- END: NEW MODEL FOR INSIGHT GENERATION ---


# --- START: NEW MODEL FOR FAILED INGESTIONS ---
class FailedIngestion(Base):
    __tablename__ = "failed_ingestions"
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    filename = Column(String, nullable=False)
    document_type = Column(
        String, nullable=False
    )  # 'PurchaseOrder' or 'GoodsReceiptNote'
    raw_data = Column(JSON, nullable=False)
    error_message = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job")


# --- END: NEW MODEL FOR FAILED INGESTIONS ---


class DocumentTypeEnum(str, enum.Enum):
    Invoice = "Invoice"
    PurchaseOrder = "PurchaseOrder"
    GoodsReceiptNote = "GoodsReceiptNote"


class ExtractionFieldConfiguration(Base):
    __tablename__ = "extraction_field_configurations"
    id = Column(Integer, primary_key=True, index=True)
    document_type = Column(Enum(DocumentTypeEnum), nullable=False, index=True)
    field_name = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)
    is_editable = Column(Boolean, default=False, nullable=False)
    is_essential = Column(Boolean, default=False, nullable=False)


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    id = Column(Integer, primary_key=True, index=True)
    po_number = Column(
        String(StringLength.SHORT), unique=True, index=True, nullable=False
    )
    vendor_name = Column(String(StringLength.MEDIUM))
    buyer_name = Column(String(StringLength.MEDIUM))
    order_date = Column(Date, nullable=True)
    line_items = Column(JSON, nullable=True)
    # --- NEW: Store the complete data payload used for PDF generation ---
    raw_data_payload = Column(JSON, nullable=True)
    file_path = Column(String, nullable=True)
    subtotal = Column(Float, nullable=True)
    tax = Column(Float, nullable=True)
    grand_total = Column(Float, nullable=True)

    # --- START: ADD VERSION FOR CONCURRENCY CONTROL ---
    version = Column(Integer, nullable=False, default=1, server_default="1")
    __mapper_args__ = {
        "version_id_col": version,
        "version_id_generator": False,
    }
    # --- END: ADD VERSION FOR CONCURRENCY CONTROL ---

    # One-to-many relationship: One PO can have multiple GRNs
    grns = relationship("GoodsReceiptNote", back_populates="po")

    # --- MODIFIED: Many-to-many relationship with Invoice ---
    invoices = relationship(
        "Invoice", secondary="invoice_po_association", back_populates="purchase_orders"
    )

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GoodsReceiptNote(Base):
    __tablename__ = "goods_receipt_notes"
    id = Column(Integer, primary_key=True, index=True)
    grn_number = Column(String, unique=True, index=True, nullable=False)
    po_number = Column(String, ForeignKey("purchase_orders.po_number"), nullable=True)
    received_date = Column(Date, nullable=True)
    line_items = Column(JSON, nullable=True)
    file_path = Column(String, nullable=True)

    # Many-to-one relationship: A GRN belongs to one PO
    po = relationship("PurchaseOrder", back_populates="grns")

    # --- MODIFIED: Many-to-many relationship with Invoice ---
    invoices = relationship(
        "Invoice", secondary="invoice_grn_association", back_populates="grns"
    )

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(
        String(StringLength.SHORT), unique=True, index=True, nullable=False
    )
    vendor_name = Column(String(StringLength.MEDIUM))
    vendor_address = Column(String(StringLength.LONG), nullable=True)
    buyer_name = Column(String(StringLength.MEDIUM))
    buyer_address = Column(String(StringLength.LONG), nullable=True)
    shipping_address = Column(String(StringLength.LONG), nullable=True)
    billing_address = Column(String(StringLength.LONG), nullable=True)
    payment_terms = Column(String(StringLength.MEDIUM), nullable=True)
    other_header_fields = Column(JSON, nullable=True)

    # --- NEW: Stores an array of PO numbers found on the invoice for easy lookup. ---
    # This is our source of truth for linking.
    related_po_numbers = Column(JSON, nullable=True, default=list)

    # --- NEW: Stores an array of GRN numbers found on the invoice. ---
    # Per your clarification, we will extract this but the primary link is via PO.
    related_grn_numbers = Column(JSON, nullable=True, default=list)

    invoice_date = Column(Date, nullable=True)
    due_date = Column(Date, nullable=True)
    subtotal = Column(Float, nullable=True)
    tax = Column(Float, nullable=True)
    grand_total = Column(Float, nullable=True)
    line_items = Column(JSON, nullable=True)
    invoice_metadata = Column(
        DatabaseJSON, nullable=True
    )  # NEW: Store additional key-value pairs extracted from invoice

    # --- MODIFIED: This now stores a complete, step-by-step trace of the matching process. ---
    match_trace = Column(JSON, nullable=True)

    status = Column(
        Enum(DocumentStatus), default=DocumentStatus.ingested, nullable=False
    )
    review_category = Column(String, nullable=True)
    ai_recommendation = Column(JSON, nullable=True)
    file_path = Column(String, nullable=True)
    notes = Column(Text, nullable=True)  # Use Text for potentially long notes
    gl_code = Column(String(StringLength.SHORT), nullable=True)
    discount_terms = Column(String(StringLength.MEDIUM), nullable=True)
    discount_amount = Column(Float, nullable=True)
    discount_due_date = Column(Date, nullable=True)
    paid_date = Column(Date, nullable=True)
    payment_batch_id = Column(String, index=True, nullable=True)
    hold_until = Column(DateTime, nullable=True)

    # --- START: ADD VERSION FOR CONCURRENCY CONTROL ---
    version = Column(Integer, nullable=False, default=1, server_default="1")
    __mapper_args__ = {
        "version_id_col": version,
        "version_id_generator": False,
    }
    # --- END: ADD VERSION FOR CONCURRENCY CONTROL ---

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)
    job = relationship("Job")

    # --- NEW: Many-to-many relationships ---
    purchase_orders = relationship(
        "PurchaseOrder",
        secondary="invoice_po_association",
        back_populates="invoices",
        cascade="all, delete",
    )
    grns = relationship(
        "GoodsReceiptNote",
        secondary="invoice_grn_association",
        back_populates="invoices",
        cascade="all, delete",
    )
    comments = relationship(
        "Comment", back_populates="invoice", cascade="all, delete-orphan"
    )
    audit_logs = relationship(
        "AuditLog", back_populates="invoice", cascade="all, delete-orphan"
    )


# --- NEW: Contract and Loan Models for Loan Collections ---

class ContractNote(Base):
    __tablename__ = "contract_notes"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(StringLength.MEDIUM), nullable=False)
    file_path = Column(String(StringLength.MEDIUM), nullable=False)
    extracted_data = Column(DatabaseJSON, nullable=True)
    
    # Extracted contract fields
    contract_emi_amount = Column(Float, nullable=True)
    contract_due_day = Column(Integer, nullable=True)  # e.g., 5 for 5th of month
    contract_late_fee_percent = Column(Float, nullable=True)
    contract_default_clause = Column(String(StringLength.LONG), nullable=True)
    contract_governing_law = Column(String(StringLength.MEDIUM), nullable=True)
    contract_interest_rate = Column(Float, nullable=True)
    contract_loan_amount = Column(Float, nullable=True)
    contract_tenure_months = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to customers/loans
    customers = relationship("Customer", back_populates="contract_note")


class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    customer_no = Column(String(StringLength.SHORT), unique=True, index=True, nullable=False)
    name = Column(String(StringLength.MEDIUM), nullable=False)
    email = Column(String(StringLength.MEDIUM), nullable=True)
    phone = Column(String(StringLength.SHORT), nullable=True)
    address = Column(String(StringLength.LONG), nullable=True)
    
    # CBS data fields
    cbs_emi_amount = Column(Float, nullable=True)
    cbs_due_day = Column(Integer, nullable=True)
    cbs_last_payment_date = Column(Date, nullable=True)
    cbs_outstanding_amount = Column(Float, nullable=True)
    cbs_risk_level = Column(String(StringLength.SHORT), nullable=True)  # RED, AMBER, GREEN
    
    # New fields from customer data spreadsheet
    cibil_score = Column(Integer, nullable=True)  # CIBIL score (e.g., 720, 650, 580)
    days_since_employment = Column(Integer, nullable=True)  # Days since employment 
    employment_status = Column(String(StringLength.SHORT), nullable=True)  # Verified, Unverified
    cbs_income_verification = Column(String(StringLength.SHORT), nullable=True)  # Income verification percentage
    segment = Column(String(StringLength.SHORT), nullable=True)
    emi_pending = Column(Integer, nullable=True)  # Number of EMIs pending
    salary_last_date = Column(Date, nullable=True)  # Last salary credit date
    pending_amount = Column(Float, nullable=True)  # Pending EMI amount
    pendency = Column(String(StringLength.SHORT), nullable=True)  # Yes/No pendency status
    
    # Contract relationship
    contract_note_id = Column(Integer, ForeignKey("contract_notes.id"), nullable=True)
    contract_note = relationship("ContractNote", back_populates="customers")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    loans = relationship("Loan", back_populates="customer")


class Loan(Base):
    __tablename__ = "loans"
    id = Column(Integer, primary_key=True, index=True)
    loan_id = Column(String(StringLength.SHORT), unique=True, index=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    
    # Loan details
    loan_amount = Column(Float, nullable=False)
    emi_amount = Column(Float, nullable=False)
    tenure_months = Column(Integer, nullable=False)
    interest_rate = Column(Float, nullable=False)
    
    # Status fields
    status = Column(String(StringLength.SHORT), nullable=False, default="active")  # active, closed, npa
    outstanding_amount = Column(Float, nullable=True)
    last_payment_date = Column(Date, nullable=True)
    next_due_date = Column(Date, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    customer = relationship("Customer", back_populates="loans")


# --- NEW: Data Integrity Alert Model ---
class DataIntegrityAlert(Base):
    __tablename__ = "data_integrity_alerts"
    id = Column(Integer, primary_key=True, index=True)
    alert_type = Column(String(StringLength.SHORT), nullable=False)  # EMI_MISMATCH, DUE_DAY_MISMATCH, etc.
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    severity = Column(String(StringLength.SHORT), nullable=False, default="high")  # high, medium, low
    
    # Alert details
    title = Column(String(StringLength.MEDIUM), nullable=False)
    description = Column(String(StringLength.LONG), nullable=False)
    cbs_value = Column(String(StringLength.MEDIUM), nullable=True)
    contract_value = Column(String(StringLength.MEDIUM), nullable=True)
    
    # Status
    is_resolved = Column(Boolean, default=False)
    resolved_by = Column(String(StringLength.MEDIUM), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    customer = relationship("Customer")


class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(
        Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False
    )
    user = Column(String, default="System")
    text = Column(Text, nullable=False)  # Use Text for comment content
    created_at = Column(DateTime, default=datetime.utcnow)
    type = Column(String, default="internal")
    invoice = relationship("Invoice", back_populates="comments")




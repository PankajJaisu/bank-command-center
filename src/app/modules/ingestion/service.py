# src/app/modules/ingestion/service.py
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Dict, Tuple, List, Any
from datetime import datetime, date
import json
import re

from app.config import QUANTITY_TOLERANCE_PERCENT
from app.db import models
from app.modules.ingestion import extractor
from app.utils import unit_converter


def build_extraction_prompt(db: Session) -> str:
    base_prompt = """You are an elite Accounts Payable data extraction engine. Your task is to analyze the attached document with extreme precision and return ONLY a single, minified JSON object.

**Critical Rules:**
1.  **Identify Document Type:** First, classify the document by searching for keywords like "Invoice", "Purchase Order", "Goods Receipt", "Loan", "Bank Reconciliation", or "Command Center". This is the most important step. The `document_type` field MUST be one of: "PurchaseOrder", "GoodsReceiptNote", "Invoice", or "Error".
2.  **Special Financial Document Handling:** If the document contains any of these patterns, treat it as an "Invoice" document type with special formatting:
   - Loan-related keywords: "loan", "credit", "financing", "lending", "borrower", "lender" → Use "LOAN-" prefix
   - Bank reconciliation: "bank reconciliation", "reconciliation summary", "loan command center" → Use "RECON-" prefix
   - Use current date in YYYYMMDD format for the ID suffix (e.g., "LOAN-20250814", "RECON-20250814")
3.  **Strict Schema Adherence:** Extract data *only* for the fields listed in the schema for the identified document type. Do not invent fields.
4.  **Data Typing:** Dates MUST be "YYYY-MM-DD". Numbers MUST be pure numeric types (integer or float) with no currency symbols or commas.
5.  **Array Rule:** `related_po_numbers` and `related_grn_numbers` MUST ALWAYS be string arrays. If one number is found, return `["PO-123"]`. If none, return `[]`.
6.  **Line Item Rule:** Do NOT extract shipping, handling, or other summary charges as line items. Line items are only for tangible goods or services with a quantity and price.
7.  **Multi-Document Rule:** If the PDF contains multiple separate documents (e.g., an invoice followed by its PO), extract data ONLY for the FIRST document you identify.
8.  **Metadata Extraction:** Identify any other relevant key-value pairs on the document header and place them in a single `metadata` JSON object. For bank reconciliation reports, include: report_date, company, account_number, reconciliation_type, balance_per_bank, adjusted_ledger_balance, unreconciled_items, etc.
9.  **Output Format:** Provide only the final JSON object. Do not include any other text, explanations, or markdown formatting like ```json.

**Output Examples (Follow this structure precisely):**
*   **Invoice with one PO:** `{"document_type":"Invoice","invoice_id":"INV-98002","vendor_name":"Acme Manufacturing","related_po_numbers":["PO-AC-1001"],"related_grn_numbers":[],"grand_total":594.00,"metadata":{"customer_id":"CUST-123","account_no":"ACC-456"},...}`
*   **Invoice with multiple POs:** `{"document_type":"Invoice","invoice_id":"INV-98005","vendor_name":"Global Supplies Co","related_po_numbers":["PO-ST-78005-A","PO-ST-78005-B"],"related_grn_numbers":[],"grand_total":4050.00,"metadata":{"order_ref":"ORD-789","terms":"NET30"},...}`
*   **Loan Document:** `{"document_type":"Invoice","invoice_id":"LOAN-20250814","vendor_name":"First National Bank","related_po_numbers":[],"related_grn_numbers":[],"grand_total":100000.00,"metadata":{"loan_id":"L-789123","contract_number":"CNT-456","borrower":"ABC Corp"},...}`
*   **Bank Reconciliation:** `{"document_type":"Invoice","invoice_id":"RECON-20250814","vendor_name":"ICICI Bank","related_po_numbers":[],"related_grn_numbers":[],"grand_total":1550750.00,"metadata":{"account_number":"49848382882828","report_date":"2025-08-14","company":"Supervity","reconciliation_type":"Loan Command Center"},...}`
*   **Purchase Order:** `{"document_type":"PurchaseOrder","po_number":"PO-AC-1001","vendor_name":"Acme Manufacturing","order_date":"2024-03-05","grand_total":540.00,...}`
*   **Goods Receipt Note:** `{"document_type":"GoodsReceiptNote","grn_number":"GRN-AC-1001","po_number":"PO-AC-1001","received_date":"2024-03-15",...}`

**Your Task:** Now, analyze the attached document and generate the JSON based on the following dynamic schemas.
**JSON Schemas:**
"""
    schemas_parts = []
    configs = (
        db.query(models.ExtractionFieldConfiguration).filter_by(is_enabled=True).all()
    )

    def get_schema_fields_str(doc_type):
        fields = [c for c in configs if c.document_type == doc_type]
        schema_fields = [f'"{f.field_name}": "..."' for f in fields]
        if doc_type == models.DocumentTypeEnum.Invoice:
            schema_fields.append(
                '"line_items": [{"description": "...", "quantity": "...", "unit_price": "...", "line_total": "..."}]'
            )
            schema_fields = [
                s
                for s in schema_fields
                if "related_po_numbers" not in s and "related_grn_numbers" not in s
            ]
            schema_fields.append('"related_po_numbers": ["..."]')
            schema_fields.append('"related_grn_numbers": ["..."]')
            schema_fields.append('"metadata": {"key1": "value1", "key2": "value2"}')
        elif doc_type == models.DocumentTypeEnum.PurchaseOrder:
            schema_fields.append(
                '"line_items": [{"description": "...", "ordered_qty": "...", "unit_price": "...", "line_total": "..."}]'
            )
        elif doc_type == models.DocumentTypeEnum.GoodsReceiptNote:
            schema_fields.append(
                '"line_items": [{"description": "...", "received_qty": "..."}]'
            )
        return ", ".join(schema_fields)

        for doc_type in models.DocumentTypeEnum:
            schema_fields_str = get_schema_fields_str(doc_type)
            schemas_parts.append(
                f'\n**If {doc_type.value}:**\n{{"document_type": "{doc_type.value}", {schema_fields_str}}}'
            )

    error_schema = '\n**If Unreadable:**\n{"document_type": "Error", "error_message": "The document is illegible or not a recognizable AP document type."}'

    return base_prompt


def build_policy_extraction_prompt(db: Session) -> str:
    """
    Build a specialized prompt for extracting rules from loan policy documents.
    This prompt focuses on identifying risk assessment rules, conditions, and actions.
    """
    policy_prompt = """You are an expert loan policy analyzer. Your task is to extract risk assessment rules from loan policy documents and return them as a structured JSON object.

**Critical Rules:**
1. **Rule Identification:** Look for sections that define risk levels, customer categorization, or automated actions based on customer data.
2. **Condition Extraction:** Identify specific conditions like credit score thresholds, missed payments, overdue amounts, etc.
3. **Action Mapping:** Map policy statements to risk levels (red/critical, amber/medium, green/low).
4. **Structured Output:** Return rules in a standardized format that can be converted to automation rules.

**Expected JSON Structure:**
{
  "document_type": "PolicyDocument",
  "policy_name": "...",
  "effective_date": "YYYY-MM-DD",
  "rules": [
    {
      "name": "Rule Name",
      "description": "Clear description of when this rule applies",
      "conditions": {
        "logical_operator": "AND",
        "conditions": [
          {
            "field": "credit_score",
            "operator": "<=",
            "value": 650
          },
          {
            "field": "missed_emis",
            "operator": ">=",
            "value": 2
          }
        ]
      },
      "action": "Send Legal Notice",
      "priority": 1
    }
  ],
  "metadata": {
    "document_version": "...",
    "approval_authority": "...",
    "review_date": "..."
  }
}

**Field Mappings:**
- Credit Score: "credit_score"
- Missed EMIs: "missed_emis"
- Days Overdue: "days_overdue"
- Monthly Income: "monthly_income"
- Total Outstanding: "total_outstanding"
- Payment Disputes: "payment_disputes"

**Action Mappings:**
- Critical/High Risk → "Send Legal Notice" or "Block Account"
- Medium/Moderate Risk → "Send Reminder" or "Make Phone Call"
- Low/Good Risk → "Send Email" or "Monitor Account"
- Escalation → "Escalate to Manager" or "Field Visit"

**Instructions:**
1. Read the entire policy document carefully
2. Identify ONLY the most important risk assessment criteria and thresholds
3. Generate a MAXIMUM of 5 rules per document - focus on the most critical ones
4. Consolidate similar conditions into single comprehensive rules
5. Convert policy language into structured conditions
6. Assign appropriate collection actions based on severity
7. Return ONLY the JSON object, no additional text

**Example Policy Text → Rule Conversion:**
"Customers with credit scores below 650 and more than 2 missed EMI payments should be classified as high risk"
→
{
  "name": "High Risk - Low Credit Score with Missed Payments",
  "description": "Customers with credit scores below 650 and more than 2 missed EMI payments",
  "conditions": {
    "logical_operator": "AND",
    "conditions": [
      {"field": "credit_score", "operator": "<", "value": 650},
      {"field": "missed_emis", "operator": ">", "value": 2}
    ]
  },
  "action": "Send Legal Notice",
  "priority": 1
}

Now analyze the attached policy document and extract all risk assessment rules:"""

    return policy_prompt


def convert_string_to_date(date_string: str | None) -> date | None:
    if not date_string:
        return None
    try:
        return datetime.strptime(date_string, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def validate_required_fields(extracted_data: Dict, doc_type: str) -> Tuple[bool, str]:
    if doc_type == "PurchaseOrder" and not extracted_data.get("po_number"):
        return False, "Purchase Order is missing required field: po_number"
    if doc_type == "GoodsReceiptNote" and not extracted_data.get("grn_number"):
        return False, "Goods Receipt Note is missing required field: grn_number"
    if doc_type == "Invoice":
        invoice_id = extracted_data.get("invoice_id")
        if not invoice_id:
            return False, "Invoice is missing required field: invoice_id"
        # Special handling for financial documents - they're valid even with minimal fields
        if invoice_id.startswith(("LOAN-", "RECON-")):
            return True, ""  # Financial documents are considered valid with just an invoice_id
    return True, ""


def prepare_po_data(extracted_data: Dict) -> Dict:
    line_items = extracted_data.get("line_items", [])
    if line_items and isinstance(line_items, list):
        extracted_data["line_items"] = [
            unit_converter.normalize_item(item) for item in line_items
        ]
    return {
        "po_number": extracted_data.get("po_number"),
        "vendor_name": extracted_data.get("vendor_name"),
        "buyer_name": extracted_data.get("buyer_name"),
        "order_date": convert_string_to_date(extracted_data.get("order_date")),
        "line_items": extracted_data.get("line_items"),
        "raw_data_payload": extracted_data,
        "subtotal": extracted_data.get("subtotal"),
        "tax": extracted_data.get("tax"),
        "grand_total": extracted_data.get("grand_total"),
    }


def prepare_grn_data(extracted_data: Dict) -> Dict:
    line_items_str = extracted_data.get("line_items")
    line_items = []
    if isinstance(line_items_str, str):
        try:
            line_items = json.loads(line_items_str)
        except json.JSONDecodeError:
            line_items = []
    elif isinstance(line_items_str, list):
        line_items = line_items_str
    if line_items:
        extracted_data["line_items"] = [
            unit_converter.normalize_item(item) for item in line_items
        ]
    return {
        "grn_number": extracted_data.get("grn_number"),
        "po_number": extracted_data.get("po_number"),
        "received_date": convert_string_to_date(extracted_data.get("received_date")),
        "line_items": extracted_data.get("line_items"),
    }


def prepare_invoice_data(extracted_data: Dict, job_id: int) -> Dict:
    line_items = extracted_data.get("line_items", [])
    if line_items and isinstance(line_items, list):
        extracted_data["line_items"] = [
            unit_converter.normalize_item(item) for item in line_items
        ]
    return {
        "invoice_id": extracted_data.get("invoice_id"),
        "vendor_name": extracted_data.get("vendor_name"),
        "buyer_name": extracted_data.get("buyer_name"),
        "invoice_date": convert_string_to_date(extracted_data.get("invoice_date")),
        "due_date": convert_string_to_date(extracted_data.get("due_date")),
        "subtotal": extracted_data.get("subtotal"),
        "tax": extracted_data.get("tax"),
        "grand_total": extracted_data.get("grand_total"),
        "line_items": extracted_data.get("line_items"),
        "discount_terms": extracted_data.get("discount_terms"),
        "discount_amount": extracted_data.get("discount_amount"),
        "discount_due_date": convert_string_to_date(
            extracted_data.get("discount_due_date")
        ),
        "related_po_numbers": (
            extracted_data.get("related_po_numbers", [])
            if isinstance(extracted_data.get("related_po_numbers"), list)
            else []
        ),
        "related_grn_numbers": (
            extracted_data.get("related_grn_numbers", [])
            if isinstance(extracted_data.get("related_grn_numbers"), list)
            else []
        ),
        "job_id": job_id,
        "status": models.DocumentStatus.ingested,
        "vendor_address": extracted_data.get("vendor_address"),
        "buyer_address": extracted_data.get("buyer_address"),
        "shipping_address": extracted_data.get("shipping_address"),
        "billing_address": extracted_data.get("billing_address"),
        "payment_terms": extracted_data.get("payment_terms"),
        "other_header_fields": extracted_data.get("other_header_fields"),
        "invoice_metadata": extracted_data.get("metadata"),
    }


def _save_po_from_dict(
    db: Session, po_data: Dict[str, Any], job_id: int
) -> Tuple[models.PurchaseOrder | None, str | None]:
    po_number = po_data.get("po_number")
    filename = po_data.get("file_path", "structured_file")
    if not po_number:
        error_message = "Missing po_number."
        db.add(
            models.FailedIngestion(
                job_id=job_id,
                filename=filename,
                document_type="PurchaseOrder",
                raw_data=po_data,
                error_message=error_message,
            )
        )
        return None, error_message
    if db.query(models.PurchaseOrder).filter_by(po_number=po_number).first():
        error_message = f"PO {po_number} already exists."
        db.add(
            models.FailedIngestion(
                job_id=job_id,
                filename=filename,
                document_type="PurchaseOrder",
                raw_data=po_data,
                error_message=error_message,
            )
        )
        return None, error_message
    try:
        prepared_data = prepare_po_data(po_data)
        new_po = models.PurchaseOrder(**prepared_data, file_path=filename)
        db.add(new_po)
        return new_po, None
    except Exception as e:
        error_message = str(e)
        db.add(
            models.FailedIngestion(
                job_id=job_id,
                filename=filename,
                document_type="PurchaseOrder",
                raw_data=po_data,
                error_message=error_message,
            )
        )
        return None, error_message


def _save_grn_from_dict(
    db: Session, grn_data: Dict[str, Any], job_id: int
) -> Tuple[models.GoodsReceiptNote | None, str | None]:
    grn_number = grn_data.get("grn_number")
    filename = grn_data.get("file_path", "structured_file")
    if not grn_number:
        error_message = "Missing grn_number."
        db.add(
            models.FailedIngestion(
                job_id=job_id,
                filename=filename,
                document_type="GoodsReceiptNote",
                raw_data=grn_data,
                error_message=error_message,
            )
        )
        return None, error_message
    if db.query(models.GoodsReceiptNote).filter_by(grn_number=grn_number).first():
        error_message = f"GRN {grn_number} already exists."
        db.add(
            models.FailedIngestion(
                job_id=job_id,
                filename=filename,
                document_type="GoodsReceiptNote",
                raw_data=grn_data,
                error_message=error_message,
            )
        )
        return None, error_message
    try:
        prepared_data = prepare_grn_data(grn_data)

        # CRITICAL FIX: Check if referenced PO exists before setting po_number
        referenced_po_number = prepared_data.get("po_number")
        if referenced_po_number:
            po = (
                db.query(models.PurchaseOrder)
                .filter_by(po_number=referenced_po_number)
                .first()
            )
            if not po:
                from app.utils.logging import get_logger

                logger = get_logger(__name__)
                logger.warning(
                    f"GRN {grn_number} references non-existent PO {referenced_po_number}, setting po_number to None"
                )
                prepared_data["po_number"] = (
                    None  # Remove invalid foreign key reference
                )

        new_grn = models.GoodsReceiptNote(**prepared_data, file_path=filename)

        # Set the relationship if PO exists
        if referenced_po_number and prepared_data.get("po_number"):
            po = (
                db.query(models.PurchaseOrder)
                .filter_by(po_number=referenced_po_number)
                .first()
            )
            if po:
                new_grn.po = po

        db.add(new_grn)
        return new_grn, None
    except Exception as e:
        error_message = str(e)
        db.add(
            models.FailedIngestion(
                job_id=job_id,
                filename=filename,
                document_type="GoodsReceiptNote",
                raw_data=grn_data,
                error_message=error_message,
            )
        )
        return None, error_message


# --- START MODIFICATION: Handle Duplicate Invoices ---
def _save_invoice_from_dict(
    db: Session, invoice_data: Dict[str, Any], job_id: int
) -> Tuple[models.Invoice | None, str | None]:
    invoice_id = invoice_data.get("invoice_id")
    filename = invoice_data.get("file_path", "structured_file")

    if not invoice_id:
        error_message = "Missing invoice_id."
        db.add(
            models.FailedIngestion(
                job_id=job_id,
                filename=filename,
                document_type="Invoice",
                raw_data=invoice_data,
                error_message=error_message,
            )
        )
        return None, error_message

    vendor_name = invoice_data.get("vendor_name")
    if vendor_name:
        existing_setting = (
            db.query(models.VendorSetting)
            .filter(models.VendorSetting.vendor_name == vendor_name)
            .first()
        )
        vendor_in_session = any(
            isinstance(obj, models.VendorSetting) and obj.vendor_name == vendor_name
            for obj in db.new
        )
        if not existing_setting and not vendor_in_session:
            from app.config import PRICE_TOLERANCE_PERCENT, QUANTITY_TOLERANCE_PERCENT

            db.add(
                models.VendorSetting(
                    vendor_name=vendor_name,
                    price_tolerance_percent=PRICE_TOLERANCE_PERCENT,
                    quantity_tolerance_percent=QUANTITY_TOLERANCE_PERCENT,
                )
            )

    existing_invoice = db.query(models.Invoice).filter_by(invoice_id=invoice_id).first()
    if existing_invoice:
        # Instead of returning an error, create a new record with a REJECTED status.
        # This makes the system's action visible to the user.
        try:
            # We must assign a new, unique invoice_id for the database record
            # while keeping the original for context. We can append a timestamp.
            unique_id_for_db = f"{invoice_id}-DUP-{datetime.utcnow().timestamp()}"

            prepared_data = prepare_invoice_data(invoice_data, job_id)
            # Override key fields for the duplicate record
            prepared_data["invoice_id"] = (
                unique_id_for_db  # Use the unique ID for the primary key
            )
            prepared_data["status"] = models.DocumentStatus.rejected

            # Create a clear trace log explaining the rejection
            trace = [
                {
                    "step": "Ingestion Check",
                    "status": "FAIL",
                    "message": f"Duplicate invoice detected. Original invoice '{invoice_id}' already exists in the system.",
                    "details": {"original_invoice_id": invoice_id},
                }
            ]

            new_duplicate_invoice = models.Invoice(
                **prepared_data, file_path=filename, match_trace=trace
            )
            db.add(new_duplicate_invoice)
            return new_duplicate_invoice, "Processed as Duplicate (Rejected)"
        except Exception as e:
            error_message = f"Error processing duplicate invoice: {e}"
            db.add(
                models.FailedIngestion(
                    job_id=job_id,
                    filename=filename,
                    document_type="Invoice",
                    raw_data=invoice_data,
                    error_message=error_message,
                )
            )
            return None, error_message

    # This is the normal path for a new, non-duplicate invoice
    try:
        prepared_data = prepare_invoice_data(invoice_data, job_id)
        new_invoice = models.Invoice(**prepared_data, file_path=filename)
        db.add(new_invoice)
        return new_invoice, None
    except Exception as e:
        error_message = str(e)
        db.add(
            models.FailedIngestion(
                job_id=job_id,
                filename=filename,
                document_type="Invoice",
                raw_data=invoice_data,
                error_message=error_message,
            )
        )
        return None, error_message


# --- END MODIFICATION ---


def save_document_from_dict(
    db: Session, document_data: Dict[str, Any], job_id: int
) -> Tuple[
    models.PurchaseOrder | models.GoodsReceiptNote | models.Invoice | None, str | None
]:
    doc_type = document_data.get("document_type")
    if doc_type == "PurchaseOrder":
        return _save_po_from_dict(db, document_data, job_id)
    elif doc_type == "GoodsReceiptNote":
        return _save_grn_from_dict(db, document_data, job_id)
    elif doc_type == "Invoice":
        return _save_invoice_from_dict(db, document_data, job_id)
    else:
        error_message = f"Unknown document type: {doc_type}"
        db.add(
            models.FailedIngestion(
                job_id=job_id,
                filename=document_data.get("file_path", "unknown"),
                document_type=doc_type,
                raw_data=document_data,
                error_message=error_message,
            )
        )
        return None, error_message


def process_document_from_file(
    db: Session, job_id: int, file_path: str, file_content: bytes
) -> Tuple[
    models.PurchaseOrder | models.GoodsReceiptNote | models.Invoice | None, str | None
]:
    try:
        extraction_prompt = build_extraction_prompt(db)
        extracted_data = extractor.extract_data_from_pdf(
            file_content, extraction_prompt
        )

        if not extracted_data:
            error_message = "Failed to extract data from document."
            db.add(
                models.FailedIngestion(
                    job_id=job_id,
                    filename=file_path,
                    document_type="Unknown",
                    raw_data={},
                    error_message=error_message,
                )
            )
            return None, error_message

        # Add file path to the extracted data
        extracted_data["file_path"] = file_path

        # Validate required fields
        doc_type = extracted_data.get("document_type")
        is_valid, validation_error = validate_required_fields(extracted_data, doc_type)
        if not is_valid:
            db.add(
                models.FailedIngestion(
                    job_id=job_id,
                    filename=file_path,
                    document_type=doc_type,
                    raw_data=extracted_data,
                    error_message=validation_error,
                )
            )
            return None, validation_error

        return save_document_from_dict(db, extracted_data, job_id)

    except Exception as e:
        error_message = f"Unexpected error processing document: {str(e)}"
        db.add(
            models.FailedIngestion(
                job_id=job_id,
                filename=file_path,
                document_type="Unknown",
                raw_data={},
                error_message=error_message,
            )
        )
        return None, error_message

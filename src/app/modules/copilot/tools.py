# src/app/modules/copilot/tools.py
import json
import os
import sys
import logging

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from google.genai import types as genai_types
from thefuzz import fuzz
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

# Set up logging
logger = logging.getLogger(__name__)

from app.db import models, schemas
from app.utils import data_formatting
from app.config import settings
from sample_data.pdf_templates import draw_po_pdf

# --- ADDED: Import API logic and audit logger ---
from app.api.endpoints import (
    invoices,
    configuration,
    learning,
    notifications,
    payments,
    workflow,
    documents,
)
from app.services import dashboard_service, document_service
from app.utils.auditing import log_audit_event

# Use centralized configuration for generated documents
GENERATED_DOCS_DIR = settings.generated_pdf_storage_path

# Ensure directory exists on module import with error handling
try:
    os.makedirs(GENERATED_DOCS_DIR, exist_ok=True)
except OSError as e:
    print(
        f"Warning: Could not create generated documents directory {GENERATED_DOCS_DIR}: {e}"
    )


# --- Helper Function ---
def make_json_serializable(data: Any) -> Any:
    """Converts a Python object into a JSON-serializable version."""
    return json.loads(json.dumps(data, default=str))


# --- Helper to create a system user context for service calls ---
def get_system_user_context(db: Session) -> models.User:
    """Creates a temporary admin user context for service calls."""
    admin_role = db.query(models.Role).filter(models.Role.name == "admin").first()
    if not admin_role:
        raise ValueError("Admin role not found, cannot execute system-level requests.")
    return models.User(id=-1, role=admin_role, email="system@agent")


# ==============================================================================
# SECTION 1: READ-ONLY & ANALYSIS TOOLS
# ==============================================================================

get_system_kpis_declaration = genai_types.FunctionDeclaration(
    name="get_system_kpis",
    description="Gets key performance indicators (KPIs) for the entire AP system, such as touchless rate and discount capture.",
)


def get_system_kpis(db: Session) -> Dict[str, Any]:
    print("Executing tool: get_system_kpis")
    system_user_context = get_system_user_context(db)
    kpis = dashboard_service.get_kpis_logic(db=db, current_user=system_user_context)
    return make_json_serializable(kpis)


# --- START: COLLECTION SEARCH TOOLS ---
find_customers_declaration = genai_types.FunctionDeclaration(
    name="find_customers",
    description="Search for customers and loan accounts based on various criteria like risk level, outstanding amount, customer name, or payment status.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "search_term": genai_types.Schema(
                type=genai_types.Type.STRING,
                description="Customer name, customer number, or loan ID to search for",
            ),
            "risk_level": genai_types.Schema(
                type=genai_types.Type.STRING,
                description="Filter by risk level: 'red', 'amber', or 'yellow'",
            ),
            "min_outstanding": genai_types.Schema(
                type=genai_types.Type.NUMBER,
                description="Minimum outstanding amount to filter by",
            ),
            "days_overdue": genai_types.Schema(
                type=genai_types.Type.NUMBER,
                description="Filter by minimum days overdue",
            ),
        },
    ),
)


def find_customers(
    db: Session, 
    search_term: Optional[str] = None,
    risk_level: Optional[str] = None,
    min_outstanding: Optional[float] = None,
    days_overdue: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Search for customers based on various criteria"""
    print(f"Executing tool: find_customers with criteria: search_term={search_term}, risk_level={risk_level}, min_outstanding={min_outstanding}, days_overdue={days_overdue}")
    
    try:
        # Use the existing collection models
        query = db.query(
            models.Customer.id.label("customer_id"),
            models.Customer.customer_no,
            models.Customer.name.label("customer_name"),
            models.Customer.cbs_risk_level,
            models.Customer.cbs_emi_amount,
            models.Customer.cbs_due_day,
            models.Customer.cbs_outstanding_amount,
            models.Customer.cbs_last_payment_date,
            models.Customer.cibil_score,
            models.Loan.loan_id,
            models.Loan.emi_amount,
            models.Loan.outstanding_amount,
            models.Loan.last_payment_date,
            models.Loan.next_due_date,
            models.ContractNote.id.label("contract_note_id"),
            models.ContractNote.contract_emi_amount,
            models.ContractNote.contract_due_day,
            models.ContractNote.contract_late_fee_percent,
        ).outerjoin(models.Loan, models.Customer.id == models.Loan.customer_id
        ).outerjoin(models.ContractNote, models.Customer.contract_note_id == models.ContractNote.id)
        
        # Apply filters
        if search_term:
            query = query.filter(
                models.Customer.name.ilike(f"%{search_term}%") |
                models.Customer.customer_no.ilike(f"%{search_term}%") |
                models.Loan.loan_id.ilike(f"%{search_term}%")
            )
        
        if risk_level:
            query = query.filter(models.Customer.cbs_risk_level == risk_level.upper())
        
        if min_outstanding:
            query = query.filter(models.Customer.cbs_outstanding_amount >= min_outstanding)
        
        results = query.order_by(models.Customer.customer_no).limit(20).all()
        
        # Format results
        customers = []
        for result in results:
            # Calculate days overdue
            days_overdue_calc = 0
            if result.next_due_date:
                from datetime import date
                today = date.today()
                if result.next_due_date < today:
                    days_overdue_calc = (today - result.next_due_date).days
            
            # Apply days overdue filter if specified
            if days_overdue is not None and days_overdue_calc < days_overdue:
                continue
            
            customer_data = {
                "customer_id": result.customer_id,
                "customer_no": result.customer_no,
                "customer_name": result.customer_name,
                "risk_level": result.cbs_risk_level,
                "cibil_score": int(result.cibil_score) if result.cibil_score else None,
                "outstanding_amount": result.cbs_outstanding_amount or 0,
                "emi_amount": result.cbs_emi_amount or 0,
                "days_overdue": days_overdue_calc,
                "loan_id": result.loan_id,
                "has_contract": result.contract_note_id is not None,
                "contract_emi_amount": result.contract_emi_amount,
                "last_payment_date": result.last_payment_date.isoformat() if result.last_payment_date else None,
                "next_due_date": result.next_due_date.isoformat() if result.next_due_date else None,
            }
            customers.append(customer_data)
        
        return make_json_serializable(customers)
        
    except Exception as e:
        return [{"error": f"An error occurred during customer search: {str(e)}"}]


find_documents_declaration = genai_types.FunctionDeclaration(
    name="find_documents",
    description="Legacy invoice search - kept for backward compatibility. Search for documents/invoices based on various criteria.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "query_json": genai_types.Schema(
                type=genai_types.Type.STRING,
                description="JSON string containing search criteria for documents/invoices",
            ),
        },
        required=["query_json"],
    ),
)


def find_documents(db: Session, query_json: str) -> List[Dict[str, Any]]:
    """Legacy invoice search - kept for backward compatibility"""
    print(f"Executing tool: find_documents with query: {query_json}")
    try:
        query_data = json.loads(query_json)
        search_req = schemas.SearchRequest(**query_data)
        system_user_context = get_system_user_context(db)
        results = document_service.search_invoices_logic(
            db, search_req, system_user_context
        )
        if not results:
            return []
        return make_json_serializable(
            [schemas.InvoiceSummary.from_orm(inv).model_dump() for inv in results]
        )
    except json.JSONDecodeError:
        return [{"error": "Invalid JSON format for the search query."}]
    except Exception as e:
        return [{"error": f"An error occurred during search: {str(e)}"}]


# --- END: COLLECTION SEARCH TOOLS ---


get_invoice_details_declaration = genai_types.FunctionDeclaration(
    name="get_invoice_details",
    description="Retrieves a complete dossier (including related PO and GRN) for a single invoice ID.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={"invoice_id": genai_types.Schema(type=genai_types.Type.STRING)},
    ),
)


def get_invoice_details(db: Session, invoice_id: str) -> Dict[str, Any]:
    print(f"Executing tool: get_invoice_details for invoice_id={invoice_id}")
    invoice = (
        db.query(models.Invoice).filter(models.Invoice.invoice_id == invoice_id).first()
    )
    if not invoice:
        return {"error": f"Invoice with ID '{invoice_id}' not found."}
    dossier = data_formatting.format_full_dossier(invoice, db)
    return make_json_serializable(dossier)


get_payment_forecast_declaration = genai_types.FunctionDeclaration(
    name="get_payment_forecast",
    description="Forecasts cash outflow by showing payments due in upcoming periods (e.g., next 7 days, 8-30 days).",
)


def get_payment_forecast(db: Session) -> Dict[str, Any]:
    print("Executing tool: get_payment_forecast")
    system_user_context = get_system_user_context(db)
    forecast = dashboard_service.get_payment_forecast_logic(
        db=db, current_user=system_user_context
    )
    return make_json_serializable(forecast)


get_learned_heuristics_declaration = genai_types.FunctionDeclaration(
    name="get_learned_heuristics",
    description="Shows patterns the system has learned from user behavior, like consistently approving specific exceptions.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={"vendor_name": genai_types.Schema(type=genai_types.Type.STRING)},
    ),
)


def get_learned_heuristics(
    db: Session, vendor_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    print(f"Executing tool: get_learned_heuristics for vendor={vendor_name}")
    results = learning.get_aggregated_heuristics(vendor_name=vendor_name, db=db)
    if not results:
        return [{"message": "No specific heuristics have been learned yet."}]
    return make_json_serializable(results)


get_notifications_declaration = genai_types.FunctionDeclaration(
    name="get_notifications",
    description="Fetches important, unread notifications, alerts, and suggestions from the proactive engine.",
)


def get_notifications(db: Session) -> List[Dict[str, Any]]:
    print("Executing tool: get_notifications")
    results = notifications.get_notifications(db=db)
    if not results:
        return [{"message": "There are no new notifications."}]
    return make_json_serializable(
        [schemas.Notification.from_orm(r).model_dump(mode="json") for r in results]
    )


# --- START: NEW INSIGHTS TOOL ---
get_process_inefficiencies_declaration = genai_types.FunctionDeclaration(
    name="get_process_inefficiencies",
    description="Identifies systemic process issues, like vendors who frequently require manual PO creation.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "vendor_name": genai_types.Schema(
                type=genai_types.Type.STRING,
                description="Optional: filter inefficiencies for a specific vendor.",
            )
        },
    ),
)


def get_process_inefficiencies(
    db: Session, vendor_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    print(f"Executing tool: get_process_inefficiencies for vendor: {vendor_name}")
    query = db.query(models.UserActionPattern)
    if vendor_name:
        query = query.filter(
            models.UserActionPattern.entity_name.ilike(f"%{vendor_name}%")
        )

    # Find significant patterns (e.g., count > 5 in the last month)
    patterns = (
        query.filter(models.UserActionPattern.count > 5)
        .order_by(models.UserActionPattern.count.desc())
        .limit(5)
        .all()
    )

    if not patterns:
        return [{"message": "No significant process inefficiencies were detected."}]

    return make_json_serializable(
        [
            {
                "pattern_type": p.pattern_type,
                "entity_name": p.entity_name,
                "count": p.count,
                "last_detected": p.last_detected,
            }
            for p in patterns
        ]
    )


# --- END: NEW INSIGHTS TOOL ---

# --- START: NEW LEARNING TOOL ---
remember_user_preference_declaration = genai_types.FunctionDeclaration(
    name="remember_user_preference",
    description="Saves a specific user preference, such as a contact email for a vendor.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "preference_type": genai_types.Schema(
                type=genai_types.Type.STRING,
                description="The type of preference, e.g., 'PREFERRED_VENDOR_CONTACT'",
            ),
            "context_key": genai_types.Schema(
                type=genai_types.Type.STRING,
                description="The entity the preference applies to, e.g., the vendor's name.",
            ),
            "preference_value": genai_types.Schema(
                type=genai_types.Type.STRING,
                description="The value of the preference, e.g., 'contact@vendor.com'.",
            ),
        },
    ),
)


def remember_user_preference(
    db: Session, preference_type: str, context_key: str, preference_value: str
) -> Dict[str, Any]:
    print(f"Executing tool: remember_user_preference for {preference_type}")

    # We need a user context to save the preference against
    # For now, we'll assume a default user or will need to pass it in. Let's use the system user for demo.
    system_user = get_system_user_context(db)

    # In a real multi-user system, you would get the current_user's ID

    # Find existing preference to update it (upsert)
    existing_pref = (
        db.query(models.LearnedPreference)
        .filter_by(
            # user_id=current_user.id,
            preference_type=preference_type,
            context_key=context_key,
        )
        .first()
    )

    if existing_pref:
        existing_pref.preference_value = preference_value
    else:
        new_pref = models.LearnedPreference(
            user_id=system_user.id,  # Replace with actual user ID in a real system
            preference_type=preference_type,
            context_key=context_key,
            preference_value=preference_value,
        )
        db.add(new_pref)

    db.commit()
    return {
        "success": True,
        "message": f"Preference '{preference_type}' for '{context_key}' has been saved.",
    }


# --- END: NEW LEARNING TOOL ---


get_audit_trail_declaration = genai_types.FunctionDeclaration(
    name="get_audit_trail",
    description="Retrieves the full history of all actions taken on a specific invoice.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={"invoice_id": genai_types.Schema(type=genai_types.Type.STRING)},
    ),
)


def get_audit_trail(db: Session, invoice_id: str) -> List[Dict[str, Any]]:
    print(f"Executing tool: get_audit_trail for invoice_id={invoice_id}")
    invoice = db.query(models.Invoice).filter_by(invoice_id=invoice_id).first()
    if not invoice:
        return [{"error": f"Invoice '{invoice_id}' not found."}]
    logs = workflow.get_invoice_audit_log(invoice_db_id=invoice.id, db=db)
    return make_json_serializable(
        [schemas.AuditLog.from_orm(log).model_dump(mode="json") for log in logs]
    )


get_actionable_insights_declaration = genai_types.FunctionDeclaration(
    name="get_actionable_insights",
    description="Retrieves specific, high-confidence learned patterns or proactive notifications about a particular vendor or invoice. Use this to find suggestions for resolving a problem.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "vendor_name": genai_types.Schema(type=genai_types.Type.STRING),
            "invoice_id": genai_types.Schema(type=genai_types.Type.STRING),
        },
    ),
)


def get_actionable_insights(
    db: Session, vendor_name: Optional[str] = None, invoice_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Finds relevant high-confidence heuristics and unread notifications
    to provide proactive advice to the user.
    """
    print(
        f"Executing tool: get_actionable_insights for vendor={vendor_name}, invoice={invoice_id}"
    )
    insights = {"learned_patterns": [], "notifications": []}

    # Find high-confidence heuristics for the vendor
    if vendor_name:
        heuristics = (
            db.query(models.LearnedHeuristic)
            .filter(
                models.LearnedHeuristic.vendor_name.ilike(f"%{vendor_name}%"),
                models.LearnedHeuristic.confidence_score >= 0.8,
            )
            .order_by(models.LearnedHeuristic.confidence_score.desc())
            .limit(3)
            .all()
        )

        insights["learned_patterns"] = [
            schemas.LearnedHeuristic.from_orm(h).model_dump(mode="json")
            for h in heuristics
        ]

    # Find unread notifications for the vendor or invoice
    entity_ids = [eid for eid in [vendor_name, invoice_id] if eid is not None]
    if entity_ids:
        notifications_list = (
            db.query(models.Notification)
            .filter(
                models.Notification.is_read == 0,
                models.Notification.related_entity_id.in_(entity_ids),
            )
            .order_by(models.Notification.created_at.desc())
            .limit(3)
            .all()
        )

        insights["notifications"] = [
            schemas.Notification.from_orm(n).model_dump(mode="json")
            for n in notifications_list
        ]

    return make_json_serializable(insights)


# ==============================================================================
# SECTION 2: ACTION & WORKFLOW TOOLS
# These tools change the state of the system (e.g., update status, edit data).
# ==============================================================================


def _get_invoice_db_id(db: Session, invoice_id_str: str) -> Optional[int]:
    """Helper to safely get the database ID from a string ID."""
    return db.query(models.Invoice.id).filter_by(invoice_id=invoice_id_str).scalar()


def _update_invoice_status_tool(
    db: Session, invoice_ids: List[str], new_status: models.DocumentStatus, reason: str
) -> Dict[str, Any]:
    """Internal helper for all status update tools, now handles batches."""
    db_ids = [
        id
        for id in (_get_invoice_db_id(db, iid) for iid in invoice_ids)
        if id is not None
    ]
    if not db_ids:
        return {"error": "None of the provided invoice IDs were found."}

    # We can reuse the existing batch update endpoint logic for this
    req = schemas.BatchUpdateStatusRequest(
        invoice_ids=db_ids, new_status=new_status.value, reason=reason
    )
    system_user_context = get_system_user_context(db)
    result = invoices.batch_update_invoice_status(
        request=req, db=db, current_user=system_user_context
    )
    return result


# --- START: MODIFIED ACTION TOOLS ---
approve_invoice_declaration = genai_types.FunctionDeclaration(
    name="approve_invoice",
    description="Approves one or more invoices, moving them to the 'matched' state, ready for payment.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "invoice_ids": genai_types.Schema(
                type=genai_types.Type.ARRAY,
                items=genai_types.Schema(type=genai_types.Type.STRING),
            ),
            "reason": genai_types.Schema(type=genai_types.Type.STRING),
        },
    ),
)


def approve_invoice(
    db: Session, invoice_ids: List[str], reason: str = "Approved via AI Bank Collection Manager"
) -> Dict[str, Any]:
    print(f"Executing tool: approve_invoice for {invoice_ids}")
    return _update_invoice_status_tool(
        db, invoice_ids, models.DocumentStatus.matched, reason
    )


reject_invoice_declaration = genai_types.FunctionDeclaration(
    name="reject_invoice",
    description="Rejects one or more invoices, moving them to the 'rejected' state.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "invoice_ids": genai_types.Schema(
                type=genai_types.Type.ARRAY,
                items=genai_types.Schema(type=genai_types.Type.STRING),
            ),
            "reason": genai_types.Schema(type=genai_types.Type.STRING),
        },
    ),
)


def reject_invoice(db: Session, invoice_ids: List[str], reason: str) -> Dict[str, Any]:
    print(f"Executing tool: reject_invoice for {invoice_ids}")
    if not reason or len(reason.strip()) < 5:
        return {"error": "A reason must be provided for rejecting an invoice."}
    return _update_invoice_status_tool(
        db, invoice_ids, models.DocumentStatus.rejected, reason
    )


# --- END: MODIFIED ACTION TOOLS ---


update_vendor_tolerance_declaration = genai_types.FunctionDeclaration(
    name="update_vendor_tolerance",
    description="Sets or updates the price tolerance percentage for a specific vendor.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "vendor_name": genai_types.Schema(type=genai_types.Type.STRING),
            "new_tolerance_percent": genai_types.Schema(type=genai_types.Type.NUMBER),
        },
    ),
)


def update_vendor_tolerance(
    db: Session, vendor_name: str, new_tolerance_percent: float
) -> Dict[str, Any]:
    print(f"Executing tool: update_vendor_tolerance for {vendor_name}")
    setting = (
        db.query(models.VendorSetting)
        .filter(models.VendorSetting.vendor_name.ilike(f"%{vendor_name}%"))
        .first()
    )
    if not setting:
        setting_data = schemas.VendorSettingCreate(
            vendor_name=vendor_name, price_tolerance_percent=new_tolerance_percent
        )
        configuration.create_vendor_setting(setting_data=setting_data, db=db)
    else:
        setting_data = schemas.VendorSettingCreate(
            vendor_name=setting.vendor_name,
            price_tolerance_percent=new_tolerance_percent,
            contact_email=setting.contact_email,
        )
        configuration.update_single_vendor_setting(
            setting_id=setting.id, setting_data=setting_data, db=db
        )

    return {
        "success": True,
        "vendor_name": vendor_name,
        "new_tolerance_percent": new_tolerance_percent,
    }


edit_purchase_order_declaration = genai_types.FunctionDeclaration(
    name="edit_purchase_order",
    description="Edits fields of an existing Purchase Order. Use a JSON object for changes. This triggers a re-match of linked invoices.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "po_number": genai_types.Schema(type=genai_types.Type.STRING),
            "changes_json": genai_types.Schema(
                type=genai_types.Type.STRING,
                description='A JSON string of fields to update, e.g., \'{"line_items": [{"description": "...", "ordered_qty": 110}]}\'',
            ),
        },
    ),
)


def edit_purchase_order(
    db: Session, po_number: str, changes_json: str
) -> Dict[str, Any]:
    print(f"Executing tool: edit_purchase_order for {po_number}")
    po = db.query(models.PurchaseOrder).filter_by(po_number=po_number).first()
    if not po:
        return {"error": f"PO '{po_number}' not found."}

    try:
        changes = json.loads(changes_json)

        # --- START FIX: Make the edit more robust ---
        if "line_items" in changes:
            # Create a map of existing items by description for easy lookup
            existing_items_map = {
                item.get("description"): item for item in (po.line_items or [])
            }

            updated_line_items = []
            for change_item in changes["line_items"]:
                # Find the original item to get all its fields (like SKU)
                original_item = existing_items_map.get(change_item.get("description"))
                if original_item:
                    # Merge the changes into the original item data
                    updated_item = {**original_item, **change_item}
                    # Recalculate line total if necessary
                    if "ordered_qty" in change_item or "unit_price" in change_item:
                        qty = updated_item.get("ordered_qty", 0)
                        price = updated_item.get("unit_price", 0)
                        updated_item["line_total"] = qty * price
                    updated_line_items.append(updated_item)
                else:
                    # If the item is new, add it (less common case for an edit)
                    updated_line_items.append(change_item)

            changes["line_items"] = updated_line_items
        # --- END FIX ---

        # Dummy BackgroundTasks object since we are calling the endpoint function directly
        from fastapi import BackgroundTasks

        background_tasks = BackgroundTasks()
        result = documents.update_purchase_order(
            po_db_id=po.id, changes=changes, background_tasks=background_tasks, db=db
        )
        return result
    except json.JSONDecodeError:
        return {"error": "Invalid JSON format for changes."}
    except Exception as e:
        return {"error": f"Failed to update PO: {str(e)}"}


regenerate_po_pdf_declaration = genai_types.FunctionDeclaration(
    name="regenerate_po_pdf",
    description="Generates a new PDF file for a Purchase Order, typically after it has been edited.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={"po_number": genai_types.Schema(type=genai_types.Type.STRING)},
    ),
)


def regenerate_po_pdf(db: Session, po_number: str) -> Dict[str, Any]:
    print(f"Executing tool: regenerate_po_pdf for {po_number}")
    po = db.query(models.PurchaseOrder).filter_by(po_number=po_number).first()
    if not po:
        return {"error": f"PO '{po_number}' not found."}

    # --- START FIX: Use the complete, most up-to-date PO data ---
    po_data_for_pdf = po.raw_data_payload
    if not po_data_for_pdf:
        return {
            "error": f"No raw data payload found for PO '{po_number}'. Cannot regenerate PDF."
        }

    # Override the payload with the latest data from the PO object
    po_data_for_pdf["line_items"] = po.line_items
    po_data_for_pdf["vendor_name"] = po.vendor_name
    po_data_for_pdf["buyer_name"] = po.buyer_name
    po_data_for_pdf["po_number"] = po.po_number
    po_data_for_pdf["order_date"] = po.order_date

    # Recalculate totals to ensure consistency
    subtotal = sum(item.get("line_total", 0) for item in (po.line_items or []))
    tax = subtotal * 0.088  # Use the same tax rate as the data generator
    po_data_for_pdf["po_subtotal"] = subtotal
    po_data_for_pdf["po_tax"] = tax
    po_data_for_pdf["po_grand_total"] = subtotal + tax
    # --- END FIX ---

    # Ensure all required fields are present with defaults
    from datetime import date as date_type

    # Handle order_date conversion if it's a string
    order_date = po_data_for_pdf.get("order_date", po.order_date)
    if isinstance(order_date, str):
        try:
            from datetime import datetime

            order_date = datetime.strptime(order_date, "%Y-%m-%d").date()
        except ValueError:
            order_date = po.order_date or date_type.today()
    elif order_date is None:
        order_date = po.order_date or date_type.today()

    required_defaults = {
        "buyer_name": po_data_for_pdf.get("buyer_name", "Supervity Bank Collection Center"),
        "buyer_address": po_data_for_pdf.get(
            "buyer_address", "123 Business Ave\nSuite 100\nBusiness City, BC 12345"
        ),
        "vendor_name": po_data_for_pdf.get(
            "vendor_name", po.vendor_name or "Unknown Vendor"
        ),
        "vendor_address": po_data_for_pdf.get(
            "vendor_address", "Vendor Address\nNot Available"
        ),
        "po_number": po_data_for_pdf.get("po_number", po.po_number),
        "order_date": order_date,
    }

    # Update po_data_for_pdf with required fields
    po_data_for_pdf.update(required_defaults)

    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    filename = f"REGEN_{po_number}_{timestamp}.pdf"
    filepath = os.path.join(GENERATED_DOCS_DIR, filename)

    try:
        draw_po_pdf(po_data_for_pdf, filepath)  # Use the corrected data payload
    except Exception as e:
        return {"error": f"Failed to generate PDF: {str(e)}"}

    log_audit_event(
        db=db,
        user="AI Bank Collection Manager",
        action="PO PDF Regenerated",
        entity_type="PurchaseOrder",
        entity_id=po_number,
        summary=f"Generated new PDF: {filepath}",
        details={"path": filepath},
    )
    db.commit()
    return {"success": True, "po_number": po_number, "generated_file_path": filepath}


draft_vendor_communication_declaration = genai_types.FunctionDeclaration(
    name="draft_vendor_communication",
    description="Drafts a professional email to a vendor about a specific invoice issue.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "invoice_id": genai_types.Schema(type=genai_types.Type.STRING),
            "reason": genai_types.Schema(
                type=genai_types.Type.STRING,
                description="The core issue to address, e.g., 'price mismatch for safety gloves', 'quantity short-shipped for cutting discs'",
            ),
        },
    ),
)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(
        (httpx.ConnectError, httpx.TimeoutException, ConnectionError)
    ),
)
def generate_vendor_communication_with_retry(client, model, contents, config):
    """Generate vendor communication with retry logic"""
    try:
        response_text = ""
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=config,
        ):
            if chunk.text:
                response_text += chunk.text
        return response_text
    except (httpx.ConnectError, httpx.TimeoutException, ConnectionError) as e:
        logger.warning(f"Streaming failed with {type(e).__name__}: {e}. Retrying...")
        raise  # This will trigger the retry mechanism


def draft_vendor_communication(
    db: Session, client: Any, invoice_id: str, reason: str
) -> Dict[str, Any]:
    print(f"Executing tool: draft_vendor_communication for {invoice_id}")
    invoice = db.query(models.Invoice).filter_by(invoice_id=invoice_id).first()
    if not invoice:
        return {"error": f"Invoice '{invoice_id}' not found."}

    dossier = get_invoice_details(db, invoice_id)
    if dossier.get("error"):
        return dossier

    vendor_name = dossier.get("summary", {}).get("vendor_name")

    # --- START: USE LEARNED PREFERENCE ---
    # 1. Check for a learned preference for the contact email
    learned_email_pref = (
        db.query(models.LearnedPreference)
        .filter_by(preference_type="PREFERRED_VENDOR_CONTACT", context_key=vendor_name)
        .first()
    )

    # 2. Fallback to vendor settings
    vendor_setting = (
        db.query(models.VendorSetting).filter_by(vendor_name=vendor_name).first()
    )

    # 3. Determine final email address
    if learned_email_pref:
        vendor_email = learned_email_pref.preference_value
    elif vendor_setting and vendor_setting.contact_email:
        vendor_email = vendor_setting.contact_email
    else:
        vendor_email = "vendor_contact@example.com"  # Final fallback
    # --- END: USE LEARNED PREFERENCE ---

    # --- START: NEW CONTEXT GATHERING ---
    # Summarize all failed steps from the match trace
    failed_steps_summary = []
    if invoice.match_trace:
        for step in invoice.match_trace:
            if step.get("status") == "FAIL":
                failed_steps_summary.append(
                    f"- {step.get('step')}: {step.get('message')}"
                )

    # Get the last 3 audit log entries for context on recent actions
    recent_actions_summary = []
    recent_logs = (
        db.query(models.AuditLog)
        .filter_by(invoice_db_id=invoice.id)
        .order_by(models.AuditLog.timestamp.desc())
        .limit(3)
        .all()
    )
    for log in recent_logs:
        recent_actions_summary.append(
            f"- {log.timestamp.strftime('%Y-%m-%d %H:%M')}: {log.action} by {log.user}. Summary: {log.summary or 'N/A'}"
        )

    context_block = (
        f"**Invoice Details:**\n"
        f"- Invoice ID: {invoice.invoice_id}\n"
        f"- Invoice Date: {invoice.invoice_date}\n"
        f"- Total Amount: {invoice.grand_total}\n\n"
        f"**Detected Issues (from automated system):**\n"
        f"{chr(10).join(failed_steps_summary) if failed_steps_summary else 'No specific system-detected failures found.'}\n\n"
        f"**Recent Actions Taken:**\n"
        f"{chr(10).join(recent_actions_summary) if recent_actions_summary else 'No recent actions logged.'}\n"
    )
    # --- END: NEW CONTEXT GATHERING ---

    # --- MODIFIED PROMPT ---
    prompt = f"""You are a professional Accounts Payable specialist. Draft a clear, polite email to a vendor about an invoice issue.

**Recipient Email:** {vendor_email}
**Subject:** Query regarding Invoice {invoice_id}

**User's Goal for this Email:**
"{reason}"

**Full Context & Evidence:**
{context_block}

**Instructions:**
1.  Start with a polite and professional opening.
2.  Clearly state the primary issue based on the user's goal.
3.  Use the specific details from the 'Detected Issues' and 'Recent Actions' sections to provide concrete evidence and context for the problem. Do not simply repeat the text; explain it naturally.
4.  Conclude with a clear and polite call to action (e.g., "Please provide a corrected invoice," or "Please issue a credit note for the discrepancy.").
5.  Maintain a professional and collaborative tone throughout.

Draft the email body now.
"""
    try:
        from google.genai import types

        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=prompt),
                ],
            ),
        ]
        generate_content_config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                thinking_budget=0,
            ),
            safety_settings=[
                types.SafetySetting(
                    category="HARM_CATEGORY_HARASSMENT",
                    threshold="BLOCK_NONE",  # Block none
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_HATE_SPEECH",
                    threshold="BLOCK_NONE",  # Block none
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    threshold="BLOCK_NONE",  # Block none
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_DANGEROUS_CONTENT",
                    threshold="BLOCK_NONE",  # Block none
                ),
            ],
            response_mime_type="text/plain",
        )

        try:
            response_text = generate_vendor_communication_with_retry(
                client=client,
                model=settings.gemini_model_name,
                contents=contents,
                config=generate_content_config,
            )
            return {"draft_email": response_text}
        except Exception as e:
            logger.error(f"Vendor communication generation failed after retries: {e}")
            return {
                "error": f"Failed to generate communication after multiple attempts: {str(e)}"
            }
    except Exception as e:
        return {"error": f"Error generating email draft: {str(e)}"}


create_automation_rule_declaration = genai_types.FunctionDeclaration(
    name="create_automation_rule",
    description="Creates intelligent automation rules for loan risk assessment and collection management. Use this when users want to create rules based on loan policies, risk patterns, or collection strategies. You should intelligently interpret user requests and create appropriate rules.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "rule_name": genai_types.Schema(
                type=genai_types.Type.STRING,
                description="A descriptive name for the rule based on user's request"
            ),
            "description": genai_types.Schema(
                type=genai_types.Type.STRING,
                description="A detailed description explaining what the rule does and why it's important"
            ),
            "risk_level": genai_types.Schema(
                type=genai_types.Type.STRING,
                description="The risk level this rule should assign: red (high risk), amber (medium risk), or yellow (low risk)"
            ),
            "field": genai_types.Schema(
                type=genai_types.Type.STRING,
                description="The database field to check: missed_emis, days_overdue, pending_amount, cbs_outstanding_amount, cbs_risk_level"
            ),
            "operator": genai_types.Schema(
                type=genai_types.Type.STRING,
                description="The comparison operator: >=, >, <=, <, =, !="
            ),
            "value": genai_types.Schema(
                type=genai_types.Type.NUMBER,
                description="The threshold value for the condition"
            ),
            "priority": genai_types.Schema(
                type=genai_types.Type.INTEGER,
                description="Rule priority from 1 (highest) to 10 (lowest)"
            ),
        },
        required=["rule_name", "description", "risk_level", "field", "operator", "value"]
    ),
)


def create_automation_rule(
    db: Session,
    rule_name: str,
    description: str,
    risk_level: str,
    field: str,
    operator: str,
    value: float,
    priority: int = 5,
) -> Dict[str, Any]:
    print(f"Executing tool: create_automation_rule - {rule_name}")
    try:
        # Validate risk level
        valid_risk_levels = ["red", "amber", "yellow"]
        if risk_level.lower() not in valid_risk_levels:
            return {"error": f"Invalid risk level '{risk_level}'. Must be one of: {', '.join(valid_risk_levels)}"}
        
        # Validate field
        valid_fields = ["missed_emis", "days_overdue", "pending_amount", "cbs_outstanding_amount", "cbs_risk_level"]
        if field not in valid_fields:
            return {"error": f"Invalid field '{field}'. Must be one of: {', '.join(valid_fields)}"}
        
        # Validate operator
        valid_operators = [">=", ">", "<=", "<", "=", "!="]
        if operator not in valid_operators:
            return {"error": f"Invalid operator '{operator}'. Must be one of: {', '.join(valid_operators)}"}
        
        # Create conditions in the expected format
        conditions = {
            "logical_operator": "AND",
            "conditions": [
                {
                    "field": field,
                    "operator": operator,
                    "value": value
                }
            ]
        }
        
        # Create the action based on risk level
        action = f"set_risk_level_{risk_level.lower()}"
        
        # Create the rule
        rule_data = schemas.AutomationRuleCreate(
            rule_name=rule_name,
            description=description,
            vendor_name=None,  # Not used for loan risk rules
            conditions=conditions,
            action=action,
            source="ai_agent",
            is_active=True
        )
        
        # Create the rule directly in the database (bypassing endpoint dependencies)
        new_rule = models.AutomationRule(
            rule_name=rule_data.rule_name,
            description=rule_data.description,
            vendor_name=rule_data.vendor_name,
            conditions=rule_data.conditions,
            action=rule_data.action,
            source=rule_data.source,
            is_active=1  # Use integer 1 instead of boolean True
        )
        db.add(new_rule)
        db.commit()
        db.refresh(new_rule)
        
        return {
            "success": True,
            "message": f"✅ Automation rule '{rule_name}' created successfully! This rule will flag customers as {risk_level.upper()} risk when {field} {operator} {value}.",
            "rule_id": new_rule.id,
            "rule_details": {
                "name": rule_name,
                "description": description,
                "risk_level": risk_level,
                "condition": f"{field} {operator} {value}",
                "priority": priority
            }
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating automation rule: {e}")
        return {"error": f"Failed to create rule: {str(e)}"}


# --- Master Tool Dictionary ---
# Collection-focused tools with legacy AP tools for backward compatibility
AVAILABLE_TOOLS = {
    # Collection Analysis
    "find_customers": find_customers,
    "get_system_kpis": get_system_kpis,
    "get_notifications": get_notifications,
    "get_audit_trail": get_audit_trail,
    "get_actionable_insights": get_actionable_insights,
    "get_process_inefficiencies": get_process_inefficiencies,
    # Legacy AP Tools (kept for backward compatibility)
    "find_documents": find_documents,
    "get_invoice_details": get_invoice_details,
    "get_payment_forecast": get_payment_forecast,
    "get_learned_heuristics": get_learned_heuristics,
    "approve_invoice": approve_invoice,
    "reject_invoice": reject_invoice,
    "update_vendor_tolerance": update_vendor_tolerance,
    "edit_purchase_order": edit_purchase_order,
    "regenerate_po_pdf": regenerate_po_pdf,
    "draft_vendor_communication": draft_vendor_communication,
    "create_automation_rule": create_automation_rule,
    "remember_user_preference": remember_user_preference,
}

# --- Tool Declarations for Gemini ---
# Collection-focused tools with legacy AP tools for backward compatibility
ALL_TOOL_DECLARATIONS = [
    # Collection Tools
    find_customers_declaration,
    get_system_kpis_declaration,
    get_notifications_declaration,
    get_audit_trail_declaration,
    get_actionable_insights_declaration,
    get_process_inefficiencies_declaration,
    remember_user_preference_declaration,
    # Legacy AP Tools (kept for backward compatibility)
    find_documents_declaration,
    get_invoice_details_declaration,
    get_payment_forecast_declaration,
    get_learned_heuristics_declaration,
    approve_invoice_declaration,
    reject_invoice_declaration,
    update_vendor_tolerance_declaration,
    edit_purchase_order_declaration,
    regenerate_po_pdf_declaration,
    draft_vendor_communication_declaration,
    create_automation_rule_declaration,
]

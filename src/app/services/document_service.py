# src/app/services/document_service.py
from sqlalchemy.orm import Session, Query, joinedload
from sqlalchemy import or_, func, text
from typing import List, Optional
from datetime import datetime

from ..db import models
from ..db.schemas import SearchRequest
from .permission_service import apply_invoice_permissions
from ..utils.auditing import log_audit_event
from ..utils.logging import get_logger
from ..modules.matching import engine as matching_engine
from ..db.session import engine

logger = get_logger(__name__)


def search_invoices_logic(
    db: Session, request: SearchRequest, current_user: models.User
) -> List[models.Invoice]:
    """
    Core logic for searching invoices with RBAC.
    This function is reused by both search endpoint and AI tools.
    """
    query: Query = db.query(models.Invoice).options(
        joinedload(models.Invoice.purchase_orders), joinedload(models.Invoice.grns)
    )

    # --- APPLY RBAC FILTER ---
    query = apply_invoice_permissions(query, current_user, db)
    # --- END RBAC FILTER ---

    # --- APPLY SEARCH TERM FILTER ---
    if request.search_term:
        search_term_like = f"%{request.search_term.lower()}%"

        # Standard field search
        search_filter = or_(
            models.Invoice.invoice_id.ilike(search_term_like),
            models.Invoice.vendor_name.ilike(search_term_like),
        )

        # Database-specific JSON search
        dialect = engine.dialect.name
        if dialect == "postgresql":
            # Efficiently search in all values of the invoice_metadata JSONB object
            json_search_filter = text(
                "exists (select 1 from jsonb_each_text(invoice_metadata) as t(key, value) where lower(t.value) like :term)"
            )
            search_filter = or_(search_filter, json_search_filter)
            query = query.filter(search_filter).params(term=search_term_like)
        else:  # SQLite fallback (less efficient)
            # Add metadata search to the existing filter
            search_filter = or_(
                search_filter,
                models.Invoice.invoice_metadata.ilike(
                    search_term_like
                ),  # Search raw JSON string
            )
            query = query.filter(search_filter)
    # --- END SEARCH TERM FILTER ---

    # --- APPLY SPECIFIC FILTERS ---
    for condition in request.filters:
        column = getattr(models.Invoice, condition.field, None)
        if column is None:
            continue

        if condition.operator == "is" or condition.operator == "equals":
            query = query.filter(column == condition.value)
        elif condition.operator == "contains":
            query = query.filter(column.ilike(f"%{condition.value}%"))
        elif condition.operator == "gt":
            query = query.filter(column > condition.value)
        elif condition.operator == "lt":
            query = query.filter(column < condition.value)
        elif condition.operator == "gte":
            query = query.filter(column >= condition.value)
        elif condition.operator == "lte":
            query = query.filter(column <= condition.value)
        elif condition.operator == "not_equals":
            query = query.filter(column != condition.value)
        elif condition.operator == "in":
            if isinstance(condition.value, list):
                query = query.filter(column.in_(condition.value))
        elif condition.operator == "not_in":
            if isinstance(condition.value, list):
                query = query.filter(~column.in_(condition.value))
        elif condition.operator == "is_null":
            query = query.filter(column.is_(None))
        elif condition.operator == "is_not_null":
            query = query.filter(column.isnot(None))

    # --- APPLY SORTING ---
    sort_column = getattr(models.Invoice, request.sort_by, models.Invoice.invoice_date)
    if request.sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    # --- GET RESULTS AND ANNOTATE WITH SLA STATUS ---
    invoices = query.all()

    if not invoices:
        return []

    # Find all active SLA breach notifications for the fetched invoices
    invoice_ids = [inv.invoice_id for inv in invoices]
    breached_notifications = (
        db.query(models.Notification.related_entity_id)
        .filter(
            models.Notification.type == "SlaBreach",
            models.Notification.is_read == 0,
            models.Notification.related_entity_id.in_(invoice_ids),
        )
        .all()
    )
    breached_invoice_ids = {nid for (nid,) in breached_notifications}

    # Annotate the invoice objects before returning
    for inv in invoices:
        if inv.invoice_id in breached_invoice_ids:
            inv.sla_status = "breached"
        else:
            inv.sla_status = None

    return invoices


# --- START: NEW FEATURE LOGIC ---
def create_po_from_invoice_logic(
    db: Session, invoice_db_id: int, current_user: models.User, background_tasks
) -> models.PurchaseOrder:
    """
    Creates a new Purchase Order based on the data from an existing non-PO invoice.
    """
    invoice = (
        db.query(models.Invoice).filter(models.Invoice.id == invoice_db_id).first()
    )
    if not invoice:
        raise ValueError("Invoice not found")

    # Generate a unique, recognizable PO number
    new_po_number = f"C-INV-{invoice.invoice_id}"

    # Check if a PO with this number already exists to prevent duplicates
    existing_po = (
        db.query(models.PurchaseOrder)
        .filter(models.PurchaseOrder.po_number == new_po_number)
        .first()
    )
    if existing_po:
        raise ValueError(
            f"A Purchase Order ({new_po_number}) for this invoice already exists."
        )

    # Map invoice data to PO data
    new_po = models.PurchaseOrder(
        po_number=new_po_number,
        vendor_name=invoice.vendor_name,
        buyer_name=invoice.buyer_name,
        order_date=invoice.invoice_date,  # Use invoice date as order date
        subtotal=invoice.subtotal,
        tax=invoice.tax,
        grand_total=invoice.grand_total,
        line_items=[
            {
                "description": item.get("description"),
                "ordered_qty": item.get("quantity"),
                "unit_price": item.get("unit_price"),
                "line_total": item.get("line_total"),
                "unit": item.get("unit"),
                "sku": item.get("sku"),
                # Copy normalized data if it exists
                "normalized_qty": item.get("normalized_qty"),
                "normalized_unit": item.get("normalized_unit"),
                "normalized_unit_price": item.get("normalized_unit_price"),
            }
            for item in (invoice.line_items or [])
        ],
        # raw_data_payload can be omitted as this PO wasn't from a document
    )
    db.add(new_po)

    # Link the new PO back to the invoice
    invoice.related_po_numbers = (invoice.related_po_numbers or []) + [new_po_number]

    # Log the creation event
    log_audit_event(
        db=db,
        invoice_db_id=invoice.id,
        user=current_user.email,
        action="PO Created from Invoice",
        entity_type="Invoice",
        entity_id=invoice.invoice_id,
        summary=f"New PO '{new_po_number}' was created from this non-PO invoice.",
    )

    # Change invoice status to 'matching' to prepare for re-match
    invoice.status = models.DocumentStatus.matching

    db.commit()  # Commit all changes

    # Trigger the re-match in the background
    logger.info(
        f"Queueing invoice ID {invoice.id} for re-matching against new PO {new_po_number}."
    )
    background_tasks.add_task(matching_engine.run_match_for_invoice, db, invoice.id)

    db.refresh(new_po)
    return new_po


# --- END: NEW FEATURE LOGIC ---

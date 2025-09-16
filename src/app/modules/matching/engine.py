# src/app/modules/matching/engine.py

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Dict, Any, Tuple, Optional
from thefuzz import process as fuzzy_process
import math

from app.db import models
from app.config import PRICE_TOLERANCE_PERCENT, QUANTITY_TOLERANCE_PERCENT
from app.utils.auditing import log_audit_event
from app.utils.logging import get_logger

logger = get_logger(__name__)


def add_trace(
    trace_list: List, step: str, status: str, message: str, details: Dict = None
):
    """Helper function to add a step to the match trace."""
    trace_list.append(
        {"step": step, "status": status, "message": message, "details": details or {}}
    )


def _find_best_po_item_match(
    invoice_item: Dict[str, Any], po_items_map: Dict[str, Dict[str, Any]]
) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Finds the best PO line item match using a hierarchical cascade.
    Returns the matched PO item and the method used for matching.

    Cascade Order:
    1. Exact SKU/Part Number Match
    2. High-Confidence Fuzzy Description Match (score > 85)
    3. Lower-Confidence Fuzzy Description Match (score > 60)
    """
    inv_sku = invoice_item.get("sku")
    inv_desc = invoice_item.get("description", "")

    # Stage 1: Exact SKU Match (Highest Priority)
    if inv_sku:
        for po_item in po_items_map.values():
            if po_item.get("sku") == inv_sku:
                return po_item, "Exact SKU Match"

    # Stage 2: High-Confidence Fuzzy Description Match
    if inv_desc:
        high_conf_match = fuzzy_process.extractOne(
            inv_desc, po_items_map.keys(), score_cutoff=85
        )
        if high_conf_match:
            return (
                po_items_map[high_conf_match[0]],
                f"Fuzzy Match (Score: {high_conf_match[1]})",
            )

    # Stage 3: Lower-Confidence Fuzzy Description Match
    if inv_desc:
        low_conf_match = fuzzy_process.extractOne(
            inv_desc, po_items_map.keys(), score_cutoff=60
        )
        if low_conf_match:
            return (
                po_items_map[low_conf_match[0]],
                f"Fuzzy Match (Score: {low_conf_match[1]})",
            )

    return None, "No Match Found"


def _finalize_invoice_status(invoice: models.Invoice, trace: List, db: Session):
    """Sets the final status of the invoice based on the trace and commits to DB."""
    review_category = None
    if any(t["status"] == "FAIL" for t in trace):
        # Determine the most severe category of failure
        for step in trace:
            if step.get("status") == "FAIL":
                if "Document" in step.get("step", "") or "GRN Validation" in step.get(
                    "step", ""
                ):
                    review_category = "missing_document"
                    break  # This is a high-priority failure
                if "Duplicate" in step.get("step", "") or "Timing" in step.get(
                    "step", ""
                ):
                    review_category = "policy_violation"
                    break
        # Default to data_mismatch if no other category fits
        if not review_category:
            review_category = "data_mismatch"

    invoice.review_category = review_category
    invoice.match_trace = trace

    if review_category:
        invoice.status = models.DocumentStatus.needs_review
        add_trace(
            trace,
            "Final Result",
            "FAIL",
            f"Invoice requires manual review. Category: {review_category}",
        )
    else:
        invoice.status = models.DocumentStatus.matched
        add_trace(
            trace,
            "Final Result",
            "PASS",
            "All checks passed. Invoice is matched and ready for payment.",
        )

    log_audit_event(
        db=db,
        invoice_db_id=invoice.id,
        user="Matching Engine",
        action=f"Match "
        + ("Succeeded" if not review_category else f"Failed ({review_category})"),
        entity_type="Invoice",
        entity_id=invoice.invoice_id,
        summary="Automated matching process completed.",
    )
    db.commit()
    logger.info(
        f"--- Matching Engine finished for Invoice: {invoice.invoice_id} with status {invoice.status.value} ---"
    )


def run_match_for_invoice(db: Session, invoice_db_id: int):
    invoice = (
        db.query(models.Invoice).filter(models.Invoice.id == invoice_db_id).first()
    )
    if not invoice:
        logger.error(
            f"[ERROR] Matching engine called for non-existent invoice DB ID: {invoice_db_id}"
        )
        return

    logger.info(
        f"\n--- Running Resilient Matching Engine for Invoice: {invoice.invoice_id} (DB ID: {invoice.id}) ---"
    )
    invoice.status = models.DocumentStatus.matching
    db.commit()

    trace: List[Dict[str, Any]] = []
    add_trace(
        trace,
        "Initialisation",
        "INFO",
        f"Starting validation for Invoice {invoice.invoice_id}.",
    )

    invoice.purchase_orders.clear()
    invoice.grns.clear()
    db.flush()
    related_pos, related_grns = [], []

    if invoice.related_po_numbers:
        related_pos = (
            db.query(models.PurchaseOrder)
            .filter(
                func.trim(models.PurchaseOrder.po_number).in_(
                    invoice.related_po_numbers
                )
            )
            .all()
        )
        for po in related_pos:
            invoice.purchase_orders.append(po)

        po_numbers_from_found_pos = [po.po_number for po in related_pos]
        if po_numbers_from_found_pos:
            related_grns = (
                db.query(models.GoodsReceiptNote)
                .filter(
                    func.trim(models.GoodsReceiptNote.po_number).in_(
                        po_numbers_from_found_pos
                    )
                )
                .all()
            )
            for grn in related_grns:
                invoice.grns.append(grn)

    db.flush()

    is_po_based = bool(invoice.related_po_numbers)
    if not is_po_based:
        add_trace(
            trace,
            "Document Validation",
            "FAIL",
            "This is a Non-PO Invoice and requires manual review and GL code assignment.",
        )
        _finalize_invoice_status(invoice, trace, db)
        return
    elif not related_pos:
        add_trace(
            trace,
            "Document Validation",
            "FAIL",
            "Invoice references PO(s) that could not be found in the system.",
            {"searched_for_pos": invoice.related_po_numbers},
        )
        _finalize_invoice_status(invoice, trace, db)
        return
    else:
        add_trace(
            trace,
            "Document Discovery",
            "PASS",
            f"Found {len(related_pos)} PO(s) and {len(related_grns)} GRN(s) to match against.",
            {
                "found_pos": [p.po_number for p in related_pos],
                "found_grns": [g.grn_number for g in related_grns],
            },
        )

    vendor_setting = (
        db.query(models.VendorSetting)
        .filter_by(vendor_name=invoice.vendor_name)
        .first()
    )
    price_tolerance = (
        vendor_setting.price_tolerance_percent
        if vendor_setting and vendor_setting.price_tolerance_percent is not None
        else PRICE_TOLERANCE_PERCENT
    )
    quantity_tolerance = QUANTITY_TOLERANCE_PERCENT
    add_trace(
        trace,
        "Configuration",
        "INFO",
        f"Using price tolerance of {price_tolerance}% and quantity tolerance of {quantity_tolerance}% for '{invoice.vendor_name}'.",
    )

    potential_duplicates = (
        db.query(models.Invoice)
        .filter(
            models.Invoice.id != invoice.id,
            models.Invoice.invoice_id == invoice.invoice_id,
            models.Invoice.vendor_name == invoice.vendor_name,
            models.Invoice.status.in_(
                [
                    models.DocumentStatus.matched,
                    models.DocumentStatus.paid,
                    models.DocumentStatus.pending_payment,
                ]
            ),
        )
        .all()
    )
    if potential_duplicates:
        add_trace(
            trace,
            "Duplicate Check",
            "FAIL",
            f"Potential duplicate of already processed invoices: {[d.invoice_id for d in potential_duplicates]}",
        )

    if is_po_based and invoice.line_items:
        po_items_map = {
            item.get("description", ""): {**item, "po_number": po.po_number}
            for po in related_pos
            for item in (po.line_items or [])
            if isinstance(item, dict) and item.get("description")
        }

        aggregated_received_items: Dict[str, Dict] = {}
        for grn in related_grns:
            for item in grn.line_items or []:
                if not (
                    isinstance(item, dict)
                    and (item.get("sku") or item.get("description"))
                ):
                    continue
                key = item.get("sku") or item.get("description")
                if key in aggregated_received_items:
                    aggregated_received_items[key]["normalized_qty"] += item.get(
                        "normalized_qty", 0
                    )
                else:
                    aggregated_received_items[key] = item.copy()

        for inv_item in invoice.line_items:
            if not isinstance(inv_item, dict):
                continue

            inv_desc = inv_item.get("description", "")
            step_prefix = f"Item '{inv_desc}'"

            po_item, match_method = _find_best_po_item_match(inv_item, po_items_map)
            if not po_item:
                add_trace(
                    trace,
                    f"{step_prefix} - PO Item Match",
                    "FAIL",
                    "Item not found on any linked POs.",
                )
                continue

            add_trace(
                trace,
                f"{step_prefix} - PO Item Match",
                "PASS",
                f"Matched to PO item via {match_method}.",
            )

            inv_norm_qty = inv_item.get("normalized_qty")
            inv_norm_price = inv_item.get("normalized_unit_price")
            po_norm_price = po_item.get("normalized_unit_price")

            # --- START: CRITICAL LOGIC FIX for GRN Lookup ---
            # Use the matched PO item's identifiers for the GRN lookup key.
            aggregation_key = po_item.get("sku") or po_item.get("description")
            received_item_summary = aggregated_received_items.get(aggregation_key)
            # --- END: CRITICAL LOGIC FIX ---

            if received_item_summary and inv_norm_qty is not None:
                received_qty = received_item_summary.get("normalized_qty", 0)
                qty_diff = abs(inv_norm_qty - received_qty)
                qty_tolerance_amount = (
                    (quantity_tolerance / 100) * received_qty if received_qty > 0 else 0
                )

                if qty_diff > qty_tolerance_amount + 1e-9:
                    add_trace(
                        trace,
                        f"{step_prefix} - Quantity Match",
                        "FAIL",
                        f"Invoice quantity ({inv_norm_qty:.2f}) is outside tolerance of total received quantity ({received_qty:.2f}).",
                        {
                            "invoice_qty": inv_norm_qty,
                            "grn_total_qty": received_qty,
                            "item_description": inv_desc,
                        },
                    )
                else:
                    add_trace(
                        trace,
                        f"{step_prefix} - Quantity Match",
                        "PASS",
                        "Invoice quantity matches total received on GRNs.",
                    )
            elif inv_norm_qty is not None:
                add_trace(
                    trace,
                    f"{step_prefix} - Quantity Match",
                    "FAIL",
                    "Item was not found on any of the linked Goods Receipt Notes.",
                    {
                        "invoice_qty": inv_norm_qty,
                        "grn_total_qty": 0,
                        "item_description": inv_desc,
                    },
                )

            # Compare normalized prices directly. This assumes ingestion correctly calculates them.
            if inv_norm_price is not None and po_norm_price is not None:
                if po_norm_price > 0:
                    price_diff = abs(inv_norm_price - po_norm_price)
                    price_tolerance_amount = (price_tolerance / 100) * po_norm_price
                    if price_diff > price_tolerance_amount + 1e-9:
                        add_trace(
                            trace,
                            f"{step_prefix} - Price Match",
                            "FAIL",
                            f"Normalized invoice price (~${inv_norm_price:.2f}) is outside tolerance of PO price (~${po_norm_price:.2f}).",
                            {
                                "inv_price": inv_norm_price,
                                "po_price": po_norm_price,
                                "tolerance_percent": price_tolerance,
                                "item_description": inv_desc,
                            },
                        )
                    else:
                        add_trace(
                            trace,
                            f"{step_prefix} - Price Match",
                            "PASS",
                            "Normalized price is within tolerance.",
                        )
            else:
                add_trace(
                    trace,
                    f"{step_prefix} - Price Match",
                    "INFO",
                    "Price information was not available for a full comparison.",
                    {"inv_price": inv_norm_price, "po_price": po_norm_price},
                )

    _finalize_invoice_status(invoice, trace, db)

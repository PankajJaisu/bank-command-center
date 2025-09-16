# src/app/modules/matching/comparison.py
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Dict, Any, Tuple, Optional
from thefuzz import process as fuzzy_process
import math

from app.db import models
from app.db import schemas


# --- START MODIFICATION: Replicate the engine's hierarchical matching logic ---
def _find_best_match_for_ui(
    invoice_item: Dict[str, Any], po_items_map: Dict[str, Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Finds the best PO line item match using the same hierarchical cascade as the engine.
    This ensures the UI sees the same data as the matching process.
    """
    inv_sku = invoice_item.get("sku")
    inv_desc = invoice_item.get("description", "")

    # Stage 1: Exact SKU Match
    if inv_sku:
        for po_item in po_items_map.values():
            if po_item.get("sku") == inv_sku:
                return po_item

    # Stage 2: High-Confidence Fuzzy Match
    if inv_desc:
        high_conf_match = fuzzy_process.extractOne(
            inv_desc, po_items_map.keys(), score_cutoff=85
        )
        if high_conf_match:
            return po_items_map[high_conf_match[0]]

    # Stage 3: Lower-Confidence Fuzzy Match
    if inv_desc:
        low_conf_match = fuzzy_process.extractOne(
            inv_desc, po_items_map.keys(), score_cutoff=60
        )
        if low_conf_match:
            return po_items_map[low_conf_match[0]]

    return None


# --- END MODIFICATION ---


def prepare_comparison_data(db: Session, invoice_db_id: int) -> Dict[str, Any]:
    """
    Prepares a detailed, line-by-line comparison between an invoice,
    and all its related POs and GRNs, and includes proactive suggestions.
    """
    invoice = (
        db.query(models.Invoice)
        .options(
            joinedload(models.Invoice.purchase_orders),
            joinedload(models.Invoice.grns).joinedload(models.GoodsReceiptNote.po),
        )
        .filter(models.Invoice.id == invoice_db_id)
        .first()
    )

    if not invoice:
        return {"error": "Invoice not found"}

    # --- START MODIFICATION: Use a more robust PO item map ---
    po_items_map: Dict[str, Dict] = {}
    for po in invoice.purchase_orders:
        for item in po.line_items or []:
            if not isinstance(item, dict):
                continue
            description = item.get("description", "")
            if not description:
                continue
            # Use description as the key for fuzzy matching
            po_items_map[description] = {
                **item,
                "po_number": po.po_number,
                "po_db_id": po.id,
            }
    # --- END MODIFICATION ---

    grn_items_map: Dict[str, Dict] = {}
    for grn in invoice.grns:
        for item in grn.line_items or []:
            if not isinstance(item, dict):
                continue
            description = item.get("description", "")
            if not description:
                continue
            key = f"{description}##{grn.grn_number}"
            grn_items_map[key] = {**item, "grn_number": grn.grn_number}

    comparison_lines = []
    for inv_item in invoice.line_items or []:
        if not isinstance(inv_item, dict):
            continue

        # --- START MODIFICATION: Use the new hierarchical matching for UI data ---
        po_item_match = _find_best_match_for_ui(inv_item, po_items_map)

        # For GRN, we still need to find a related item. Let's use the PO item's description if available.
        lookup_desc_for_grn = (
            po_item_match.get("description")
            if po_item_match
            else inv_item.get("description", "")
        )
        grn_match_result = (
            fuzzy_process.extractOne(
                lookup_desc_for_grn, grn_items_map.keys(), score_cutoff=85
            )
            if lookup_desc_for_grn
            else None
        )
        grn_key_match = grn_match_result[0] if grn_match_result else None
        grn_item_match = grn_items_map.get(grn_key_match) if grn_key_match else None
        # --- END MODIFICATION ---

        comparison_lines.append(
            {
                "invoice_line": inv_item,
                "po_line": po_item_match,  # This will now be correctly populated
                "grn_line": grn_item_match,
                "po_number": (
                    po_item_match.get("po_number")
                    if po_item_match
                    else inv_item.get("po_number")
                ),
                "grn_number": (
                    grn_item_match.get("grn_number") if grn_item_match else None
                ),
            }
        )

    related_pos_data = []
    for po in invoice.purchase_orders:
        related_pos_data.append(
            {
                "id": po.id,
                "po_number": po.po_number,
                "order_date": str(po.order_date) if po.order_date else None,
                "line_items": po.line_items,
                "po_grand_total": po.grand_total,
            }
        )

    invoice_doc = {"file_path": invoice.file_path}
    po_doc = (
        {"file_path": invoice.purchase_orders[0].file_path}
        if invoice.purchase_orders
        else None
    )
    grn_doc = {"file_path": invoice.grns[0].file_path} if invoice.grns else None

    suggestion = None
    if invoice.status == models.DocumentStatus.needs_review and invoice.match_trace:
        first_failure = next(
            (step for step in invoice.match_trace if step.get("status") == "FAIL"), None
        )
        if first_failure:
            failure_step_name = first_failure.get("step", "")
            exception_type = ""
            if "Price Match" in failure_step_name:
                exception_type = "PriceMismatchException"
            elif "Quantity Match" in failure_step_name:
                exception_type = "QuantityMismatchException"

            if exception_type:
                heuristic = (
                    db.query(models.LearnedHeuristic)
                    .filter(
                        models.LearnedHeuristic.vendor_name == invoice.vendor_name,
                        models.LearnedHeuristic.exception_type == exception_type,
                        models.LearnedHeuristic.confidence_score >= 0.8,
                        models.LearnedHeuristic.resolution_action == "matched",
                    )
                    .order_by(models.LearnedHeuristic.confidence_score.desc())
                    .first()
                )
                if heuristic:
                    condition_text = ""
                    if exception_type == "PriceMismatchException":
                        max_variance = heuristic.learned_condition.get(
                            "max_variance_percent", 0
                        )
                        condition_text = f"price mismatches of up to {max_variance}%"
                    suggestion = {
                        "message": f"You have previously approved {condition_text} for {invoice.vendor_name}. This invoice appears to match that pattern.",
                        "action": heuristic.resolution_action,
                        "confidence": heuristic.confidence_score,
                    }

    invoice_header_data = {
        "invoice_id": invoice.invoice_id,
        "vendor_name": invoice.vendor_name,
        "vendor_address": invoice.vendor_address,
        "buyer_name": invoice.buyer_name,
        "buyer_address": invoice.buyer_address,
        "shipping_address": invoice.shipping_address,
        "billing_address": invoice.billing_address,
        "invoice_date": str(invoice.invoice_date) if invoice.invoice_date else None,
        "due_date": str(invoice.due_date) if invoice.due_date else None,
        "payment_terms": invoice.payment_terms,
        "subtotal": invoice.subtotal,
        "tax": invoice.tax,
        "grand_total": invoice.grand_total,
        "other_header_fields": invoice.other_header_fields,
        "metadata": invoice.invoice_metadata,
    }

    po_editable_fields_config = (
        db.query(
            models.ExtractionFieldConfiguration.field_name,
            models.ExtractionFieldConfiguration.display_name,
        )
        .filter_by(
            document_type=models.DocumentTypeEnum.PurchaseOrder,
            is_editable=True,
            is_enabled=True,
        )
        .all()
    )
    po_editable_fields = [
        {"field_name": r.field_name, "display_name": r.display_name}
        for r in po_editable_fields_config
    ]

    return {
        "invoice_id": invoice.invoice_id,
        "invoice_header_data": invoice_header_data,
        "vendor_name": invoice.vendor_name,
        "grand_total": invoice.grand_total,
        "line_item_comparisons": comparison_lines,
        "related_pos": related_pos_data,
        "related_grns": [
            schemas.GoodsReceiptNote.from_orm(grn).model_dump(mode="json")
            for grn in invoice.grns
        ],
        "invoice_notes": invoice.notes,
        "invoice_status": invoice.status.value,
        "match_trace": invoice.match_trace or [],
        "gl_code": invoice.gl_code,
        "related_documents": {
            "invoice": invoice_doc,
            "po": (
                {"file_path": invoice.purchase_orders[0].file_path}
                if invoice.purchase_orders
                else None
            ),
            "grn": {"file_path": invoice.grns[0].file_path} if invoice.grns else None,
        },
        "all_related_documents": {
            "pos": [
                {
                    "id": po.id,
                    "file_path": po.file_path,
                    "po_number": po.po_number,
                    "data": schemas.PurchaseOrder.from_orm(po).model_dump(mode="json"),
                }
                for po in invoice.purchase_orders
            ],
            "grns": [
                {
                    "id": grn.id,
                    "file_path": grn.file_path,
                    "grn_number": grn.grn_number,
                    "data": schemas.GoodsReceiptNote.from_orm(grn).model_dump(
                        mode="json"
                    ),
                }
                for grn in invoice.grns
            ],
        },
        "suggestion": suggestion,
        "po_editable_fields": po_editable_fields,
    }

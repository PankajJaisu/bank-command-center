# src/app/utils/data_formatting.py
import re
from sqlalchemy.orm import Session
from app.db import models, schemas
from app.config import PRICE_TOLERANCE_PERCENT


def format_invoice_dossier_for_display(invoice: models.Invoice) -> dict:
    """Formats a full invoice object into a user-friendly dictionary for the frontend."""
    if not invoice:
        return {}

    # Use the new many-to-many relationships
    grn = invoice.grns[0] if invoice.grns else None
    po = grn.po if grn else None

    formatted_exceptions = []
    if (
        invoice.status == models.DocumentStatus.needs_review
        and invoice.exception_details
    ):
        for exc in invoice.exception_details:
            # This formatting logic can be greatly expanded based on exception types
            formatted_exc = {
                "title": f"🚨 {exc.get('type', 'Unknown Exception')}",
                "details": [
                    {
                        "label": "Details",
                        "value": exc.get("message", "No details provided"),
                    }
                ],
            }
            formatted_exceptions.append(formatted_exc)

    return {
        "invoice_info": {
            "ID": invoice.invoice_id,
            "Vendor": invoice.vendor_name,
            "Date": str(invoice.invoice_date) if invoice.invoice_date else "N/A",
            "Status": invoice.status.value.replace("_", " ").title(),
        },
        "financials": {
            "Subtotal": f"${invoice.subtotal or 0:,.2f}",
            "Tax": f"${invoice.tax or 0:,.2f}",
            "Grand Total": f"${invoice.grand_total or 0:,.2f}",
        },
        "linked_documents": {
            "PO Number": po.po_number if po else "N/A",
            "GRN Number": grn.grn_number if grn else "N/A",
        },
        "exceptions": formatted_exceptions,
        "raw_data": schemas.Invoice.from_orm(
            invoice
        ).model_dump(),  # Keep raw data for expander
    }


def format_full_dossier(invoice: models.Invoice, db: Session) -> dict:
    """
    Gathers an invoice and all its related documents (PO, GRN) into a
    comprehensive dictionary for detailed frontend display.
    Handles various linking permutations (e.g., Invoice -> GRN -> PO, or Invoice -> PO).
    """
    if not invoice:
        return {}

    # --- START FIX: Correctly gather related documents ---
    # Use the new many-to-many relationships

    # Take the first related documents for the dossier view.
    # In a real-world multi-document scenario, the UI would need a way to select which to view.
    grn = invoice.grns[0] if invoice.grns else None
    po = None

    # Find PO through GRN first (most common path)
    if grn and grn.po:
        po = grn.po
    # Fallback to direct PO link on invoice if no GRN or GRN->PO link
    elif invoice.purchase_orders:
        po = invoice.purchase_orders[0]
    # --- END FIX ---

    # --- MODIFIED SECTION ---
    # Parse the new match_trace instead of exception_details
    failed_checks = []
    if invoice.status == models.DocumentStatus.needs_review and invoice.match_trace:
        for trace_step in invoice.match_trace:
            if trace_step.get("status") == "FAIL":
                failed_checks.append(
                    {
                        "title": f"🚨 {trace_step.get('step', 'Unknown Step')}",
                        "message": trace_step.get("message", "No details provided"),
                        "details": trace_step.get("details", {}),
                    }
                )
    # --- END MODIFICATION ---

    # Package everything into a structured response
    dossier = {
        "summary": {
            "invoice_id": invoice.invoice_id,
            "vendor_name": invoice.vendor_name,
            "grand_total": invoice.grand_total,
            "status": invoice.status.value,
            "invoice_date": (
                str(invoice.invoice_date) if invoice.invoice_date else "N/A"
            ),
        },
        "documents": {
            "invoice": {
                "data": schemas.Invoice.from_orm(invoice).model_dump(mode="json"),
                "file_path": invoice.file_path,
            },
            "grn": {
                "data": (
                    schemas.GoodsReceiptNote.from_orm(grn).model_dump(mode="json")
                    if grn
                    else None
                ),
                "file_path": grn.file_path if grn else None,
            },
            "po": {
                "data": (
                    schemas.PurchaseOrder.from_orm(po).model_dump(mode="json")
                    if po
                    else None
                ),
                "file_path": po.file_path if po else None,
            },
        },
        # This is now the summary of failed checks from the trace
        "exceptions": failed_checks,
        # The full trace is available for a detailed view
        "match_trace": invoice.match_trace,
        "ai_recommendation": invoice.ai_recommendation,
    }

    return dossier

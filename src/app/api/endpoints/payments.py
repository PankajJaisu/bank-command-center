# src/app/api/endpoints/payments.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from datetime import datetime

from app.api.dependencies import get_db, get_current_user
from app.db import models, schemas
from app.utils.auditing import log_audit_event
from sqlalchemy.orm import joinedload

router = APIRouter()


# --- HELPER FUNCTION TO APPLY USER FILTERS ---
def _apply_user_filters(query, current_user: models.User, db: Session):
    """Apply user permission filters to invoice queries."""
    if current_user.role.name == "ap_processor":
        user_with_vendors = (
            db.query(models.User)
            .options(joinedload(models.User.assigned_vendors))
            .filter(models.User.id == current_user.id)
            .first()
        )

        if user_with_vendors and user_with_vendors.assigned_vendors:
            assigned_vendor_names = [
                v.vendor_name for v in user_with_vendors.assigned_vendors
            ]
            query = query.filter(models.Invoice.vendor_name.in_(assigned_vendor_names))
        else:
            # If no vendors assigned, return empty result
            query = query.filter(models.Invoice.id == -1)

    return query


class CreatePaymentBatchRequest(BaseModel):
    invoice_ids: List[int]  # List of invoice database IDs


@router.get("/payable", response_model=List[schemas.InvoiceSummary])
def get_payable_invoices(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """Retrieves all invoices with status 'matched', respecting user permissions."""
    query = db.query(models.Invoice).filter(
        models.Invoice.status == models.DocumentStatus.matched
    )

    # Apply user permission filters
    query = _apply_user_filters(query, current_user, db)

    return query.order_by(models.Invoice.due_date.asc()).all()


@router.post("/batches", status_code=201)
def create_payment_batch(
    request: CreatePaymentBatchRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Creates a payment batch from a list of 'matched' invoice IDs, updates their status
    to 'pending_payment', and stamps them with a unique batch ID.
    Respects user permissions.
    """
    if not request.invoice_ids:
        raise HTTPException(status_code=400, detail="No invoice IDs provided.")

    query = db.query(models.Invoice).filter(
        models.Invoice.id.in_(request.invoice_ids),
        models.Invoice.status == models.DocumentStatus.matched,
    )

    # Apply user permission filters
    query = _apply_user_filters(query, current_user, db)

    invoices = query.all()

    if len(invoices) != len(request.invoice_ids):
        raise HTTPException(
            status_code=400,
            detail="One or more invoices were not in 'matched' status, did not exist, or you don't have permission to access them.",
        )

    if not invoices:
        raise HTTPException(
            status_code=400, detail="No valid invoices found to create a batch."
        )

    batch_id = f"PAY-BATCH-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    total_amount = 0

    for inv in invoices:
        inv.status = models.DocumentStatus.pending_payment
        inv.payment_batch_id = batch_id
        total_amount += inv.grand_total or 0

        # --- MODIFIED: Use the correct arguments for the log function ---
        log_audit_event(
            db=db,
            invoice_db_id=inv.id,
            user=current_user.email,
            action="Added to Payment Batch",
            entity_type="Invoice",
            entity_id=inv.invoice_id,
            summary=f"Added to payment batch {batch_id}",
            details={"batch_id": batch_id, "amount": inv.grand_total},
        )
        # --- END MODIFICATION ---

    db.commit()

    return {
        "message": f"Payment batch {batch_id} created successfully.",
        "batch_id": batch_id,
        "processed_invoice_count": len(invoices),
        "total_amount": total_amount,
    }

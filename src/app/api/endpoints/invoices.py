# src/app/api/endpoints/invoices.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.orm.exc import StaleDataError
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import math

from app.api.dependencies import get_db, get_current_user
from app.db import models, schemas
from app.utils import data_formatting
from app.modules.matching import comparison as comparison_service
from app.modules.matching import engine as matching_engine
from app.utils.auditing import log_audit_event
from app.services.rule_evaluator import evaluate_policy
from app.services.permission_service import apply_invoice_permissions
from app.services import invoice_service
from app.utils.logging import get_logger
from pydantic import BaseModel, Field

logger = get_logger(__name__)

router = APIRouter()


# --- HELPER FUNCTIONS ---
def _apply_user_filters(query, current_user: models.User, db: Session):
    return apply_invoice_permissions(query, current_user, db)


def _check_invoice_permission(
    invoice: models.Invoice, current_user: models.User, db: Session
) -> bool:
    if current_user.role.name == "admin":
        return True
    user_with_policies = (
        db.query(models.User)
        .options(joinedload(models.User.permission_policies))
        .filter(models.User.id == current_user.id)
        .one()
    )
    return any(
        policy.is_active and evaluate_policy(invoice, policy.conditions)
        for policy in user_with_policies.permission_policies
    )


def _learn_from_manual_approval(db: Session, invoice: models.Invoice):
    """
    Analyzes a manually approved invoice to create or update a LearnedHeuristic.
    This now reads from the match_trace field.
    """
    if not invoice.match_trace or not invoice.vendor_name:
        return

    first_failure = next(
        (step for step in invoice.match_trace if step.get("status") == "FAIL"), None
    )
    if not first_failure:
        return

    failure_details = first_failure.get("details", {})
    failure_step = first_failure.get("step", "")
    learned_condition = {}
    exception_type = ""

    if "Price Match" in failure_step:
        exception_type = "PriceMismatchException"
        invoice_price = failure_details.get("inv_price", 0)
        po_price = failure_details.get("po_price", 0)
        if po_price > 0:
            variance = abs(invoice_price - po_price) / po_price * 100
            learned_condition = {"max_variance_percent": math.ceil(variance)}
    elif "Quantity Match" in failure_step:
        exception_type = "QuantityMismatchException"
        invoice_qty = failure_details.get("invoice_qty", 0)
        source_qty = failure_details.get(
            "grn_total_qty", failure_details.get("po_qty", 0)
        )
        if source_qty and invoice_qty:
            quantity_diff = abs(invoice_qty - source_qty)
            learned_condition = {"max_quantity_diff": math.ceil(quantity_diff)}

    if not exception_type or not learned_condition:
        return

    heuristic = (
        db.query(models.LearnedHeuristic)
        .filter_by(
            vendor_name=invoice.vendor_name,
            exception_type=exception_type,
            learned_condition=learned_condition,
        )
        .first()
    )
    if heuristic:
        heuristic.trigger_count += 1
        heuristic.confidence_score = 1.0 - (1.0 / (heuristic.trigger_count + 1))
        logger.info(
            f"✅ Strengthened heuristic for {invoice.vendor_name}: {exception_type}. New confidence: {heuristic.confidence_score:.2f}"
        )
    else:
        new_heuristic = models.LearnedHeuristic(
            vendor_name=invoice.vendor_name,
            exception_type=exception_type,
            learned_condition=learned_condition,
            resolution_action=models.DocumentStatus.matched.value,
            trigger_count=1,
            confidence_score=0.5,
        )
        db.add(new_heuristic)
        logger.info(
            f"✅ Created new heuristic for {invoice.vendor_name}: {exception_type}"
        )


class UpdateNoteRequest(BaseModel):
    notes: str


class UpdateGLCodeRequest(BaseModel):
    gl_code: str


class PutOnHoldRequest(BaseModel):
    hold_days: int = Field(..., gt=0)


class BatchUpdateStatusRequest(BaseModel):
    invoice_ids: List[int]
    new_status: str
    reason: Optional[str] = "Bulk update via Invoice Explorer"


class BatchMarkAsPaidRequest(BaseModel):
    invoice_ids: List[int]


# --- API ENDPOINTS ---


@router.get("/queue-summary", response_model=Dict[str, Any])
def get_queue_summary(
    statuses: List[str] = Query(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return invoice_service.get_queue_summary_logic(db, statuses, current_user)


@router.get("/", response_model=List[schemas.InvoiceSummary])
def get_invoices(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    query = db.query(models.Invoice)
    query = _apply_user_filters(query, current_user, db)
    if status and status.strip():
        try:
            query = query.filter(models.Invoice.status == models.DocumentStatus(status))
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Invalid status value: {status}"
            )
    return query.order_by(models.Invoice.invoice_date.desc()).all()


@router.get("/{invoice_db_id}/matching-policies", response_model=List[str])
def get_matching_permission_policies(
    invoice_db_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    invoice = (
        db.query(models.Invoice).filter(models.Invoice.id == invoice_db_id).first()
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if current_user.role.name == "admin":
        return ["Admin Access (all invoices)"]
    user_with_policies = (
        db.query(models.User)
        .options(joinedload(models.User.permission_policies))
        .filter(models.User.id == current_user.id)
        .one()
    )
    matching_policies = [
        policy.name
        for policy in user_with_policies.permission_policies
        if policy.is_active and evaluate_policy(invoice, policy.conditions)
    ]
    if not matching_policies:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view this invoice's policies.",
        )
    return matching_policies


@router.post("/{invoice_id}/update-status")
def update_invoice_status_endpoint(
    invoice_id: str,
    request: schemas.UpdateInvoiceStatusRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    try:
        invoice = (
            db.query(models.Invoice)
            .filter(models.Invoice.invoice_id == invoice_id)
            .first()
        )
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        invoice.version = request.version
        if not _check_invoice_permission(invoice, current_user, db):
            raise HTTPException(
                status_code=403, detail="Not authorized to update this invoice"
            )

        # --- START MODIFICATION: Delegate logic to the batch endpoint ---
        # This simplifies the single update and centralizes the core logic.
        batch_request = BatchUpdateStatusRequest(
            invoice_ids=[invoice.id],
            new_status=request.new_status,
            reason=request.reason,
        )
        result = batch_update_invoice_status(batch_request, db, current_user)
        return {
            "message": f"Invoice {invoice_id} status updated to '{request.new_status}' successfully."
        }
        # --- END MODIFICATION ---

    except StaleDataError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="This invoice has been modified by someone else. Please refresh and try again.",
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{invoice_id}/dossier")
def get_invoice_dossier(
    invoice_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    invoice = (
        db.query(models.Invoice).filter(models.Invoice.invoice_id == invoice_id).first()
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if not _check_invoice_permission(invoice, current_user, db):
        raise HTTPException(
            status_code=403, detail="Not authorized to view this invoice"
        )
    return data_formatting.format_full_dossier(invoice, db)


@router.get("/{invoice_db_id}/comparison-data")
def get_invoice_comparison_data(
    invoice_db_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    invoice = (
        db.query(models.Invoice).filter(models.Invoice.id == invoice_db_id).first()
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if not _check_invoice_permission(invoice, current_user, db):
        raise HTTPException(
            status_code=403, detail="Not authorized to view this invoice"
        )
    data = comparison_service.prepare_comparison_data(db, invoice_db_id)
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])
    return data


@router.put("/{invoice_db_id}/notes")
def update_invoice_notes(
    invoice_db_id: int,
    request: UpdateNoteRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    invoice = (
        db.query(models.Invoice).filter(models.Invoice.id == invoice_db_id).first()
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if not _check_invoice_permission(invoice, current_user, db):
        raise HTTPException(
            status_code=403, detail="Not authorized to update this invoice"
        )
    invoice.notes = request.notes
    log_audit_event(
        db=db,
        invoice_db_id=invoice.id,
        user=current_user.email,
        action="Reference Notes Updated",
        entity_type="Invoice",
        entity_id=invoice.invoice_id,
        summary=f"Notes updated: '{request.notes[:50]}{'...' if len(request.notes) > 50 else ''}'",
    )
    db.commit()
    return {"message": "Notes updated successfully."}


@router.put("/{invoice_db_id}/gl-code")
def update_invoice_gl_code(
    invoice_db_id: int,
    request: UpdateGLCodeRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    invoice = (
        db.query(models.Invoice).filter(models.Invoice.id == invoice_db_id).first()
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if not _check_invoice_permission(invoice, current_user, db):
        raise HTTPException(
            status_code=403, detail="Not authorized to update this invoice"
        )
    invoice.gl_code = request.gl_code
    log_audit_event(
        db=db,
        invoice_db_id=invoice.id,
        user=current_user.email,
        action="GL Code Applied",
        entity_type="Invoice",
        entity_id=invoice.invoice_id,
        summary=f"GL Code set to '{request.gl_code}'.",
        details={"gl_code": request.gl_code},
    )
    db.commit()
    return {"message": "GL Code updated successfully."}


# --- START MODIFICATION: Add Learning Logic to Batch Update ---
@router.post("/batch-update-status")
def batch_update_invoice_status(
    request: BatchUpdateStatusRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not request.invoice_ids:
        raise HTTPException(status_code=400, detail="No invoice IDs provided.")
    try:
        new_status_enum = models.DocumentStatus(request.new_status)
    except ValueError:
        raise HTTPException(
            status_code=400, detail=f"Invalid status value: {request.new_status}"
        )

    invoices_to_update = (
        db.query(models.Invoice)
        .filter(models.Invoice.id.in_(request.invoice_ids))
        .all()
    )
    if len(invoices_to_update) != len(set(request.invoice_ids)):
        raise HTTPException(
            status_code=404, detail="One or more invoice IDs were not found."
        )

    updated_count = 0
    for invoice in invoices_to_update:
        if not _check_invoice_permission(invoice, current_user, db):
            db.rollback()
            raise HTTPException(
                status_code=403,
                detail=f"You do not have permission to update invoice {invoice.invoice_id}. Batch operation aborted.",
            )

        old_status = invoice.status
        invoice.status = new_status_enum

        if new_status_enum == models.DocumentStatus.paid:
            invoice.paid_date = datetime.utcnow().date()

        # --- THE LEARNING TRIGGER ---
        # If an invoice that needed review is now approved (e.g. to 'matched'), learn from it.
        # This now works for both single and batch approvals, including from the AI Manager.
        if (
            old_status == models.DocumentStatus.needs_review
            and new_status_enum == models.DocumentStatus.matched
        ):
            logger.info(
                f"🧠 Learning from manual approval of invoice {invoice.invoice_id} via {current_user.email}..."
            )
            _learn_from_manual_approval(db, invoice)

        log_audit_event(
            db=db,
            invoice_db_id=invoice.id,
            user=current_user.email,
            action="Status Changed (Bulk)",
            entity_type="Invoice",
            entity_id=invoice.invoice_id,
            summary=f"Status changed from '{old_status.value}' to '{new_status_enum.value}'",
            details={
                "from": old_status.value,
                "to": new_status_enum.value,
                "reason": request.reason,
            },
        )
        updated_count += 1

    db.commit()
    return {
        "message": f"Successfully updated {updated_count} of {len(request.invoice_ids)} invoices to '{request.new_status}'.",
        "updated_count": updated_count,
    }


# --- END MODIFICATION ---


@router.post("/batch-mark-as-paid")
def batch_mark_as_paid(
    request: BatchMarkAsPaidRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not request.invoice_ids:
        raise HTTPException(status_code=400, detail="No invoice IDs provided.")
    query = db.query(models.Invoice).filter(
        models.Invoice.id.in_(request.invoice_ids),
        models.Invoice.status.in_(
            [models.DocumentStatus.matched, models.DocumentStatus.pending_payment]
        ),
    )
    query = _apply_user_filters(query, current_user, db)
    updated_count = 0
    for invoice in query.all():
        invoice.status = models.DocumentStatus.paid
        invoice.paid_date = datetime.utcnow().date()
        log_audit_event(
            db=db,
            invoice_db_id=invoice.id,
            user=current_user.email,
            action="Payment Confirmed (Bulk)",
            entity_type="Invoice",
            entity_id=invoice.invoice_id,
            summary=f"Marked as paid in batch.",
            details={"batch_id": invoice.payment_batch_id or "N/A"},
        )
        updated_count += 1
    db.commit()
    if updated_count == 0:
        raise HTTPException(
            status_code=404,
            detail="No valid invoices in 'matched' or 'pending_payment' status were found for the given IDs.",
        )
    return {
        "message": f"Successfully marked {updated_count} invoice(s) as paid.",
        "updated_count": updated_count,
    }


@router.get("/by-category", response_model=List[schemas.InvoiceSummary])
def get_invoices_by_category(
    category: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    query = db.query(models.Invoice).filter(
        models.Invoice.status == models.DocumentStatus.needs_review,
        models.Invoice.review_category == category,
    )
    query = _apply_user_filters(query, current_user, db)
    return query.order_by(models.Invoice.invoice_date.desc()).all()


@router.post("/batch-rematch", status_code=202)
def batch_rematch_invoices(
    request: schemas.BatchActionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not request.invoice_ids:
        raise HTTPException(status_code=400, detail="No invoice IDs provided.")
    query = db.query(models.Invoice).filter(models.Invoice.id.in_(request.invoice_ids))
    query = _apply_user_filters(query, current_user, db)
    rematched_count = 0
    for inv in query.all():
        inv.status = models.DocumentStatus.matching
        log_audit_event(
            db=db,
            invoice_db_id=inv.id,
            user=current_user.email,
            action="Manual Rematch Triggered",
            entity_type="Invoice",
            entity_id=inv.invoice_id,
            summary="Rematch triggered from Invoice Explorer.",
            details={"source": "Invoice Explorer"},
        )
        background_tasks.add_task(matching_engine.run_match_for_invoice, db, inv.id)
        rematched_count += 1
    db.commit()
    return {
        "message": f"Successfully queued {rematched_count} invoice(s) for re-matching.",
        "rematched_count": rematched_count,
    }


@router.get(
    "/by-string-id/{invoice_id_str:path}", response_model=schemas.InvoiceSummary
)
def get_invoice_by_string_id(
    invoice_id_str: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    invoice = (
        db.query(models.Invoice)
        .filter(models.Invoice.invoice_id == invoice_id_str)
        .first()
    )
    if not invoice:
        raise HTTPException(
            status_code=404, detail=f"Invoice with ID '{invoice_id_str}' not found."
        )
    if not _check_invoice_permission(invoice, current_user, db):
        raise HTTPException(
            status_code=403, detail="Not authorized to view this invoice"
        )
    return invoice


@router.post("/{invoice_db_id}/hold", response_model=schemas.InvoiceSummary)
def put_invoice_on_hold(
    invoice_db_id: int,
    request: PutOnHoldRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    invoice = (
        db.query(models.Invoice).filter(models.Invoice.id == invoice_db_id).first()
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if not _check_invoice_permission(invoice, current_user, db):
        raise HTTPException(
            status_code=403, detail="Not authorized to update this invoice"
        )
    old_status = invoice.status
    invoice.status = models.DocumentStatus.on_hold
    invoice.hold_until = datetime.utcnow() + timedelta(days=request.hold_days)
    log_audit_event(
        db=db,
        invoice_db_id=invoice.id,
        user=current_user.email,
        action="Invoice Placed on Hold",
        entity_type="Invoice",
        entity_id=invoice.invoice_id,
        summary=f"Invoice placed on hold for {request.hold_days} days.",
        details={
            "from_status": old_status.value,
            "hold_days": request.hold_days,
            "hold_until": invoice.hold_until.isoformat(),
        },
    )
    db.commit()
    db.refresh(invoice)
    return invoice

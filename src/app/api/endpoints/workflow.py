# src/app/api/endpoints/collaboration.py
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from app.api.dependencies import get_db, get_current_user, get_invoice_for_user
from app.db import models, schemas
from app.utils.auditing import log_audit_event

router = APIRouter()


class CommunicationRequest(BaseModel):
    message: str


@router.post(
    "/invoices/{invoice_db_id}/request-vendor-response",
    status_code=202,
    summary="Send message to Vendor",
)
def request_vendor_response(
    invoice_db_id: int,
    request: CommunicationRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    invoice: models.Invoice = Depends(get_invoice_for_user),
):
    """Logs an email communication to a vendor and updates the invoice status."""
    # Invoice is already retrieved and permission-checked by the dependency

    invoice.status = models.DocumentStatus.pending_vendor_response

    comment = models.Comment(
        invoice_id=invoice_db_id,
        user=current_user.email,
        text=f"Sent to vendor: {request.message}",
        type="vendor",
    )
    db.add(comment)

    log_audit_event(
        db=db,
        invoice_db_id=invoice_db_id,
        user=current_user.email,
        action="Vendor Communication Sent",
        entity_type="Invoice",
        entity_id=invoice.invoice_id,
        summary=f"Sent message to vendor: {request.message[:50]}{'...' if len(request.message) > 50 else ''}",
        details={"message": request.message},
    )

    db.commit()
    return {"message": "Vendor communication logged and status updated."}


@router.post(
    "/invoices/{invoice_db_id}/request-internal-response",
    status_code=202,
    summary="Send message to Internal Team",
)
def request_internal_response(
    invoice_db_id: int,
    request: CommunicationRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    invoice: models.Invoice = Depends(get_invoice_for_user),
):
    """Logs an internal communication and updates the invoice status."""
    # Invoice is already retrieved and permission-checked by the dependency

    invoice.status = models.DocumentStatus.pending_internal_response

    comment = models.Comment(
        invoice_id=invoice_db_id,
        user=current_user.email,
        text=f"Sent for internal review: {request.message}",
        type="internal_review",
    )
    db.add(comment)

    log_audit_event(
        db=db,
        invoice_db_id=invoice_db_id,
        user=current_user.email,
        action="Internal Review Requested",
        entity_type="Invoice",
        entity_id=invoice.invoice_id,
        summary=f"Requested internal review: {request.message[:50]}{'...' if len(request.message) > 50 else ''}",
        details={"message": request.message},
    )

    db.commit()
    return {"message": "Internal review requested and status updated."}


@router.get("/invoices/{invoice_db_id}/comments", response_model=List[schemas.Comment])
def get_invoice_comments(
    invoice_db_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    invoice: models.Invoice = Depends(get_invoice_for_user),
):
    """Retrieves all comments for a specific invoice."""
    # Invoice permission is already checked by the dependency
    return (
        db.query(models.Comment)
        .filter(models.Comment.invoice_id == invoice_db_id)
        .order_by(models.Comment.created_at.asc())
        .all()
    )


@router.post("/invoices/{invoice_db_id}/comments", response_model=schemas.Comment)
def add_invoice_comment(
    invoice_db_id: int,
    comment_in: schemas.CommentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    invoice: models.Invoice = Depends(get_invoice_for_user),
):
    """Adds a new internal comment to an invoice."""
    # Invoice is already retrieved and permission-checked by the dependency

    db_comment = models.Comment(
        invoice_id=invoice_db_id,
        user=current_user.email,  # Use current user instead of comment_in.user
        text=comment_in.text,
        type="internal",
    )
    db.add(db_comment)
    log_audit_event(
        db=db,
        invoice_db_id=invoice_db_id,
        user=current_user.email,
        action="Internal Comment Added",
        entity_type="Invoice",
        entity_id=invoice.invoice_id,
        summary=f"Added comment: {comment_in.text[:50]}{'...' if len(comment_in.text) > 50 else ''}",
        details={"comment": comment_in.text},
    )
    db.commit()
    db.refresh(db_comment)
    return db_comment


@router.get(
    "/invoices/{invoice_db_id}/audit-log", response_model=List[schemas.AuditLog]
)
def get_invoice_audit_log(
    invoice_db_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    invoice: models.Invoice = Depends(get_invoice_for_user),
):
    """Retrieves the audit log for a specific invoice."""
    # Invoice permission is already checked by the dependency
    return (
        db.query(models.AuditLog)
        .filter(models.AuditLog.invoice_db_id == invoice_db_id)
        .order_by(models.AuditLog.timestamp.desc())
        .all()
    )

from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

from app.db import models
from app.utils.logging import get_logger

logger = get_logger(__name__)


def log_audit_event(
    db: Session,
    user: str,
    action: str,
    entity_type: str,
    entity_id: str,
    invoice_db_id: Optional[int] = None,
    summary: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    commit: bool = False,
):
    """Creates and adds an audit log entry to the database session."""
    # --- MODIFICATION: Allow non-invoice-specific logging ---
    if invoice_db_id:
        # If invoice_db_id is provided, ensure it's valid.
        invoice_id_str_from_db = (
            db.query(models.Invoice.invoice_id)
            .filter(models.Invoice.id == invoice_db_id)
            .scalar()
        )
        if not invoice_id_str_from_db:
            logger.warning(
                f"Warning: Audit log for non-existent invoice DB ID {invoice_db_id}"
            )
            return
        # Ensure entity_id is consistent if provided.
        if entity_type == "Invoice" and entity_id != invoice_id_str_from_db:
            logger.warning(
                f"Warning: Mismatch between entity_id '{entity_id}' and invoice_id_str '{invoice_id_str_from_db}' from DB."
            )
            entity_id = invoice_id_str_from_db
    # --- END MODIFICATION ---

    audit_log = models.AuditLog(
        entity_type=entity_type,
        entity_id=str(entity_id),  # Ensure entity_id is a string
        invoice_db_id=invoice_db_id,
        user=user,
        action=action,
        summary=summary,
        details=details or {},
    )
    db.add(audit_log)

    if commit:
        db.commit()

from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.db import models
from app.utils.auditing import log_audit_event
from app.utils.logging import get_logger

logger = get_logger(__name__)


def evaluate_rule(invoice: models.Invoice, rule: models.AutomationRule) -> bool:
    """Evaluates if a single invoice matches the conditions of a single rule."""
    conditions = rule.conditions
    if not conditions:
        return False  # A rule must have conditions

    field = conditions.get("field")
    operator = conditions.get("operator")
    value = conditions.get("value")

    if not all([field, operator]):
        return False  # Invalid condition structure

    invoice_value = getattr(invoice, field, None)
    if invoice_value is None and operator != "is_null":
        return False

    try:
        if operator == "equals":
            return str(invoice_value) == str(value)
        elif operator == "<":
            return float(invoice_value) < float(value)
        elif operator == ">":
            return float(invoice_value) > float(value)
        elif operator == "contains":
            return str(value).lower() in str(invoice_value).lower()
        elif operator == "is_null":
            return invoice_value is None
        # Add more operators here as needed (e.g., <=, >=, etc.)
    except (ValueError, TypeError):
        # Failed to compare values (e.g., trying to compare a string with a number)
        return False

    return False


def run_automation_engine(db: Session):
    """
    Finds all active rules and applies them to pending invoices.
    """
    logger.info("--- 🤖 Running Automation Rule Engine ---")

    # 1. Fetch all active rules and pending invoices
    active_rules = db.query(models.AutomationRule).filter_by(is_active=1).all()
    # We only want to run this on invoices that have passed initial matching
    # or are brand new Non-PO invoices, but not those already deep in review.
    invoices_to_process = (
        db.query(models.Invoice)
        .filter(
            models.Invoice.status.in_(
                [
                    models.DocumentStatus.matched,  # Rule might auto-pay
                    models.DocumentStatus.ingested,  # Rule for non-PO invoices
                ]
            )
        )
        .all()
    )

    if not active_rules:
        logger.info("  -> No active automation rules found. Engine finished.")
        return

    logger.info(
        f"  -> Found {len(active_rules)} active rule(s) and {len(invoices_to_process)} invoice(s) to check."
    )
    processed_count = 0

    # 2. Iterate through each invoice and check against each rule
    for invoice in invoices_to_process:
        for rule in active_rules:
            # Vendor-specific rule check
            if (
                rule.vendor_name
                and rule.vendor_name.lower() != (invoice.vendor_name or "").lower()
            ):
                continue

            if evaluate_rule(invoice, rule):
                logger.info(
                    f"  -> MATCH: Invoice {invoice.invoice_id} matched rule '{rule.rule_name}'."
                )

                # 3. Perform the action
                if rule.action == "approve":
                    # We can directly approve, as it has already passed 3-way match
                    if invoice.status == models.DocumentStatus.matched:
                        invoice.status = models.DocumentStatus.pending_payment
                        action_taken = "Moved to Pending Payment"
                    elif (
                        invoice.status == models.DocumentStatus.ingested
                    ):  # Non-PO invoice
                        invoice.status = models.DocumentStatus.matched
                        action_taken = "Approved Non-PO Invoice"

                    if action_taken:
                        log_audit_event(
                            db=db,
                            invoice_db_id=invoice.id,
                            user="AutomationEngine",
                            action=action_taken,
                            entity_type="Invoice",
                            entity_id=invoice.invoice_id,
                            summary=f"Rule '{rule.rule_name}' triggered automatic action",
                            details={"rule_id": rule.id, "rule_name": rule.rule_name},
                        )
                        processed_count += 1
                        # Stop checking other rules for this invoice once one has matched
                        break

    if processed_count > 0:
        db.commit()

    logger.info(
        f"--- ✅ Automation Engine Finished. Processed {processed_count} invoice(s). ---"
    )

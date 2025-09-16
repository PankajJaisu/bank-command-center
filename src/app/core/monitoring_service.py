from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
import asyncio

from app.db import models
from app.modules.matching import engine as matching_engine
from app.utils.auditing import log_audit_event
from app.utils.email_service import send_email_notification
from app.utils.logging import get_logger

logger = get_logger(__name__)


def check_held_invoices(db: Session):
    """
    Finds invoices whose hold period has expired and re-queues them for matching.
    """
    expired_holds = (
        db.query(models.Invoice)
        .filter(
            models.Invoice.status == models.DocumentStatus.on_hold,
            models.Invoice.hold_until <= datetime.utcnow(),
        )
        .all()
    )

    if not expired_holds:
        return

    logger.info(
        f"  -> Found {len(expired_holds)} invoice(s) with expired hold periods."
    )

    ids_to_rematch = []
    for invoice in expired_holds:
        invoice.status = models.DocumentStatus.matching
        invoice.hold_until = None

        log_audit_event(
            db=db,
            invoice_db_id=invoice.id,
            user="System",
            action="Hold Period Expired",
            entity_type="Invoice",
            entity_id=invoice.invoice_id,
            summary="Hold period expired, re-initiating matching process.",
        )
        ids_to_rematch.append(invoice.id)

    # Commit all status changes at once
    db.commit()

    # Now, trigger rematching for all of them
    for invoice_id in ids_to_rematch:
        # The matching engine will handle its own session and commits
        matching_engine.run_match_for_invoice(db, invoice_id)
        logger.debug(f"  -> Re-queued invoice ID {invoice_id} for matching.")


def check_slas(db: Session):
    """
    Checks all active SLAs against invoices and creates notifications for breaches.
    """
    active_slas = db.query(models.SLA).filter_by(is_active=True).all()
    if not active_slas:
        return

    logger.info(f"  -> Checking {len(active_slas)} active SLA(s)...")

    for sla in active_slas:
        # Build a query based on the SLA's conditions
        query = db.query(models.Invoice)
        conditions = sla.conditions

        # Example condition: {"status": "needs_review"}
        if "status" in conditions:
            try:
                status_enum = models.DocumentStatus(conditions["status"])
                query = query.filter(models.Invoice.status == status_enum)
            except ValueError:
                continue  # Skip SLA with invalid status

        # The expression to calculate age in hours depends on the database dialect
        dialect = db.get_bind().dialect.name
        if dialect == "postgresql":
            age_in_hours_expr = (
                func.extract(
                    "epoch",
                    func.timezone("UTC", func.now()) - models.Invoice.updated_at,
                )
                / 3600
            )
        else:  # SQLite
            age_in_hours_expr = (
                func.julianday(func.datetime("now"))
                - func.julianday(models.Invoice.updated_at)
            ) * 24

        # Find invoices that have breached the SLA threshold
        breached_invoices = query.filter(age_in_hours_expr > sla.threshold_hours).all()

        for invoice in breached_invoices:
            # We use the invoice's string ID for the notification's entity_id
            notification_entity_id = invoice.invoice_id

            message = f"SLA '{sla.name}' breached for Invoice {invoice.invoice_id}. It has been in status '{invoice.status.value}' for too long."

            # Use the existing helper to create a notification if one doesn't already exist for this breach
            _create_notification_if_not_exists(
                db,
                type="SlaBreach",
                message=message,
                entity_id=notification_entity_id,
                entity_type="Invoice",
            )

            # Get all admin emails
            admin_users = (
                db.query(models.User)
                .join(models.Role)
                .filter(models.Role.name == "admin")
                .all()
            )
            admin_emails = [user.email for user in admin_users]

            if admin_emails:
                subject = f"[AP ALERT] SLA Breached for Invoice {invoice.invoice_id}"
                body = f"<p>This is an automated alert.</p><p>{message}</p><p>Please log in to the Proactive Loan Command Center to resolve this issue.</p>"
                # Run the async email function from our sync context
                asyncio.run(send_email_notification(subject, admin_emails, body))


def _create_notification_if_not_exists(
    db: Session,
    type: str,
    message: str,
    entity_id: str,
    entity_type: str,
    action: dict = None,
):
    """Prevents creating duplicate notifications."""
    existing = (
        db.query(models.Notification)
        .filter_by(type=type, related_entity_id=entity_id, is_read=0)
        .first()
    )

    if not existing:
        new_notif = models.Notification(
            type=type,
            message=message,
            related_entity_id=entity_id,
            related_entity_type=entity_type,
            proposed_action=action,
        )
        db.add(new_notif)
        logger.info(
            f"💡 PROACTIVE: Generated new '{type}' notification for {entity_type} {entity_id}."
        )


def check_for_automation_suggestions(db: Session):
    """
    Scans high-confidence learned heuristics and suggests promoting them to
    formal automation rules.
    """
    # Find heuristics with high confidence that don't already have a corresponding rule
    high_confidence_heuristics = (
        db.query(models.LearnedHeuristic)
        .filter(models.LearnedHeuristic.confidence_score >= 0.9)
        .all()
    )

    for heuristic in high_confidence_heuristics:
        # Check if an automation rule for this exact case already exists
        # We need to avoid direct JSON comparison, so we'll check by vendor and action only
        # and then filter in Python code if needed for more precision
        potential_rules = (
            db.query(models.AutomationRule)
            .filter_by(
                vendor_name=heuristic.vendor_name, action=heuristic.resolution_action
            )
            .all()
        )

        # Check in Python if any existing rule has the same conditions
        existing_rule = None
        for rule in potential_rules:
            if rule.conditions == heuristic.learned_condition:
                existing_rule = rule
                break

        if not existing_rule:
            message = f"You often approve '{heuristic.exception_type}' for '{heuristic.vendor_name}' under certain conditions. Would you like to automate this?"
            action = {
                "tool_name": "create_automation_rule",
                "args": {
                    "rule_name": f"Auto-approve {heuristic.exception_type} for {heuristic.vendor_name}",
                    "vendor_name": heuristic.vendor_name,
                    "condition_json": str(heuristic.learned_condition).replace(
                        "'", '"'
                    ),
                    "action": "approve",  # Hard-coded for now
                },
            }
            _create_notification_if_not_exists(
                db,
                "AutomationSuggestion",
                message,
                heuristic.vendor_name,
                "Vendor",
                action,
            )


def check_for_financial_optimizations(db: Session):
    """
    Scans for invoices with approaching early payment discounts.
    """
    deadline = datetime.utcnow().date() + timedelta(days=3)

    invoices_with_discounts = (
        db.query(models.Invoice)
        .filter(
            models.Invoice.status == models.DocumentStatus.matched,
            models.Invoice.discount_due_date.isnot(None),
            models.Invoice.discount_due_date <= deadline,
            models.Invoice.discount_due_date >= datetime.utcnow().date(),
        )
        .all()
    )

    for inv in invoices_with_discounts:
        message = f"Early payment discount of ${inv.discount_amount or 0:,.2f} for Invoice {inv.invoice_id} is expiring on {inv.discount_due_date}. Pay now to capture it."
        _create_notification_if_not_exists(
            db, "Optimization", message, inv.invoice_id, "Invoice"
        )


def run_monitoring_cycle(db: Session):
    """
    The main entry point for the proactive engine's check-up.
    This function is called periodically by the background scheduler.
    """
    logger.info("--- 🧠 Running Proactive Monitoring Cycle ---")
    try:
        check_held_invoices(db)
        check_slas(db)
        check_for_automation_suggestions(db)
        check_for_financial_optimizations(db)
        db.commit()
    except Exception as e:
        logger.error(f"❌ Error during monitoring cycle: {e}")
        db.rollback()
        logger.info("--- ✅ Monitoring Cycle Complete ---")

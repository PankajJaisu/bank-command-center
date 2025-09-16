from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import datetime, timedelta
import math

from app.db import models
from app.utils.logging import get_logger

logger = get_logger(__name__)


def _create_or_update_heuristic(
    db: Session, vendor_name: str, exception_type: str, condition: dict, resolution: str
):
    """
    Finds an existing heuristic or creates a new one, strengthening its confidence.
    """
    if not vendor_name or not exception_type or not condition:
        return

    # Check for an existing heuristic with the exact same condition
    heuristic = (
        db.query(models.LearnedHeuristic)
        .filter_by(
            vendor_name=vendor_name,
            exception_type=exception_type,
            learned_condition=condition,
        )
        .first()
    )

    if heuristic:
        # It exists, so we strengthen it
        heuristic.trigger_count += 1
        # Confidence formula: approaches 1 as trigger_count increases
        heuristic.confidence_score = 1.0 - (1.0 / (heuristic.trigger_count + 1))
        heuristic.last_applied_at = datetime.utcnow()
        logger.info(
            f"  -> ✅ Strengthened heuristic for '{vendor_name}': {exception_type}. New confidence: {heuristic.confidence_score:.2f}"
        )
    else:
        # It's a new pattern, create a new heuristic
        new_heuristic = models.LearnedHeuristic(
            vendor_name=vendor_name,
            exception_type=exception_type,
            learned_condition=condition,
            resolution_action=resolution,  # e.g., 'matched'
            trigger_count=1,
            confidence_score=0.5,  # Start with a moderate confidence
            last_applied_at=datetime.utcnow(),
        )
        db.add(new_heuristic)
        logger.info(
            f"  -> ✨ Created new heuristic for '{vendor_name}': {exception_type}"
        )


def _create_notification_if_not_exists(
    db: Session,
    type: str,
    message: str,
    entity_id: str,
    entity_type: str,
    action: dict = None,
):
    """Prevents creating duplicate active notifications."""
    existing = (
        db.query(models.Notification)
        .filter(
            models.Notification.type == type,
            models.Notification.related_entity_id == entity_id,
            models.Notification.is_read == 0,  # 0 means unread
        )
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
            f"  -> 💡 Generated new '{type}' notification for {entity_type} '{entity_id}'."
        )


def find_manual_approval_patterns(db: Session):
    """
    Analyzes audit logs for manually approved invoices to create or strengthen heuristics.
    This is the core of "Reinforcement Learning" from user actions.
    """
    # Find audit log entries from the last 24 hours where an invoice was manually moved
    # from 'needs_review' to 'matched' (approved). We limit the time window to avoid re-processing old events.
    time_window = datetime.utcnow() - timedelta(hours=24)

    approval_logs = (
        db.query(models.AuditLog)
        .filter(
            and_(
                models.AuditLog.timestamp >= time_window,
                models.AuditLog.entity_type == "Invoice",
                models.AuditLog.action == "Status Changed",
                models.AuditLog.details["from"].as_string() == "needs_review",
                models.AuditLog.details["to"].as_string() == "matched",
            )
        )
        .all()
    )

    if not approval_logs:
        logger.info(
            "  -> No manual approval logs found. No patterns to learn from in this cycle."
        )
        return

    logger.info(
        f"  -> Found {len(approval_logs)} manual approval(s) to analyze for learning."
    )

    for log in approval_logs:
        invoice = db.query(models.Invoice).filter_by(id=log.invoice_db_id).first()
        if not invoice or not invoice.match_trace:
            continue

        # Find the first 'FAIL' in the trace, as that's what the user overrode.
        first_failure = next(
            (step for step in invoice.match_trace if step.get("status") == "FAIL"), None
        )
        if not first_failure:
            continue

        failure_step = first_failure.get("step", "")
        failure_details = first_failure.get("details", {})

        # Learn from Price Mismatches
        if "Price Match" in failure_step:
            invoice_price = failure_details.get("inv_price", 0)
            po_price = failure_details.get("po_price", 0)
            if po_price and invoice_price:
                variance = abs(invoice_price - po_price) / po_price * 100
                # We learn the ceiling of the variance. E.g., if variance is 8.3%, we learn a rule for 9%.
                # This makes the rule more generalized for future invoices.
                learned_condition = {"max_variance_percent": math.ceil(variance)}
                _create_or_update_heuristic(
                    db,
                    invoice.vendor_name,
                    "PriceMismatchException",
                    learned_condition,
                    "matched",
                )

        # Learn from Quantity Mismatches
        elif "Quantity Match" in failure_step:
            invoice_qty = failure_details.get("invoice_qty", 0)
            source_qty = failure_details.get(
                "grn_total_qty", failure_details.get("po_qty", 0)
            )
            if source_qty and invoice_qty:
                # Learn the absolute difference in quantity
                quantity_diff = abs(invoice_qty - source_qty)
                learned_condition = {"max_quantity_diff": math.ceil(quantity_diff)}
                _create_or_update_heuristic(
                    db,
                    invoice.vendor_name,
                    "QuantityMismatchException",
                    learned_condition,
                    "matched",
                )


def find_communication_loops(db: Session):
    """
    Analyzes communication logs to find vendors who repeatedly cause the same types of issues.
    """
    # Find vendors for whom we have sent 3 or more communications in the last 30 days
    time_window = datetime.utcnow() - timedelta(days=30)

    frequent_communications = (
        db.query(
            models.Invoice.vendor_name,
            func.count(models.AuditLog.id).label("issue_count"),
        )
        .join(models.Invoice, models.AuditLog.invoice_db_id == models.Invoice.id)
        .filter(
            and_(
                models.AuditLog.timestamp >= time_window,
                models.AuditLog.action == "Vendor Communication Sent",
            )
        )
        .group_by(models.Invoice.vendor_name)
        .having(func.count(models.AuditLog.id) >= 3)
        .all()
    )

    if not frequent_communications:
        return

    for vendor_name, issue_count in frequent_communications:
        if not vendor_name:
            continue

        message = (
            f"You have contacted '{vendor_name}' {issue_count} times recently. "
            f"Consider setting a stricter policy or a dedicated automation rule for them to reduce manual work."
        )

        _create_notification_if_not_exists(
            db,
            type="RepetitiveIssue",
            message=message,
            entity_id=vendor_name,
            entity_type="Vendor",
        )


def find_workflow_discrepancies(db: Session):
    """
    [Phase 2] Analyzes workflow timings to find bottlenecks.
    """
    # print("  -> [TODO] Scanning for workflow discrepancies...")
    pass


# --- START: NEW INSIGHT-GATHERING FUNCTION ---
def find_process_inefficiencies(db: Session):
    """
    Analyzes audit logs for patterns of inefficiency and stores them.
    """
    logger.info("  -> Scanning for process inefficiencies...")

    # Define the time window for analysis (e.g., last 30 days)
    time_window = datetime.utcnow() - timedelta(days=30)

    # --- Pattern 1: Manual PO Creation ---
    # Find vendors for whom POs are frequently created from invoices
    manual_po_creations = (
        db.query(
            models.Invoice.vendor_name,
            func.count(models.AuditLog.id).label("creation_count"),
        )
        .join(models.Invoice, models.AuditLog.invoice_db_id == models.Invoice.id)
        .filter(
            models.AuditLog.action == "PO Created from Invoice",
            models.AuditLog.timestamp >= time_window,
        )
        .group_by(models.Invoice.vendor_name)
        .all()
    )

    for vendor_name, count in manual_po_creations:
        if not vendor_name:
            continue

        # Find or create a pattern record
        pattern = (
            db.query(models.UserActionPattern)
            .filter_by(pattern_type="MANUAL_PO_CREATION", entity_name=vendor_name)
            .first()
        )

        if pattern:
            pattern.count = count  # Update with the latest count
            pattern.last_detected = datetime.utcnow()
        else:
            new_pattern = models.UserActionPattern(
                pattern_type="MANUAL_PO_CREATION", entity_name=vendor_name, count=count
            )
            db.add(new_pattern)
            logger.debug(
                f"     -> Logged pattern: {count} manual PO creations for '{vendor_name}'."
            )

    # --- Add more patterns here in the future ---
    # e.g., Pattern 2: Frequent rejections for a specific vendor
    # e.g., Pattern 3: High number of edits to a vendor's POs


# --- END: NEW INSIGHT-GATHERING FUNCTION ---


def run_analysis_cycle(db: Session):
    """
    The main entry point for the Proactive Insight Engine.
    This function is called periodically by the background scheduler.
    """
    logger.info("--- 🧠 Running Proactive Insight Engine Analysis Cycle ---")
    try:
        # In Phase 2, we will uncomment and implement these functions.
        find_manual_approval_patterns(db)
        find_communication_loops(db)
        find_workflow_discrepancies(db)
        find_process_inefficiencies(db)  # Call the new function here

        db.commit()  # Commit any new notifications or heuristics
        logger.info("--- ✅ Insight Engine Cycle Complete ---")
    except Exception as e:
        logger.error(f"❌ Error during Insight Engine analysis cycle: {e}")
        db.rollback()

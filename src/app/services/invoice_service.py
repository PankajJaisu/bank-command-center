# src/app/services/invoice_service.py
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.db import models
from .permission_service import apply_invoice_permissions


def get_queue_summary_logic(
    db: Session, statuses: List[str], current_user: models.User
) -> Dict[str, Any]:
    """
    Calculates and returns a contextual summary for a given set of invoice statuses,
    respecting user permissions.
    """
    if not statuses:
        return {
            "total_count": 0,
            "total_value": 0.0,
            "avg_processing_time": None,
            "exception_count": 0,
            "oldest_invoice_days": None,
        }

    # Base query filtered by the user's permissions
    base_query = apply_invoice_permissions(db.query(models.Invoice), current_user, db)

    # Apply the status filter for the specific queue
    queue_query = base_query.filter(models.Invoice.status.in_(statuses))

    # Basic counts and totals
    total_count = queue_query.count()
    total_value = (
        queue_query.with_entities(func.sum(models.Invoice.grand_total)).scalar() or 0.0
    )

    # Exception count (invoices that need review)
    exception_count = queue_query.filter(
        models.Invoice.status == models.DocumentStatus.needs_review
    ).count()

    # Average processing time (in hours, converted to days)
    from ..db.session import engine

    dialect = engine.dialect.name
    if dialect == "postgresql":
        time_diff_expr = (
            func.extract(
                "epoch", func.timezone("UTC", func.now()) - models.Invoice.created_at
            )
            / 3600
        )
    else:  # SQLite
        time_diff_expr = (
            func.julianday(func.datetime("now"))
            - func.julianday(models.Invoice.created_at)
        ) * 24

    avg_processing_time_hours = queue_query.with_entities(
        func.avg(time_diff_expr)
    ).scalar()
    avg_processing_time = (
        round(avg_processing_time_hours / 24, 1) if avg_processing_time_hours else None
    )

    # Oldest invoice age (in days)
    oldest_invoice_created_at = queue_query.with_entities(
        func.min(models.Invoice.created_at)
    ).scalar()
    oldest_invoice_days = None
    if oldest_invoice_created_at:
        oldest_age_hours = (
            datetime.utcnow() - oldest_invoice_created_at
        ).total_seconds() / 3600
        oldest_invoice_days = round(oldest_age_hours / 24, 1)

    summary = {
        "total_count": total_count,
        "total_value": total_value,
        "avg_processing_time": avg_processing_time,
        "exception_count": exception_count,
        "oldest_invoice_days": oldest_invoice_days,
    }

    # Add context-specific metrics based on the primary status of the queue
    primary_status = statuses[0] if statuses else None

    if primary_status == "needs_review":
        # For the review queue, break down exceptions by category
        exception_breakdown = (
            queue_query.with_entities(
                models.Invoice.review_category, func.count(models.Invoice.id)
            )
            .group_by(models.Invoice.review_category)
            .all()
        )
        summary["exception_breakdown"] = {
            cat: count for cat, count in exception_breakdown if cat
        }

    elif primary_status in ["pending_vendor_response", "pending_internal_response"]:
        # For pending queues, calculate the average age
        from ..db.session import engine

        dialect = engine.dialect.name
        if dialect == "postgresql":
            time_diff_expr = (
                func.extract(
                    "epoch",
                    func.timezone("UTC", func.now()) - models.Invoice.updated_at,
                )
                / 3600
            )
        else:  # SQLite
            time_diff_expr = (
                func.julianday(func.datetime("now"))
                - func.julianday(models.Invoice.updated_at)
            ) * 24

        avg_age_hours = (
            queue_query.with_entities(func.avg(time_diff_expr)).scalar() or 0.0
        )
        summary["average_age_days"] = round(avg_age_hours / 24, 1)

    elif primary_status == "matched":
        # For the matched queue, calculate potential discounts
        potential_discounts = (
            queue_query.filter(models.Invoice.discount_amount.isnot(None))
            .with_entities(func.sum(models.Invoice.discount_amount))
            .scalar()
            or 0.0
        )
        summary["potential_discounts"] = potential_discounts

    return summary

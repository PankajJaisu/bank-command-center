# src/app/services/dashboard_service.py

from sqlalchemy.orm import Session, Query as SQLQuery, joinedload
from sqlalchemy import func, case, desc, cast, Float
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from collections import Counter

from ..db import models
from ..db.session import engine
from .permission_service import apply_invoice_permissions

# --- HELPER FUNCTIONS ---


def _get_date_diff_hours(date_col_1, date_col_2):
    """
    Returns a SQLAlchemy expression for the difference between two dates in hours,
    handling different database dialects.
    """
    dialect = engine.dialect.name
    if dialect == "postgresql":
        return func.extract("epoch", date_col_1 - date_col_2) / 3600
    else:
        return (func.julianday(date_col_1) - func.julianday(date_col_2)) * 24


def _get_date_diff_days(date_col_1, date_col_2):
    """
    Returns a SQLAlchemy expression for the difference between two dates in days,
    handling different database dialects.
    """
    dialect = engine.dialect.name
    if dialect == "postgresql":
        return date_col_1 - date_col_2
    else:
        return func.julianday(date_col_1) - func.julianday(date_col_2)


def _get_filtered_query(
    db: Session,
    model,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    user_id: Optional[int] = None,
) -> SQLQuery:
    """
    Creates a base query for invoices, filtered by date and optionally by a specific user.
    Permissions are applied separately.
    """
    query = db.query(model)

    # Date filtering
    if start_date and hasattr(model, "created_at"):
        query = query.filter(
            model.created_at >= datetime.combine(start_date, datetime.min.time())
        )
    if end_date and hasattr(model, "created_at"):
        query = query.filter(
            model.created_at <= datetime.combine(end_date, datetime.max.time())
        )

    # User filtering (for team performance metrics)
    if user_id and model == models.AuditLog:
        user = db.query(models.User).filter_by(id=user_id).first()
        if user:
            query = query.filter(model.user == user.email)

    return query


# --- STRATEGIC DASHBOARD FUNCTIONS ---


def get_admin_dashboard_data(
    db: Session, start_date: Optional[date], end_date: Optional[date]
) -> Dict[str, Any]:
    """
    Generates the comprehensive dashboard data for an Admin/Manager.
    """
    base_query = _get_filtered_query(db, models.Invoice, start_date, end_date)

    # --- Financial Health ---
    total_payable_value = (
        base_query.filter(
            models.Invoice.status.in_(
                [
                    models.DocumentStatus.matched,
                    models.DocumentStatus.pending_payment,
                    models.DocumentStatus.qa_approval,
                ]
            )
        )
        .with_entities(func.sum(models.Invoice.grand_total))
        .scalar()
        or 0.0
    )

    paid_invoices_query = base_query.filter(
        models.Invoice.status == models.DocumentStatus.paid
    )
    total_paid_value = (
        paid_invoices_query.with_entities(func.sum(models.Invoice.grand_total)).scalar()
        or 0.0
    )

    # Days Payable Outstanding (DPO) - A simplified version
    # (Sum of ending AP / Total COGS) * Number of Days. We'll approximate COGS with total paid value.
    days_in_period = (end_date - start_date).days if start_date and end_date else 30
    dpo = (
        (total_payable_value / (total_paid_value or 1)) * days_in_period
        if total_paid_value > 0
        else 0
    )

    # --- Operational Metrics ---
    total_processed = base_query.filter(
        models.Invoice.status != models.DocumentStatus.ingested
    ).count()
    exceptions_count = base_query.filter(
        models.Invoice.status == models.DocumentStatus.needs_review
    ).count()
    exception_rate = (
        (exceptions_count / total_processed * 100) if total_processed > 0 else 0
    )

    # --- Workflow Bottleneck Analysis ---
    statuses_to_track = [
        models.DocumentStatus.needs_review,
        models.DocumentStatus.pending_vendor_response,
        models.DocumentStatus.on_hold,
        models.DocumentStatus.qa_approval,
    ]
    # Use database-specific current time function
    from ..db.session import engine

    dialect = engine.dialect.name
    if dialect == "postgresql":
        current_time = func.timezone("UTC", func.now())
    else:  # SQLite
        current_time = func.datetime("now")

    bottlenecks = {}
    for status in statuses_to_track:
        avg_time_in_status = (
            db.query(
                func.avg(_get_date_diff_hours(current_time, models.Invoice.updated_at))
            )
            .filter(models.Invoice.status == status)
            .scalar()
            or 0
        )
        bottlenecks[status.value] = round(avg_time_in_status, 1)

    # --- Team Performance ---
    processors = (
        db.query(models.User)
        .join(models.Role)
        .filter(models.Role.name == "ap_processor")
        .all()
    )
    team_performance = []
    for processor in processors:
        # A simplified throughput metric: count of status changes made by the user
        throughput = (
            db.query(models.AuditLog)
            .filter(
                models.AuditLog.user == processor.email,
                models.AuditLog.action == "Status Changed",
                (
                    models.AuditLog.timestamp.between(start_date, end_date)
                    if start_date and end_date
                    else True
                ),
            )
            .count()
        )
        team_performance.append(
            {
                "name": processor.full_name or processor.email,
                "invoices_processed": throughput,
            }
        )

    # --- Exception Breakdown Calculation ---
    exception_breakdown_query = (
        base_query.filter(
            models.Invoice.status == models.DocumentStatus.needs_review,
            models.Invoice.review_category.isnot(None),
        )
        .group_by(models.Invoice.review_category)
        .with_entities(models.Invoice.review_category, func.count(models.Invoice.id))
        .all()
    )

    exception_breakdown = [
        {"name": category.replace("_", " ").title(), "count": count}
        for category, count in exception_breakdown_query
    ]

    return {
        "financial_health": {
            "total_payable_value": total_payable_value,
            "days_payable_outstanding": round(dpo, 1),
        },
        "operational_metrics": {
            "total_processed": total_processed,
            "exception_rate": round(exception_rate, 1),
        },
        "workflow_bottlenecks": bottlenecks,
        "team_performance": sorted(
            team_performance, key=lambda x: x["invoices_processed"], reverse=True
        ),
        "exception_breakdown": exception_breakdown,  # Add the new data to the response
    }


def get_processor_dashboard_data(
    db: Session, user: models.User, start_date: Optional[date], end_date: Optional[date]
) -> Dict[str, Any]:
    """
    Generates the personalized dashboard data for an AP Processor.
    """
    # Get invoices this user has permission to see
    user_invoices_query = apply_invoice_permissions(
        _get_filtered_query(db, models.Invoice, start_date, end_date), user, db
    )

    # --- Personal Queue ---
    my_queue = {
        "needs_review": user_invoices_query.filter(
            models.Invoice.status == models.DocumentStatus.needs_review
        ).count(),
        "on_hold": user_invoices_query.filter(
            models.Invoice.status == models.DocumentStatus.on_hold
        ).count(),
        "pending_response": user_invoices_query.filter(
            models.Invoice.status.in_(
                [
                    models.DocumentStatus.pending_vendor_response,
                    models.DocumentStatus.pending_internal_response,
                ]
            )
        ).count(),
    }

    # --- Personal Performance ---
    my_actions = db.query(models.AuditLog).filter(
        models.AuditLog.user == user.email,
        (
            models.AuditLog.timestamp.between(start_date, end_date)
            if start_date and end_date
            else True
        ),
    )
    my_throughput = my_actions.filter(
        models.AuditLog.action == "Status Changed"
    ).count()

    # --- Team Average for Comparison ---
    all_processors_emails = [
        u.email
        for u in db.query(models.User)
        .join(models.Role)
        .filter(models.Role.name == "ap_processor")
        .all()
    ]
    total_team_actions = (
        db.query(func.count(models.AuditLog.id))
        .filter(
            models.AuditLog.user.in_(all_processors_emails),
            models.AuditLog.action == "Status Changed",
            (
                models.AuditLog.timestamp.between(start_date, end_date)
                if start_date and end_date
                else True
            ),
        )
        .scalar()
        or 0
    )
    team_avg_throughput = (
        (total_team_actions / len(all_processors_emails))
        if all_processors_emails
        else 0
    )

    # --- Recent Activity ---
    my_recent_logs = (
        my_actions.order_by(models.AuditLog.timestamp.desc()).limit(5).all()
    )

    return {
        "personal_queue": my_queue,
        "my_performance": {
            "invoices_processed": my_throughput,
            "team_average_processed": round(team_avg_throughput, 1),
        },
        "recent_activity": [
            {
                "invoice_id": log.entity_id,
                "summary": log.summary,
                "timestamp": log.timestamp,
            }
            for log in my_recent_logs
        ],
    }


# --- LEGACY FUNCTIONS (PRESERVED FOR BACKWARD COMPATIBILITY) ---


def _get_filtered_query_logic(
    db: Session,
    model,
    current_user: models.User,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    for_user_id: Optional[int] = None,
) -> SQLQuery:
    """Core logic for filtering queries by user and date."""
    query = db.query(model)

    # Determine which user to filter for
    user_to_filter = current_user
    if for_user_id and current_user.role.name == "admin":
        target_user = (
            db.query(models.User).filter(models.User.id == for_user_id).first()
        )
        if target_user:
            user_to_filter = target_user
        else:
            # Invalid user ID, return empty results
            return (
                query.filter(models.Invoice.id == -1)
                if hasattr(model, "id")
                else query.filter(False)
            )

    # Apply user permission filters
    if model == models.Invoice:
        query = apply_invoice_permissions(query, user_to_filter, db)
    elif user_to_filter.role.name == "ap_processor":
        # For non-Invoice models, we need to handle permissions differently
        # This is a fallback for models that don't have permission system yet
        return query.filter(False)  # Return empty results for now

    # Apply date filters
    if start_date and hasattr(model, "created_at"):
        query = query.filter(
            model.created_at >= datetime.combine(start_date, datetime.min.time())
        )
    if end_date and hasattr(model, "created_at"):
        query = query.filter(
            model.created_at <= datetime.combine(end_date, datetime.max.time())
        )

    return query


def _map_trace_to_category(step_name: str, review_category: str) -> Optional[str]:
    """Maps a raw match trace step to a clean, user-friendly category name."""
    if review_category == "missing_document":
        return "Missing PO / Non-PO"
    if "Price Match" in step_name:
        return "Price Mismatch"
    if "Quantity Match" in step_name:
        return "Quantity Mismatch"
    if "PO Item Match" in step_name:
        return "Item Not on PO"
    if "Duplicate Check" in step_name:
        return "Potential Duplicate"
    if "Timing Check" in step_name:
        return "Date Mismatch"
    if "Financials" in step_name:
        return "Financials Mismatch"
    return None


def get_dashboard_summary_logic(
    db: Session,
    current_user: models.User,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    for_user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Core logic to get basic dashboard summary."""
    base_query = _get_filtered_query_logic(
        db, models.Invoice, current_user, start_date, end_date, for_user_id
    )

    total_value_exceptions = (
        base_query.filter(
            models.Invoice.status == models.DocumentStatus.needs_review,
            models.Invoice.grand_total.isnot(None),
        )
        .with_entities(func.sum(models.Invoice.grand_total))
        .scalar()
        or 0.0
    )

    # Get kpis for the same period to calculate touchless count
    kpis = get_kpis_logic(db, current_user, start_date, end_date, for_user_id)
    op_eff = kpis.get("operational_efficiency", {})
    touchless_rate = op_eff.get("touchless_invoice_rate_percent", 0)
    total_processed = op_eff.get("total_processed_invoices", 0)
    auto_approved_count = round((touchless_rate / 100) * total_processed)

    summary = {
        "total_invoices": base_query.count(),
        "requires_review": base_query.filter(
            models.Invoice.status == models.DocumentStatus.needs_review
        ).count(),
        "auto_approved": auto_approved_count,
        "pending_match": base_query.filter(
            models.Invoice.status == models.DocumentStatus.matching
        ).count(),
        # POs and GRNs are not date-filtered as they are master data
        "total_pos": db.query(models.PurchaseOrder).count(),
        "total_grns": db.query(models.GoodsReceiptNote).count(),
        "total_value_exceptions": total_value_exceptions,
    }
    return summary


def get_kpis_logic(
    db: Session,
    current_user: models.User,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    for_user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Core logic to calculate advanced KPIs."""
    base_query = _get_filtered_query_logic(
        db, models.Invoice, current_user, start_date, end_date, for_user_id
    )

    # --- Current Period Calculations ---
    discounts_captured = (
        base_query.filter(
            models.Invoice.status == models.DocumentStatus.paid,
            models.Invoice.paid_date <= models.Invoice.discount_due_date,
            models.Invoice.discount_amount.isnot(None),
        )
        .with_entities(func.sum(models.Invoice.discount_amount))
        .scalar()
        or 0.0
    )

    total_processed_invoices = base_query.filter(
        models.Invoice.status.in_(
            [
                models.DocumentStatus.matched,
                models.DocumentStatus.paid,
                models.DocumentStatus.needs_review,
            ]
        )
    ).count()

    invoices_in_review = base_query.filter(
        models.Invoice.status == models.DocumentStatus.needs_review
    ).count()

    touchless_invoices = total_processed_invoices - invoices_in_review
    touchless_rate_percent = (
        (touchless_invoices / total_processed_invoices * 100)
        if total_processed_invoices > 0
        else 0.0
    )

    # Use database-specific current time function
    dialect = engine.dialect.name
    if dialect == "postgresql":
        current_time = func.timezone("UTC", func.now())
    else:  # SQLite
        current_time = func.datetime("now")

    # Calculate average exception handling time
    avg_exception_age_hours_result = (
        base_query.filter(models.Invoice.status == models.DocumentStatus.needs_review)
        .with_entities(
            func.avg(_get_date_diff_hours(current_time, models.Invoice.updated_at))
        )
        .scalar()
    )
    avg_exception_age_hours = avg_exception_age_hours_result or 0

    # --- Previous Period Calculations for Trend ---
    prev_touchless_rate = 0
    if start_date and end_date:
        duration = end_date - start_date
        prev_end_date = start_date - timedelta(days=1)
        prev_start_date = prev_end_date - duration

        prev_base_query = _get_filtered_query_logic(
            db,
            models.Invoice,
            current_user,
            prev_start_date,
            prev_end_date,
            for_user_id,
        )
        prev_total_processed = prev_base_query.filter(
            models.Invoice.status.in_(
                [
                    models.DocumentStatus.matched,
                    models.DocumentStatus.paid,
                    models.DocumentStatus.needs_review,
                ]
            )
        ).count()
        prev_in_review = prev_base_query.filter(
            models.Invoice.status == models.DocumentStatus.needs_review
        ).count()
        prev_touchless = prev_total_processed - prev_in_review
        prev_touchless_rate = (
            (prev_touchless / prev_total_processed * 100)
            if prev_total_processed > 0
            else 0.0
        )

    # --- Vendor Performance (always on the selected period) ---
    vendor_exception_query = (
        base_query.with_entities(
            models.Invoice.vendor_name,
            (
                cast(
                    func.sum(
                        case(
                            (
                                models.Invoice.status
                                == models.DocumentStatus.needs_review,
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    Float,
                )
                / cast(func.count(models.Invoice.id), Float)
                * 100
            ).label("exception_rate"),
        )
        .group_by(models.Invoice.vendor_name)
        .order_by(desc("exception_rate"))
        .limit(5)
        .all()
    )

    vendor_performance = [
        {"vendor": row[0], "exception_rate": float(row[1])}
        for row in vendor_exception_query
    ]

    return {
        "operational_efficiency": {
            "total_processed_invoices": total_processed_invoices,
            "invoices_in_review_queue": invoices_in_review,
            "touchless_invoice_rate_percent": round(touchless_rate_percent, 1),
            "touchless_rate_change": round(
                touchless_rate_percent - prev_touchless_rate, 1
            ),
            "avg_exception_handling_time_hours": round(avg_exception_age_hours, 1),
        },
        "financial_optimization": {
            "discounts_captured": f"${discounts_captured:,.2f}",
        },
        "vendor_performance": vendor_performance,
    }


def get_exception_summary_logic(
    db: Session,
    current_user: models.User,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    for_user_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Core logic to get exception summary by parsing match traces."""
    base_query = _get_filtered_query_logic(
        db, models.Invoice, current_user, start_date, end_date, for_user_id
    )

    # Get invoices that need review and have match traces
    invoices_with_traces = base_query.filter(
        models.Invoice.status == models.DocumentStatus.needs_review,
        models.Invoice.match_trace.isnot(None),
    ).all()

    # Count exceptions by category
    exception_counts = Counter()

    for invoice in invoices_with_traces:
        if invoice.match_trace:
            for step in invoice.match_trace:
                step_name = step.get("step_name", "")
                review_category = step.get("review_category", "")

                mapped_category = _map_trace_to_category(step_name, review_category)
                if mapped_category:
                    exception_counts[mapped_category] += 1

    # Convert to list of dictionaries
    return [
        {"category": category, "count": count}
        for category, count in exception_counts.most_common()
    ]


def get_cost_roi_metrics_logic(
    db: Session,
    current_user: models.User,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    for_user_id: Optional[int] = None,
) -> Dict[str, float]:
    """Core logic to calculate cost and ROI metrics."""
    base_query = _get_filtered_query_logic(
        db, models.Invoice, current_user, start_date, end_date, for_user_id
    )

    # Get KPIs for touchless rate
    kpis = get_kpis_logic(db, current_user, start_date, end_date, for_user_id)
    touchless_rate = kpis["operational_efficiency"]["touchless_invoice_rate_percent"]
    total_processed = kpis["operational_efficiency"]["total_processed_invoices"]

    # Cost assumptions (these would be configurable in a real system)
    cost_per_manual_invoice = 25.0  # Estimated cost to manually process one invoice
    cost_per_touchless_invoice = 2.0  # Estimated cost for automated processing

    # Calculate savings
    touchless_invoices = round((touchless_rate / 100) * total_processed)
    manual_invoices = total_processed - touchless_invoices

    traditional_cost = total_processed * cost_per_manual_invoice
    actual_cost = (touchless_invoices * cost_per_touchless_invoice) + (
        manual_invoices * cost_per_manual_invoice
    )

    cost_savings = traditional_cost - actual_cost
    roi_percentage = (cost_savings / actual_cost * 100) if actual_cost > 0 else 0

    return {
        "cost_savings": cost_savings,
        "roi_percentage": roi_percentage,
        "touchless_invoices": touchless_invoices,
        "manual_invoices": manual_invoices,
    }


def get_payment_forecast_logic(
    db: Session, current_user: models.User, for_user_id: Optional[int] = None
) -> Dict[str, float]:
    """Core logic to get payment forecast."""
    base_query = _get_filtered_query_logic(
        db, models.Invoice, current_user, None, None, for_user_id
    )

    # Get invoices that are matched or pending payment
    payable_invoices = base_query.filter(
        models.Invoice.status.in_(
            [
                models.DocumentStatus.matched,
                models.DocumentStatus.pending_payment,
                models.DocumentStatus.qa_approval,
            ]
        ),
        models.Invoice.due_date.isnot(None),
        models.Invoice.grand_total.isnot(None),
    ).all()

    # Calculate payment forecasts
    today = date.today()
    forecasts = {
        "next_7_days": 0.0,
        "next_30_days": 0.0,
        "next_90_days": 0.0,
        "overdue": 0.0,
    }

    for invoice in payable_invoices:
        if invoice.due_date and invoice.grand_total:
            days_until_due = (invoice.due_date - today).days

            if days_until_due < 0:
                forecasts["overdue"] += invoice.grand_total
            elif days_until_due <= 7:
                forecasts["next_7_days"] += invoice.grand_total
            elif days_until_due <= 30:
                forecasts["next_30_days"] += invoice.grand_total
            elif days_until_due <= 90:
                forecasts["next_90_days"] += invoice.grand_total

    return forecasts


def get_action_queue_logic(
    db: Session, current_user: models.User, for_user_id: Optional[int] = None
) -> List[models.Invoice]:
    """Core logic to get action queue."""
    base_query = _get_filtered_query_logic(
        db, models.Invoice, current_user, None, None, for_user_id
    )

    # Get invoices that need review, ordered by oldest first
    return (
        base_query.filter(models.Invoice.status == models.DocumentStatus.needs_review)
        .order_by(models.Invoice.updated_at.asc())
        .limit(5)
        .all()
    )

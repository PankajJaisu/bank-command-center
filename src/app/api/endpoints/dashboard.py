# src/app/api/endpoints/dashboard.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date, timedelta
from typing import Optional, List, Dict, Any

from app.api.dependencies import get_db, get_current_user
from app.db import models, schemas
from app.services import dashboard_service

router = APIRouter()


@router.get("/data", summary="Get Role-Based Dashboard Data")
def get_dashboard_data(
    db: Session = Depends(get_db),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    This single endpoint provides a comprehensive set of dashboard metrics
    tailored to the user's role (Admin vs. AP Processor).
    """
    # Default to a 30-day range if not provided
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    if current_user.role.name == "admin":
        return dashboard_service.get_admin_dashboard_data(db, start_date, end_date)
    else:  # 'ap_processor'
        return dashboard_service.get_processor_dashboard_data(
            db, current_user, start_date, end_date
        )


# --- LEGACY ENDPOINTS (PRESERVED FOR BACKWARD COMPATIBILITY) ---


@router.get("/summary", summary="Get Basic Summary")
def get_dashboard_summary(
    db: Session = Depends(get_db),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: models.User = Depends(get_current_user),
    for_user_id: Optional[int] = Query(None),
):
    """Provides high-level KPI numbers for the main dashboard view, filtered by date and user."""
    return dashboard_service.get_dashboard_summary_logic(
        db, current_user, start_date, end_date, for_user_id
    )


@router.get("/kpis", summary="Get Advanced Business KPIs")
def get_advanced_kpis(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    for_user_id: Optional[int] = Query(None),
):
    """Provides a comprehensive set of Key Performance Indicators, filtered by date and user."""
    return dashboard_service.get_kpis_logic(
        db, current_user, start_date, end_date, for_user_id
    )


@router.get("/exceptions", summary="Get Exception Summary")
def get_exception_summary(
    db: Session = Depends(get_db),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: models.User = Depends(get_current_user),
    for_user_id: Optional[int] = Query(None),
):
    """
    Provides a detailed summary of invoice exceptions by parsing the match trace
    for a more granular chart, filterable by date.
    """
    return dashboard_service.get_exception_summary_logic(
        db, current_user, start_date, end_date, for_user_id
    )


@router.get("/cost-roi", summary="Get Cost and ROI Metrics")
def get_cost_roi_metrics(
    db: Session = Depends(get_db),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: models.User = Depends(get_current_user),
    for_user_id: Optional[int] = Query(None),
):
    """Calculates estimated cost savings and ROI for the AP automation, filterable by date."""
    return dashboard_service.get_cost_roi_metrics_logic(
        db, current_user, start_date, end_date, for_user_id
    )


@router.get("/payment-forecast", summary="Get Payment Forecast")
def get_payment_forecast(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    for_user_id: Optional[int] = Query(None),
):
    """
    Provides a forecast of upcoming payments by time periods.
    """
    return dashboard_service.get_payment_forecast_logic(db, current_user, for_user_id)


@router.get("/action-queue", response_model=List[schemas.InvoiceSummary])
def get_action_queue(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    for_user_id: Optional[int] = Query(None),
):
    """
    Retrieves the top 5 invoices that require immediate attention,
    prioritized by the oldest update time in 'needs_review' status.
    """
    return dashboard_service.get_action_queue_logic(db, current_user, for_user_id)

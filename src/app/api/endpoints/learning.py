# src/app/api/endpoints/learning.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.api.dependencies import get_db, get_current_user
from app.db import models, schemas

router = APIRouter()


# New schema for the API response
class AggregatedHeuristicResponse(schemas.LearnedHeuristicBase):
    id: str  # A unique ID for the frontend key, e.g., "VendorName-ExceptionType"
    confidence_score: float
    trigger_count: int
    potential_impact: int  # Represents how many times this pattern has been observed

    class Config:
        from_attributes = True


@router.get(
    "/heuristics",
    response_model=List[AggregatedHeuristicResponse],
    summary="Get Aggregated Learned Heuristics",
)
def get_aggregated_heuristics(
    vendor_name: Optional[str] = None, db: Session = Depends(get_db)
):
    """
    Retrieves and aggregates learned heuristics to provide clear, actionable
    suggestions for automation. It groups similar heuristics (same vendor and exception type)
    and presents the most relevant one.
    """
    query = (
        db.query(
            models.LearnedHeuristic.vendor_name,
            models.LearnedHeuristic.exception_type,
            func.max(models.LearnedHeuristic.confidence_score).label("max_confidence"),
            func.sum(models.LearnedHeuristic.trigger_count).label("total_triggers"),
        )
        .filter(models.LearnedHeuristic.is_dismissed == False)
        .group_by(
            models.LearnedHeuristic.vendor_name, models.LearnedHeuristic.exception_type
        )
    )

    if vendor_name:
        query = query.filter(
            models.LearnedHeuristic.vendor_name.ilike(f"%{vendor_name}%")
        )

    aggregated_results = query.order_by(
        func.max(models.LearnedHeuristic.confidence_score).desc()
    ).all()

    response_list = []
    for vendor, exc_type, confidence, triggers in aggregated_results:
        # For each group, find the specific heuristic with the highest confidence
        # to get its learned_condition. This is more accurate than trying to average conditions.
        representative_heuristic = (
            db.query(models.LearnedHeuristic)
            .filter_by(vendor_name=vendor, exception_type=exc_type)
            .filter(models.LearnedHeuristic.is_dismissed == False)
            .order_by(models.LearnedHeuristic.confidence_score.desc())
            .first()
        )

        if representative_heuristic:
            response_list.append(
                AggregatedHeuristicResponse(
                    id=f"{vendor}-{exc_type}",
                    vendor_name=vendor,
                    exception_type=exc_type,
                    learned_condition=representative_heuristic.learned_condition,
                    resolution_action=representative_heuristic.resolution_action,
                    confidence_score=confidence,
                    trigger_count=triggers,
                    potential_impact=triggers,  # The potential impact is the number of times it has happened
                )
            )

    return response_list


# --- START: NEW SCHEMAS FOR API RESPONSE ---
class UserActionPatternResponse(schemas.BaseModel):
    id: int
    pattern_type: str
    entity_name: str
    count: int
    last_detected: datetime

    class Config:
        from_attributes = True


class LearnedPreferenceResponse(schemas.BaseModel):
    id: int
    preference_type: str
    context_key: str
    preference_value: str

    class Config:
        from_attributes = True


# --- START: NEW SCHEMA FOR EVIDENCE RESPONSE ---
class HeuristicEvidenceResponse(schemas.BaseModel):
    invoice_id: str
    approval_date: datetime
    user: str

    class Config:
        from_attributes = True


# --- END: NEW SCHEMA FOR EVIDENCE RESPONSE ---
# --- END: NEW SCHEMAS FOR API RESPONSE ---

# --- START: NEW ENDPOINTS FOR REVAMPED INSIGHTS PAGE ---


@router.get("/process-hotspots", response_model=List[UserActionPatternResponse])
def get_process_hotspots(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """
    Retrieves significant, aggregated user action patterns that indicate
    process inefficiencies (e.g., 'hotspots').
    """
    # In a real multi-user app, you might filter by user or team.
    # For now, we show system-wide patterns.
    return (
        db.query(models.UserActionPattern)
        .order_by(models.UserActionPattern.count.desc())
        .all()
    )


@router.get("/my-preferences", response_model=List[LearnedPreferenceResponse])
def get_my_preferences(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """
    Retrieves all preferences explicitly taught to the AI by the current user.
    """
    # In a real system, you'd filter by current_user.id. For demo, we show all.
    return db.query(models.LearnedPreference).all()


@router.delete(
    "/my-preferences/{preference_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_my_preference(
    preference_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Deletes a learned preference for the current user.
    """
    # Add user_id filter in a real system for security
    preference = db.query(models.LearnedPreference).filter_by(id=preference_id).first()
    if not preference:
        raise HTTPException(status_code=404, detail="Preference not found.")

    db.delete(preference)
    db.commit()
    return


# --- START: NEW ENDPOINTS FOR DISMISS/EVIDENCE ---
@router.post(
    "/heuristics/{heuristic_id}/dismiss", status_code=status.HTTP_204_NO_CONTENT
)
def dismiss_heuristic(
    heuristic_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Marks a learned heuristic as dismissed by the user."""
    heuristic = db.query(models.LearnedHeuristic).filter_by(id=heuristic_id).first()
    if not heuristic:
        raise HTTPException(status_code=404, detail="Heuristic not found.")

    heuristic.is_dismissed = True
    db.commit()
    return


@router.get(
    "/heuristics/{heuristic_id}/evidence",
    response_model=List[HeuristicEvidenceResponse],
)
def get_heuristic_evidence(
    heuristic_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Finds the specific audit log entries (i.e., the evidence) that
    led to the creation of a given heuristic.
    """
    heuristic = db.query(models.LearnedHeuristic).filter_by(id=heuristic_id).first()
    if not heuristic:
        raise HTTPException(status_code=404, detail="Heuristic not found.")

    # This is a complex query. We are looking for audit logs that represent a manual
    # approval ('needs_review' -> 'matched') on an invoice that had the specific
    # type of failure the heuristic is for (e.g., PriceMismatchException).
    evidence_logs = (
        db.query(
            models.Invoice.invoice_id,
            models.AuditLog.timestamp.label("approval_date"),
            models.AuditLog.user,
        )
        .join(models.Invoice, models.AuditLog.invoice_db_id == models.Invoice.id)
        .filter(
            and_(
                models.AuditLog.action == "Status Changed",
                models.AuditLog.details["from"].as_string() == "needs_review",
                models.AuditLog.details["to"].as_string() == "matched",
                models.Invoice.vendor_name == heuristic.vendor_name,
                # This part is tricky; we check if the match_trace contains the exception type
                # Note: This is a simplified check. A more robust way might involve JSON functions
                # specific to your DB (e.g., JSON_EXTRACT in MySQL/SQLite, ->> in PostgreSQL).
                # For this example, we'll assume the review_category is set correctly.
                models.Invoice.review_category.ilike(
                    f"%{heuristic.exception_type.split('Exception')[0]}%"
                ),
            )
        )
        .order_by(models.AuditLog.timestamp.desc())
        .limit(20)
        .all()
    )

    return evidence_logs


# --- END: NEW ENDPOINTS FOR DISMISS/EVIDENCE ---
# --- END: NEW ENDPOINTS FOR REVAMPED INSIGHTS PAGE ---

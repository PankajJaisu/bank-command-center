# src/app/api/endpoints/ai_suggestions.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from pydantic import BaseModel

from app.api.dependencies import get_db
from app.db import models
from app.services.ai_suggestion_service import AISuggestionService
from app.utils.email_service import send_policy_email
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


class EmailRequest(BaseModel):
    customer_id: int
    action_type: str
    custom_message: Optional[str] = None
    recipient_email: Optional[str] = None


class SuggestionRequest(BaseModel):
    customer_id: int


@router.get("/suggestions/{customer_id}")
def get_customer_suggestion(
    customer_id: int,
    db: Session = Depends(get_db),
):
    """
    Generate AI-powered suggestions for a specific customer based on their
    contract notes, customer details, and applicable rules.
    """
    try:
        suggestion_service = AISuggestionService(db)
        suggestion = suggestion_service.generate_customer_suggestion(customer_id)
        
        if "error" in suggestion:
            raise HTTPException(status_code=404, detail=suggestion["error"])
        
        return suggestion
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting customer suggestion for {customer_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate suggestion: {str(e)}")


@router.post("/email/generate")
def generate_email_content(
    request: EmailRequest,
    db: Session = Depends(get_db),
):
    """
    Generate AI-powered email content for a specific customer and action type.
    """
    try:
        suggestion_service = AISuggestionService(db)
        email_content = suggestion_service.generate_email_content(
            customer_id=request.customer_id,
            action_type=request.action_type,
            custom_message=request.custom_message
        )
        
        if "error" in email_content:
            raise HTTPException(status_code=404, detail=email_content["error"])
        
        return email_content
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating email content: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate email content: {str(e)}")


@router.post("/email/send")
async def send_suggestion_email(
    request: EmailRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Send AI-generated email to customer based on suggestion.
    """
    try:
        # Get customer data
        customer = db.query(models.Customer).filter(
            models.Customer.id == request.customer_id
        ).first()
        
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        # Use provided email or customer's email
        recipient_email = request.recipient_email or customer.email
        if not recipient_email:
            raise HTTPException(status_code=400, detail="No email address available for customer")
        
        # Generate email content
        suggestion_service = AISuggestionService(db)
        email_data = suggestion_service.generate_email_content(
            customer_id=request.customer_id,
            action_type=request.action_type,
            custom_message=request.custom_message
        )
        
        if "error" in email_data:
            raise HTTPException(status_code=400, detail=email_data["error"])
        
        email_content = email_data["email_content"]
        
        # Send email in background
        background_tasks.add_task(
            send_policy_email,
            to_email=recipient_email,
            subject=email_content["subject"],
            body=email_content["body"],
            customer_name=customer.name
        )
        
        # Log the action
        logger.info(f"Email queued for customer {customer.customer_no} ({customer.name}) to {recipient_email}")
        
        return {
            "message": "Email queued for sending",
            "customer_id": request.customer_id,
            "recipient_email": recipient_email,
            "action_type": request.action_type,
            "email_subject": email_content["subject"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending suggestion email: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")


@router.get("/suggestions/batch/{risk_level}")
def get_batch_suggestions(
    risk_level: str,
    limit: int = 10,
    db: Session = Depends(get_db),
):
    """
    Generate suggestions for multiple customers based on risk level.
    Useful for Resolution Workbench to get suggestions for medium/high severity cases.
    """
    try:
        # Validate risk level
        if risk_level not in ["red", "amber", "yellow"]:
            raise HTTPException(status_code=400, detail="Invalid risk level. Must be 'red', 'amber', or 'yellow'")
        
        # Get customers with specified risk level
        customers = db.query(models.Customer).filter(
            models.Customer.cbs_risk_level == risk_level
        ).limit(limit).all()
        
        if not customers:
            return {"message": f"No customers found with risk level: {risk_level}", "suggestions": []}
        
        # Generate suggestions for each customer
        suggestion_service = AISuggestionService(db)
        suggestions = []
        
        for customer in customers:
            try:
                suggestion = suggestion_service.generate_customer_suggestion(customer.id)
                if "error" not in suggestion:
                    suggestions.append(suggestion)
            except Exception as e:
                logger.warning(f"Failed to generate suggestion for customer {customer.id}: {str(e)}")
                continue
        
        return {
            "risk_level": risk_level,
            "total_customers": len(customers),
            "successful_suggestions": len(suggestions),
            "suggestions": suggestions
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating batch suggestions for risk level {risk_level}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate batch suggestions: {str(e)}")


@router.get("/customer/{customer_id}/contract-summary")
def get_customer_contract_summary(
    customer_id: int,
    db: Session = Depends(get_db),
):
    """
    Get a summary of customer's contract note and details for AI suggestion context.
    """
    try:
        # Get customer
        customer = db.query(models.Customer).filter(
            models.Customer.id == customer_id
        ).first()
        
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        # Get contract note
        contract_note = db.query(models.ContractNote).filter(
            models.ContractNote.customer_id == customer_id
        ).first()
        
        # Get applicable automation rules count
        suggestion_service = AISuggestionService(db)
        applicable_rules = suggestion_service._get_applicable_rules(customer)
        
        summary = {
            "customer": {
                "id": customer.id,
                "customer_no": customer.customer_no,
                "name": customer.name,
                "cibil_score": customer.cibil_score,
                "risk_level": customer.cbs_risk_level,
                "outstanding_amount": customer.cbs_outstanding_amount,
                "pending_amount": customer.pending_amount,
                "emi_pending": customer.emi_pending,
                "days_overdue": customer.days_overdue,
                "segment": customer.segment,
                "email": customer.email,
                "phone": customer.phone
            },
            "contract_note": None,
            "applicable_rules_count": len(applicable_rules),
            "has_contract_note": contract_note is not None
        }
        
        if contract_note:
            summary["contract_note"] = {
                "id": contract_note.id,
                "emi_amount": contract_note.emi_amount,
                "due_day": contract_note.due_day,
                "late_fee_percent": contract_note.late_fee_percent,
                "loan_amount": contract_note.loan_amount,
                "tenure_months": contract_note.tenure_months,
                "interest_rate": contract_note.interest_rate,
                "filename": contract_note.filename
            }
        
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting customer contract summary for {customer_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get customer summary: {str(e)}")

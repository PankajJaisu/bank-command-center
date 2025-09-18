# src/app/api/endpoints/collection.py
from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, and_
from typing import List, Optional, Dict, Any
from datetime import datetime, date

from app.api.dependencies import get_db, get_current_user
from app.db import models, schemas
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/customers", response_model=List[schemas.Customer])
def get_customers(
    limit: int = QueryParam(50, le=100),
    offset: int = QueryParam(0, ge=0),
    search: Optional[str] = None,
    risk_level: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get customers with filtering and pagination"""
    query = db.query(models.Customer).options(joinedload(models.Customer.contract_note))
    
    if search:
        query = query.filter(
            models.Customer.name.ilike(f"%{search}%") |
            models.Customer.customer_no.ilike(f"%{search}%") |
            models.Customer.email.ilike(f"%{search}%")
        )
    
    if risk_level:
        query = query.filter(models.Customer.cbs_risk_level == risk_level)
    
    customers = query.order_by(models.Customer.customer_no).offset(offset).limit(limit).all()
    return customers


@router.delete("/customers/{customer_id}")
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Delete a customer and all related data (loans, alerts)"""
    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    try:
        # Delete related loans first (foreign key constraint)
        db.query(models.Loan).filter(models.Loan.customer_id == customer_id).delete()
        
        # Delete related data integrity alerts
        db.query(models.DataIntegrityAlert).filter(models.DataIntegrityAlert.customer_id == customer_id).delete()
        
        # Delete the customer
        db.delete(customer)
        db.commit()
        
        return {"message": f"Customer {customer.customer_no} and all related data deleted successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete customer: {str(e)}")


@router.get("/customers/{customer_id}", response_model=schemas.Customer)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get customer details by ID"""
    customer = (
        db.query(models.Customer)
        .options(joinedload(models.Customer.contract_note))
        .options(joinedload(models.Customer.loans))
        .filter(models.Customer.id == customer_id)
        .first()
    )
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return customer


@router.get("/customers/{customer_id}/contract-terms")
def get_customer_contract_terms(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get contract terms for a customer to display in the profile"""
    customer = (
        db.query(models.Customer)
        .options(joinedload(models.Customer.contract_note))
        .filter(models.Customer.id == customer_id)
        .first()
    )
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    contract_terms = {}
    if customer.contract_note:
        contract_terms = {
            "emi_amount": customer.contract_note.contract_emi_amount,
            "due_day": customer.contract_note.contract_due_day,
            "late_fee_percent": customer.contract_note.contract_late_fee_percent,
            "default_clause": customer.contract_note.contract_default_clause,
            "governing_law": customer.contract_note.contract_governing_law,
            "interest_rate": customer.contract_note.contract_interest_rate,
            "loan_amount": customer.contract_note.contract_loan_amount,
            "tenure_months": customer.contract_note.contract_tenure_months,
        }
    
    return {
        "customer_id": customer_id,
        "customer_no": customer.customer_no,
        "customer_name": customer.name,
        "contract_terms": contract_terms,
        "cbs_data": {
            "emi_amount": customer.cbs_emi_amount,
            "due_day": customer.cbs_due_day,
            "outstanding_amount": customer.cbs_outstanding_amount,
            "risk_level": customer.cbs_risk_level,
            "last_payment_date": customer.cbs_last_payment_date,
        }
    }


@router.get("/data-integrity-alerts", response_model=List[schemas.DataIntegrityAlert])
def get_data_integrity_alerts(
    limit: int = QueryParam(50, le=100),
    offset: int = QueryParam(0, ge=0),
    severity: Optional[str] = None,
    resolved: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get data integrity alerts for the dashboard"""
    query = db.query(models.DataIntegrityAlert).options(joinedload(models.DataIntegrityAlert.customer))
    
    if severity:
        query = query.filter(models.DataIntegrityAlert.severity == severity)
    
    if resolved is not None:
        query = query.filter(models.DataIntegrityAlert.is_resolved == resolved)
    
    alerts = query.order_by(desc(models.DataIntegrityAlert.created_at)).offset(offset).limit(limit).all()
    return alerts


@router.put("/data-integrity-alerts/{alert_id}/resolve")
def resolve_data_integrity_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Mark a data integrity alert as resolved"""
    alert = db.query(models.DataIntegrityAlert).filter(models.DataIntegrityAlert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.is_resolved = True
    alert.resolved_by = current_user.email
    alert.resolved_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Alert marked as resolved", "alert_id": alert_id}


@router.get("/dashboard/summary")
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get dashboard summary data including data integrity alerts"""
    
    # Data integrity alerts summary
    total_alerts = db.query(models.DataIntegrityAlert).filter(
        models.DataIntegrityAlert.is_resolved == False
    ).count()
    
    high_priority_alerts = db.query(models.DataIntegrityAlert).filter(
        and_(
            models.DataIntegrityAlert.is_resolved == False,
            models.DataIntegrityAlert.severity == "high"
        )
    ).count()
    
    # Customer risk summary
    risk_summary = (
        db.query(
            models.Customer.cbs_risk_level,
            func.count(models.Customer.id).label("count")
        )
        .group_by(models.Customer.cbs_risk_level)
        .all()
    )
    
    # Contract notes processed
    contract_notes_count = db.query(models.ContractNote).count()
    
    # Recent alerts (last 5)
    recent_alerts = (
        db.query(models.DataIntegrityAlert)
        .options(joinedload(models.DataIntegrityAlert.customer))
        .filter(models.DataIntegrityAlert.is_resolved == False)
        .order_by(desc(models.DataIntegrityAlert.created_at))
        .limit(5)
        .all()
    )
    
    return {
        "data_integrity": {
            "total_unresolved_alerts": total_alerts,
            "high_priority_alerts": high_priority_alerts,
            "recent_alerts": [
                {
                    "id": alert.id,
                    "type": alert.alert_type,
                    "title": alert.title,
                    "customer_name": alert.customer.name if alert.customer else "Unknown",
                    "severity": alert.severity,
                    "created_at": alert.created_at,
                }
                for alert in recent_alerts
            ]
        },
        "customer_risk": {
            risk.cbs_risk_level or "UNKNOWN": risk.count 
            for risk in risk_summary
        },
        "contract_processing": {
            "total_contracts_processed": contract_notes_count,
        }
    }


@router.get("/contract-notes", response_model=List[schemas.ContractNote])
def get_contract_notes(
    limit: int = QueryParam(50, le=100),
    offset: int = QueryParam(0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get processed contract notes"""
    contract_notes = (
        db.query(models.ContractNote)
        .order_by(desc(models.ContractNote.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )
    return contract_notes


@router.get("/contract-notes/{contract_id}", response_model=schemas.ContractNote)
def get_contract_note(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get contract note details"""
    contract_note = db.query(models.ContractNote).filter(models.ContractNote.id == contract_id).first()
    
    if not contract_note:
        raise HTTPException(status_code=404, detail="Contract note not found")
    
    return contract_note


@router.get("/loans", response_model=List[schemas.Loan])
def get_loans(
    limit: int = QueryParam(50, le=100),
    offset: int = QueryParam(0, ge=0),
    status: Optional[str] = None,
    customer_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get loans with filtering"""
    query = db.query(models.Loan).options(joinedload(models.Loan.customer))
    
    if status:
        query = query.filter(models.Loan.status == status)
    
    if customer_id:
        query = query.filter(models.Loan.customer_id == customer_id)
    
    loans = query.order_by(desc(models.Loan.created_at)).offset(offset).limit(limit).all()
    return loans


@router.get("/kpis")
def get_collection_kpis(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get collection KPIs for dashboard"""
    
    # Calculate total receivables due
    total_receivables = db.query(func.sum(models.Customer.cbs_outstanding_amount)).scalar() or 0
    
    # Calculate accounts overdue (customers with risk level 'red' or 'amber')
    accounts_overdue = db.query(models.Customer).filter(
        models.Customer.cbs_risk_level.in_(['red', 'amber'])
    ).count()
    
    # Calculate delinquency rate
    total_customers = db.query(models.Customer).count()
    delinquency_rate = (accounts_overdue / total_customers * 100) if total_customers > 0 else 0
    
    # Calculate amount overdue (sum of outstanding amounts for red/amber customers)
    amount_overdue = db.query(func.sum(models.Customer.cbs_outstanding_amount)).filter(
        models.Customer.cbs_risk_level.in_(['red', 'amber'])
    ).scalar() or 0
    
    # For simplicity, assume 75% is collected (in a real scenario, this would come from payment data)
    total_collected = total_receivables * 0.75
    collected_cleared = total_collected * 0.8
    collected_in_transit = total_collected * 0.2
    
    return {
        "totalReceivablesDue": total_receivables,
        "totalCollected": total_collected,
        "delinquencyRate": round(delinquency_rate, 1),
        "totalAmountOverdue": amount_overdue,
        "accountsOverdue": accounts_overdue,
        "collectedCleared": collected_cleared,
        "collectedInTransit": collected_in_transit,
    }


@router.get("/metrics")
def get_collection_metrics(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get collection metrics for dashboard analytics"""
    
    # Get DDD bucket analysis - group by risk level as a proxy for DPD buckets
    risk_distribution = (
        db.query(
            models.Customer.cbs_risk_level,
            func.count(models.Customer.id).label("count"),
            func.sum(models.Customer.cbs_outstanding_amount).label("amount")
        )
        .group_by(models.Customer.cbs_risk_level)
        .all()
    )
    
    # Map risk levels to DPD buckets
    ddd_buckets = []
    risk_mapping = {
        "yellow": {"bucket": "0-30", "sort": 1},
        "amber": {"bucket": "31-60", "sort": 2}, 
        "red": {"bucket": "90+", "sort": 4}
    }
    
    for risk_level, count, amount in risk_distribution:
        if risk_level in risk_mapping:
            ddd_buckets.append({
                "bucket": risk_mapping[risk_level]["bucket"],
                "accounts": count,
                "amount": round((amount or 0) / 100000, 1),  # Convert to lakhs
                "sort": risk_mapping[risk_level]["sort"]
            })
    
    # Add missing bucket if needed
    if not any(b["bucket"] == "61-90" for b in ddd_buckets):
        ddd_buckets.append({"bucket": "61-90", "accounts": 0, "amount": 0, "sort": 3})
    
    # Sort by DPD bucket order
    ddd_buckets.sort(key=lambda x: x["sort"])
    
    # Recovery performance by loan type (simulate with customer count per risk level)
    recovery_performance = []
    total_customers = db.query(models.Customer).count()
    
    # Calculate accounts overdue for delinquency trend
    accounts_overdue = db.query(models.Customer).filter(
        models.Customer.cbs_risk_level.in_(['red', 'amber'])
    ).count()
    
    for risk_level, count, _ in risk_distribution:
        recovery_rate = {"yellow": 85.2, "amber": 72.1, "red": 45.8}.get(risk_level, 60.0)
        loan_type = {"yellow": "Personal Loans", "amber": "Auto Loans", "red": "Home Loans"}.get(risk_level, "Education Loans")
        recovery_performance.append({
            "loanType": loan_type,
            "recoveryRate": recovery_rate
        })
    
    return {
        "agingBuckets": {
            "current": 125000,
            "days1_30": sum(b["amount"] * 1000 for b in ddd_buckets if b["bucket"] == "0-30"),
            "days31_60": sum(b["amount"] * 1000 for b in ddd_buckets if b["bucket"] == "31-60"),
            "days61_90": sum(b["amount"] * 1000 for b in ddd_buckets if b["bucket"] == "61-90"),
            "days90Plus": sum(b["amount"] * 1000 for b in ddd_buckets if b["bucket"] == "90+")
        },
        "collectionFunnel": {
            "totalDue": int(db.query(func.sum(models.Customer.cbs_outstanding_amount)).scalar() or 0),
            "paidByCustomer": int((db.query(func.sum(models.Customer.cbs_outstanding_amount)).scalar() or 0) * 0.75),
            "clearedByBank": int((db.query(func.sum(models.Customer.cbs_outstanding_amount)).scalar() or 0) * 0.65)
        },
        "delinquencyTrend": [
            {"month": "Feb", "rate": 22.1},
            {"month": "Mar", "rate": 24.3}, 
            {"month": "Apr", "rate": 23.8},
            {"month": "May", "rate": 25.2},
            {"month": "Jun", "rate": 26.1},
            {"month": "Jul", "rate": round((accounts_overdue / total_customers * 100) if total_customers > 0 else 0, 1)}
        ]
    }


@router.delete("/clear-all-data")
def clear_all_customer_data(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Clear all customer-related data from the database"""
    
    try:
        # Count records before deletion
        customer_count = db.query(models.Customer).count()
        loan_count = db.query(models.Loan).count()
        contract_count = db.query(models.ContractNote).count()
        alert_count = db.query(models.DataIntegrityAlert).count()
        
        # Delete in order to respect foreign key constraints
        # 1. Delete data integrity alerts first (they reference customers)
        deleted_alerts = db.query(models.DataIntegrityAlert).delete()
        
        # 2. Delete loans (they reference customers)
        deleted_loans = db.query(models.Loan).delete()
        
        # 3. Delete customers (they reference contract notes)
        deleted_customers = db.query(models.Customer).delete()
        
        # 4. Delete contract notes (no foreign key dependencies)
        deleted_contracts = db.query(models.ContractNote).delete()
        
        # Commit all deletions
        db.commit()
        
        return {
            "message": "All customer data cleared successfully",
            "deleted_counts": {
                "customers": deleted_customers,
                "loans": deleted_loans,
                "contract_notes": deleted_contracts,
                "data_integrity_alerts": deleted_alerts
            },
            "total_deleted": deleted_customers + deleted_loans + deleted_contracts + deleted_alerts
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to clear customer data: {str(e)}")


@router.get("/loan-accounts", response_model=List[Dict[str, Any]])
def get_loan_accounts_with_contracts(
    limit: int = QueryParam(50, le=100),
    offset: int = QueryParam(0, ge=0),
    status: Optional[str] = None,
    risk_level: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get loan accounts with contract information for collection cell table"""
    
    # Join customers, loans, and contract notes
    query = (
        db.query(
            models.Customer.id.label("customer_id"),
            models.Customer.customer_no,
            models.Customer.name.label("customer_name"),
            models.Customer.cbs_risk_level,
            models.Customer.cbs_emi_amount,
            models.Customer.cbs_due_day,
            models.Customer.cbs_outstanding_amount,
            models.Customer.cbs_last_payment_date,
            models.Customer.pending_amount,  # Add pending_amount field
            models.Customer.emi_pending,  # Add emi_pending field
            models.Customer.segment,  # Add segment field
            models.Customer.pendency,  # Add pendency field for processed status
            models.Loan.loan_id,
            models.Loan.emi_amount,
            models.Loan.outstanding_amount,
            models.Loan.last_payment_date,
            models.Loan.next_due_date,
            models.ContractNote.id.label("contract_note_id"),
            models.ContractNote.contract_emi_amount,
            models.ContractNote.contract_due_day,
            models.ContractNote.contract_late_fee_percent,
            models.ContractNote.filename.label("contract_filename"),
            models.ContractNote.file_path.label("contract_file_path"),
            models.Customer.cibil_score,
        )
        .outerjoin(models.Loan, models.Customer.id == models.Loan.customer_id)
        .outerjoin(models.ContractNote, models.Customer.contract_note_id == models.ContractNote.id)
    )
    
    if risk_level:
        query = query.filter(models.Customer.cbs_risk_level == risk_level.upper())
    
    if status:
        query = query.filter(models.Loan.status == status)
    
    results = query.order_by(models.Customer.customer_no).offset(offset).limit(limit).all()
    
    # Format results for frontend
    loan_accounts = []
    for i, result in enumerate(results):
        # Calculate days overdue (mock calculation)
        days_overdue = 0
        if result.next_due_date:
            from datetime import date
            today = date.today()
            if result.next_due_date < today:
                days_overdue = (today - result.next_due_date).days
        
        loan_accounts.append({
            "id": i + 1,  # Mock ID for frontend
            "customerId": result.customer_id,
            "customerNo": result.customer_no,
            "customerName": result.customer_name,
            "loanId": result.loan_id or f"LN-{result.customer_id:05d}",
            "nextPaymentDueDate": result.next_due_date.isoformat() if result.next_due_date else "2025-08-05",
            "amountDue": float(result.emi_amount) if result.emi_amount is not None and result.emi_amount > 0 else (float(result.outstanding_amount * 0.1) if result.outstanding_amount is not None and result.outstanding_amount > 0 else 1500.0),
            "pendingAmount": float(result.pending_amount) if result.pending_amount is not None else None,  # Add pending amount
            "emi_pending": int(result.emi_pending) if result.emi_pending is not None else 0,  # Add EMI pending
            "segment": result.segment if result.segment is not None else "Retail",  # Add segment
            "daysOverdue": days_overdue,
            "lastPaymentDate": result.last_payment_date.isoformat() if result.last_payment_date else "2025-07-05",
            "collectionStatus": "pending",  # Mock status
            "reconciliationStatus": "cleared",  # Mock status
            "lastContactNote": None,
            "totalOutstanding": float(result.outstanding_amount) if result.outstanding_amount is not None else 35000.0,
            "principalBalance": float(result.outstanding_amount * 0.9) if result.outstanding_amount is not None else 32000.0,  # Mock calculation
            "interestAccrued": float(result.outstanding_amount * 0.1) if result.outstanding_amount is not None else 3000.0,  # Mock calculation
            "collectorName": "System Auto",  # Mock collector
            "riskLevel": "yellow" if (result.cbs_risk_level or "GREEN").lower() == "green" else (result.cbs_risk_level or "GREEN").lower(),
            "alertSummary": f"Risk Level: {result.cbs_risk_level or 'Unknown'}",
            "lastContactDate": "2025-01-01T00:00:00",  # Mock date
            # Contract information
            "hasContractNote": result.contract_note_id is not None,
            "contractNoteId": result.contract_note_id,
            "contractEmiAmount": float(result.contract_emi_amount) if result.contract_emi_amount is not None else None,
            "contractDueDay": int(result.contract_due_day) if result.contract_due_day is not None else None,
            "contractLateFeePercent": float(result.contract_late_fee_percent) if result.contract_late_fee_percent is not None else None,
            "contractFilename": result.contract_filename,
            "contractFilePath": result.contract_file_path,
            # Customer additional info
            "cibilScore": int(result.cibil_score) if result.cibil_score is not None else None,
            "pendency": result.pendency,  # Add pendency field for processed status tracking
        })
    
    return loan_accounts


@router.post("/run-policy-agent")
async def run_policy_agent_endpoint(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Trigger the AI Policy Agent to evaluate all active rules against customer data
    and send automated emails based on matching conditions.
    """
    try:
        from app.services.policy_agent_service import run_policy_agent
        
        # Run the policy agent
        results = await run_policy_agent(db)
        
        return {
            "success": True,
            "message": "Policy agent evaluation completed",
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error running policy agent: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to run policy agent: {str(e)}")


@router.get("/policy-agent-status")
async def get_policy_agent_status(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Get the status of active policies and customer counts for the policy agent.
    """
    try:
        # Count active rules
        active_rules_count = (
            db.query(models.AutomationRule)
            .filter(models.AutomationRule.is_active == 1)
            .filter(models.AutomationRule.status == "active")
            .count()
        )
        
        # Count customers
        customers_count = db.query(models.Customer).count()
        
        # Get recent rules
        recent_rules = (
            db.query(models.AutomationRule)
            .filter(models.AutomationRule.is_active == 1)
            .filter(models.AutomationRule.status == "active")
            .order_by(desc(models.AutomationRule.id))
            .limit(5)
            .all()
        )
        
        return {
            "active_rules_count": active_rules_count,
            "customers_count": customers_count,
            "recent_active_rules": [
                {
                    "id": rule.id,
                    "name": rule.rule_name,
                    "action": rule.action,
                    "rule_level": rule.rule_level or "system"
                }
                for rule in recent_rules
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting policy agent status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get policy agent status: {str(e)}")


@router.get("/policy-scheduler-status")
async def get_policy_scheduler_status(
    current_user: models.User = Depends(get_current_user),
):
    """
    Get the status of the automatic policy scheduler.
    """
    try:
        from app.services.policy_scheduler_service import get_scheduler_status
        
        status = get_scheduler_status()
        
        return {
            "scheduler_running": status["is_running"],
            "interval_minutes": status["interval_minutes"],
            "thread_alive": status["thread_alive"],
            "message": "Automatic policy evaluation is running" if status["is_running"] else "Automatic policy evaluation is stopped"
        }
        
    except Exception as e:
        logger.error(f"Error getting policy scheduler status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get policy scheduler status: {str(e)}")


@router.post("/policy-scheduler-control")
async def control_policy_scheduler(
    action: str,
    interval_minutes: float = 0.5,  # Default to 30 seconds (0.5 minutes)
    current_user: models.User = Depends(get_current_user),
):
    """
    Control the automatic policy scheduler (start/stop).
    """
    try:
        from app.services.policy_scheduler_service import start_policy_scheduler, stop_policy_scheduler, get_scheduler_status
        
        if action == "start":
            scheduler = start_policy_scheduler(interval_minutes)
            return {
                "success": True,
                "message": f"Policy scheduler started with {interval_minutes} minute intervals",
                "status": get_scheduler_status()
            }
        elif action == "stop":
            stop_policy_scheduler()
            return {
                "success": True,
                "message": "Policy scheduler stopped",
                "status": get_scheduler_status()
            }
        else:
            raise HTTPException(status_code=400, detail="Invalid action. Use 'start' or 'stop'")
            
    except Exception as e:
        logger.error(f"Error controlling policy scheduler: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to control policy scheduler: {str(e)}")
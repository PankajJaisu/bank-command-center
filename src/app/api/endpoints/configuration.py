# src/app/api/endpoints/configuration.py
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, cast, Float, case
from typing import List, Optional
from pydantic import BaseModel
import fitz  # PyMuPDF
import os
import threading
from datetime import datetime

from app.api.dependencies import get_db, get_current_active_admin, get_current_user
from app.db import models, schemas
from app.db.session import engine  # Import the engine for dialect detection

# --- ADDED: Import the audit logger ---
from app.utils.auditing import log_audit_event

# --- ADDED: Import rule evaluator for field definitions ---
from app.services.rule_evaluator import get_available_contract_fields, get_available_customer_fields

# --- PHASE 2: Import policy parser service ---
from app.services import policy_parser_service
from app.utils.logging import get_logger

# --- ADDED: Import background tasks for sample data processing ---
from app.core.background_tasks import process_all_sample_data

logger = get_logger(__name__)

router = APIRouter()


# --- SIMPLE HEALTH CHECK ENDPOINT ---
@router.get("/health", summary="Configuration Health Check")
def get_config_health():
    """
    Simple health check endpoint for the configuration service.
    Returns basic app status without requiring database access.
    """
    return {"status": "healthy", "service": "configuration"}


# --- HELPER FUNCTION FOR DIALECT-SPECIFIC DATE DIFFERENCE ---
def _get_date_diff_days(date_col_1, date_col_2):
    """
    Returns a SQLAlchemy expression for the difference between two dates in days,
    handling different database dialects.
    """
    dialect = engine.dialect.name
    if dialect == "postgresql":
        # For PostgreSQL, simple subtraction gives days
        return date_col_1 - date_col_2
    else:  # Default to SQLite
        # For SQLite, use julianday
        return func.julianday(date_col_1) - func.julianday(date_col_2)


# --- NEW SCHEMA for Vendor Performance ---
class VendorPerformanceSummary(schemas.VendorSetting):
    total_invoices: int
    exception_rate: float
    avg_payment_time_days: Optional[float]


# --- NEW ENDPOINT for Vendor Performance ---
@router.get(
    "/vendor-performance-summary", response_model=List[VendorPerformanceSummary]
)
def get_vendor_performance_summary(
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """
    Retrieves all vendor settings and enriches them with performance KPIs. Admin only.
    """
    settings = db.query(models.VendorSetting).all()
    vendor_names = [s.vendor_name for s in settings]

    # Pre-calculate stats for all vendors with settings
    invoice_stats = (
        db.query(
            models.Invoice.vendor_name,
            func.count(models.Invoice.id).label("total_invoices"),
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
            func.avg(
                _get_date_diff_days(
                    models.Invoice.paid_date, models.Invoice.invoice_date
                )
            ).label("avg_payment_days"),
        )
        .filter(models.Invoice.vendor_name.in_(vendor_names))
        .group_by(models.Invoice.vendor_name)
        .all()
    )

    stats_map = {row.vendor_name: row for row in invoice_stats}

    results = []
    for setting in settings:
        stats = stats_map.get(setting.vendor_name)
        summary = VendorPerformanceSummary(
            **setting.__dict__,
            total_invoices=stats.total_invoices if stats else 0,
            exception_rate=(
                round(stats.exception_rate, 1)
                if stats and stats.exception_rate is not None
                else 0.0
            ),
            avg_payment_time_days=(
                round(stats.avg_payment_days, 1)
                if stats and stats.avg_payment_days is not None
                else None
            ),
        )
        results.append(summary)

    return sorted(results, key=lambda x: x.exception_rate, reverse=True)


# --- Vendor Settings Endpoints (Full CRUD) ---
@router.get("/vendor-settings", response_model=List[schemas.VendorSetting])
def get_all_vendor_settings(
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """Retrieves all vendor-specific settings. Admin only."""
    return (
        db.query(models.VendorSetting).order_by(models.VendorSetting.vendor_name).all()
    )


@router.post(
    "/vendor-settings",
    response_model=schemas.VendorSetting,
    status_code=status.HTTP_201_CREATED,
)
def create_vendor_setting(
    setting_data: schemas.VendorSettingCreate,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """Creates a new vendor-specific setting. Admin only."""
    new_setting = models.VendorSetting(**setting_data.model_dump())
    db.add(new_setting)

    # --- ADDED: Audit logging ---
    log_audit_event(
        db=db,
        user=admin_user.email,
        action="Vendor Setting Created",
        entity_type="VendorSetting",
        entity_id=new_setting.vendor_name,
        summary=f"Created settings for {new_setting.vendor_name}",
        details=setting_data.model_dump(),
    )
    # --- END ADDED ---

    db.commit()
    db.refresh(new_setting)
    return new_setting


@router.put("/vendor-settings/{setting_id}", response_model=schemas.VendorSetting)
def update_single_vendor_setting(
    setting_id: int,
    setting_data: schemas.VendorSettingCreate,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """Updates a single vendor setting. Admin only."""
    setting = (
        db.query(models.VendorSetting)
        .filter(models.VendorSetting.id == setting_id)
        .first()
    )
    if not setting:
        raise HTTPException(status_code=404, detail="Vendor setting not found")
    update_data = setting_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(setting, key, value)

    # --- ADDED: Audit logging ---
    log_audit_event(
        db=db,
        user=admin_user.email,
        action="Vendor Setting Updated",
        entity_type="VendorSetting",
        entity_id=setting.vendor_name,
        summary=f"Updated settings for {setting.vendor_name}",
        details={"changes": update_data},
    )
    # --- END ADDED ---

    db.commit()
    db.refresh(setting)
    return setting


@router.delete("/vendor-settings/{setting_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vendor_setting(
    setting_id: int,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """Deletes a vendor setting. Admin only."""
    setting = (
        db.query(models.VendorSetting)
        .filter(models.VendorSetting.id == setting_id)
        .first()
    )
    if not setting:
        raise HTTPException(status_code=404, detail="Vendor setting not found")

    vendor_name = setting.vendor_name  # Capture before delete
    db.delete(setting)

    # --- ADDED: Audit logging ---
    log_audit_event(
        db=db,
        user=admin_user.email,
        action="Vendor Setting Deleted",
        entity_type="VendorSetting",
        entity_id=vendor_name,
        summary=f"Deleted settings for {vendor_name}",
    )
    # --- END ADDED ---

    db.commit()
    return


# --- Automation Rules Endpoints (Full CRUD) ---
@router.get("/automation-rules", response_model=List[schemas.AutomationRule])
def get_all_automation_rules(
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """Retrieves all automation rules. Admin only."""
    return db.query(models.AutomationRule).order_by(models.AutomationRule.id).all()


@router.post(
    "/automation-rules",
    response_model=schemas.AutomationRule,
    status_code=status.HTTP_201_CREATED,
)
def create_new_automation_rule(
    rule_data: schemas.AutomationRuleCreate,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """Creates a new automation rule. Admin only."""
    new_rule = models.AutomationRule(**rule_data.model_dump())
    db.add(new_rule)

    # --- ADDED: Audit logging ---
    log_audit_event(
        db=db,
        user=admin_user.email,
        action="Automation Rule Created",
        entity_type="AutomationRule",
        entity_id=new_rule.rule_name,
        summary=f"Created rule: '{new_rule.rule_name}'",
        details=rule_data.model_dump(),
    )
    # --- END ADDED ---

    db.commit()
    db.refresh(new_rule)
    return new_rule


@router.put("/automation-rules/{rule_id}", response_model=schemas.AutomationRule)
def update_automation_rule(
    rule_id: int,
    rule_data: schemas.AutomationRuleCreate,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """Updates an automation rule. Admin only."""
    rule = (
        db.query(models.AutomationRule)
        .filter(models.AutomationRule.id == rule_id)
        .first()
    )
    if not rule:
        raise HTTPException(status_code=404, detail="Automation rule not found")

    update_data = rule_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(rule, key, value)

    # --- ADDED: Audit logging ---
    log_audit_event(
        db=db,
        user=admin_user.email,
        action="Automation Rule Updated",
        entity_type="AutomationRule",
        entity_id=rule.rule_name,
        summary=f"Updated rule: '{rule.rule_name}'",
        details={"changes": update_data},
    )
    # --- END ADDED ---

    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/automation-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_automation_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """Deletes an automation rule. Admin only."""
    rule = (
        db.query(models.AutomationRule)
        .filter(models.AutomationRule.id == rule_id)
        .first()
    )
    if not rule:
        raise HTTPException(status_code=404, detail="Automation rule not found")

    rule_name = rule.rule_name  # Capture before delete
    db.delete(rule)

    # --- ADDED: Audit logging ---
    log_audit_event(
        db=db,
        user=admin_user.email,
        action="Automation Rule Deleted",
        entity_type="AutomationRule",
        entity_id=rule_name,
        summary=f"Deleted rule: '{rule_name}'",
    )
    # --- END ADDED ---

    db.commit()
    return


@router.delete("/automation-rules")
def delete_all_automation_rules(
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """Delete all automation rules. Admin only."""
    try:
        # Count existing rules
        rule_count = db.query(models.AutomationRule).count()
        
        if rule_count == 0:
            return {"message": "No automation rules to delete", "deleted_count": 0}
        
        # Delete all rules
        deleted_count = db.query(models.AutomationRule).delete()
        
        # --- ADDED: Audit logging ---
        log_audit_event(
            db=db,
            user=admin_user.email,
            action="All Automation Rules Deleted",
            entity_type="AutomationRule",
            entity_id="bulk_delete",
            summary=f"Deleted all {deleted_count} automation rules",
        )
        # --- END ADDED ---
        
        db.commit()
        
        return {
            "message": f"Successfully deleted all {deleted_count} automation rules",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to delete automation rules: {str(e)}"
        )


# --- Extraction Field Configuration Endpoints ---


class ExtractionFieldConfigUpdate(BaseModel):
    id: int
    is_enabled: bool


class ExtractionFieldConfigResponse(BaseModel):
    id: int
    document_type: models.DocumentTypeEnum
    field_name: str
    display_name: str
    is_enabled: bool
    is_essential: bool
    is_editable: bool

    class Config:
        from_attributes = True


@router.get("/extraction-fields", response_model=List[ExtractionFieldConfigResponse])
def get_extraction_field_configurations(
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """
    Retrieves all configurable extraction fields for all document types. Admin only.
    """
    configs = (
        db.query(models.ExtractionFieldConfiguration)
        .order_by(
            models.ExtractionFieldConfiguration.document_type,
            models.ExtractionFieldConfiguration.id,
        )
        .all()
    )
    return configs


@router.put("/extraction-fields", response_model=List[ExtractionFieldConfigResponse])
def update_extraction_field_configurations(
    updates: List[ExtractionFieldConfigUpdate],
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """
    Bulk updates the 'is_enabled' status for a list of field configurations. Admin only.
    """
    updated_ids = [u.id for u in updates]
    configs = (
        db.query(models.ExtractionFieldConfiguration)
        .filter(models.ExtractionFieldConfiguration.id.in_(updated_ids))
        .all()
    )

    config_map = {c.id: c for c in configs}

    for update in updates:
        config_to_update = config_map.get(update.id)
        if config_to_update:
            # Prevent disabling essential fields
            if not config_to_update.is_essential:
                config_to_update.is_enabled = update.is_enabled

    db.commit()

    # Return the updated state of the requested configs
    return [config_map[uid] for uid in updated_ids if uid in config_map]


@router.get("/all-vendor-names", response_model=List[str])
def get_all_vendor_names(db: Session = Depends(get_db)):
    """
    Retrieves a list of all unique vendor names from the vendor settings.
    """
    vendor_names = (
        db.query(models.VendorSetting.vendor_name)
        .distinct()
        .order_by(models.VendorSetting.vendor_name)
        .all()
    )
    return [name for (name,) in vendor_names]


# --- SLA Endpoints (Full CRUD) ---


@router.get("/slas", response_model=List[schemas.SLA])
def get_all_slas(
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """Retrieves all SLA policies. Admin only."""
    return db.query(models.SLA).order_by(models.SLA.id).all()


@router.post("/slas", response_model=schemas.SLA, status_code=status.HTTP_201_CREATED)
def create_sla(
    sla_data: schemas.SLACreate,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """Creates a new SLA policy. Admin only."""
    new_sla = models.SLA(**sla_data.model_dump())
    db.add(new_sla)

    # --- ADDED: Audit logging ---
    log_audit_event(
        db=db,
        user=admin_user.email,
        action="SLA Created",
        entity_type="SLA",
        entity_id=new_sla.name,
        summary=f"Created SLA: '{new_sla.name}'",
        details=sla_data.model_dump(),
    )
    # --- END ADDED ---

    db.commit()
    db.refresh(new_sla)
    return new_sla


# --- LOAN POLICY LOADING ENDPOINT ---
@router.post("/load-loan-policies")
def load_loan_policies_endpoint(
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """Load loan policies from PDF documents and create automation rules. Admin only."""
    
    try:
        # Import the loan policy loader
        import subprocess
        import sys
        import os
        
        # Get the path to the loan policy loader script
        script_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "sample_data", "load_loan_policies.py")
        
        # Run the loan policy loader script
        result = subprocess.run([sys.executable, script_path], 
                              capture_output=True, text=True, cwd=os.path.dirname(script_path))
        
        if result.returncode == 0:
            # Count the newly created rules
            policy_rules = db.query(models.AutomationRule).filter(
                models.AutomationRule.source == "loan_policy"
            ).count()
            
            return {
                "success": True,
                "message": f"Successfully loaded loan policies and created {policy_rules} automation rules",
                "rules_created": policy_rules,
                "output": result.stdout
            }
        else:
            return {
                "success": False,
                "message": "Failed to load loan policies",
                "error": result.stderr,
                "output": result.stdout
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"Error loading loan policies: {str(e)}"
        }


@router.put("/slas/{sla_id}", response_model=schemas.SLA)
def update_sla(
    sla_id: int,
    sla_data: schemas.SLACreate,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """Updates an SLA policy. Admin only."""
    sla = db.query(models.SLA).filter(models.SLA.id == sla_id).first()
    if not sla:
        raise HTTPException(status_code=404, detail="SLA not found")

    update_data = sla_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(sla, key, value)

    # --- ADDED: Audit logging ---
    log_audit_event(
        db=db,
        user=admin_user.email,
        action="SLA Updated",
        entity_type="SLA",
        entity_id=sla.name,
        summary=f"Updated SLA: '{sla.name}'",
        details={"changes": update_data},
    )
    # --- END ADDED ---

    db.commit()
    db.refresh(sla)
    return sla


@router.delete("/slas/{sla_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sla(
    sla_id: int,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """Deletes an SLA policy. Admin only."""
    sla = db.query(models.SLA).filter(models.SLA.id == sla_id).first()
    if not sla:
        raise HTTPException(status_code=404, detail="SLA not found")

    sla_name = sla.name  # Capture before delete
    db.delete(sla)

    # --- ADDED: Audit logging ---
    log_audit_event(
        db=db,
        user=admin_user.email,
        action="SLA Deleted",
        entity_type="SLA",
        entity_id=sla_name,
        summary=f"Deleted SLA: '{sla_name}'",
    )
    # --- END ADDED ---

    db.commit()
    return


# --- NEW: Contract and Customer Field Endpoints for Rule Engine ---

@router.get("/rule-fields/contract")
def get_contract_rule_fields(
    admin_user: models.User = Depends(get_current_active_admin),
):
    """Get available contract fields for rule building. Admin only."""
    return {
        "fields": get_available_contract_fields(),
        "operators": [
            {"value": "equals", "label": "Equals", "types": ["text", "number"]},
            {"value": "not_equals", "label": "Not Equals", "types": ["text", "number"]},
            {"value": "contains", "label": "Contains", "types": ["text"]},
            {"value": ">", "label": "Greater Than", "types": ["number"]},
            {"value": "<", "label": "Less Than", "types": ["number"]},
            {"value": ">=", "label": "Greater Than or Equal", "types": ["number"]},
            {"value": "<=", "label": "Less Than or Equal", "types": ["number"]},
            {"value": "multiple_of", "label": "Multiple Of", "types": ["number"]},
            {"value": "percentage_greater_than", "label": "Percentage Greater Than", "types": ["number"]},
            {"value": "is_null", "label": "Is Empty", "types": ["text", "number"]},
        ]
    }


@router.get("/rule-fields/customer")
def get_customer_rule_fields(
    admin_user: models.User = Depends(get_current_active_admin),
):
    """Get available customer CBS fields for rule building. Admin only."""
    return {
        "fields": get_available_customer_fields(),
        "operators": [
            {"value": "equals", "label": "Equals", "types": ["text", "number"]},
            {"value": "not_equals", "label": "Not Equals", "types": ["text", "number"]},
            {"value": "contains", "label": "Contains", "types": ["text"]},
            {"value": ">", "label": "Greater Than", "types": ["number"]},
            {"value": "<", "label": "Less Than", "types": ["number"]},
            {"value": ">=", "label": "Greater Than or Equal", "types": ["number"]},
            {"value": "<=", "label": "Less Than or Equal", "types": ["number"]},
            {"value": "is_within_next_days", "label": "Is Within Next X Days", "types": ["date"]},
            {"value": "is_null", "label": "Is Empty", "types": ["text", "number", "date"]},
        ]
    }


@router.get("/rule-fields/all")
def get_all_rule_fields(
    admin_user: models.User = Depends(get_current_active_admin),
):
    """Get all available fields for rule building (invoice, contract, customer). Admin only."""
    
    # Standard invoice fields (from existing system)
    invoice_fields = [
        {"field": "vendor_name", "display": "Vendor Name", "type": "text"},
        {"field": "grand_total", "display": "Grand Total", "type": "number"},
        {"field": "subtotal", "display": "Subtotal", "type": "number"},
        {"field": "tax", "display": "Tax Amount", "type": "number"},
        {"field": "invoice_date", "display": "Invoice Date", "type": "date"},
        {"field": "due_date", "display": "Due Date", "type": "date"},
        {"field": "status", "display": "Status", "type": "text"},
        {"field": "review_category", "display": "Review Category", "type": "text"},
    ]
    
    return {
        "categories": [
            {
                "name": "Invoice Fields",
                "fields": invoice_fields
            },
            {
                "name": "Contract Fields", 
                "fields": get_available_contract_fields()
            },
            {
                "name": "Customer CBS Fields",
                "fields": get_available_customer_fields()
            }
        ],
        "operators": [
            {"value": "equals", "label": "Equals", "types": ["text", "number"]},
            {"value": "not_equals", "label": "Not Equals", "types": ["text", "number"]},
            {"value": "contains", "label": "Contains", "types": ["text"]},
            {"value": ">", "label": "Greater Than", "types": ["number"]},
            {"value": "<", "label": "Less Than", "types": ["number"]},
            {"value": ">=", "label": "Greater Than or Equal", "types": ["number"]},
            {"value": "<=", "label": "Less Than or Equal", "types": ["number"]},
            {"value": "multiple_of", "label": "Multiple Of", "types": ["number"]},
            {"value": "percentage_greater_than", "label": "Percentage Greater Than", "types": ["number"]},
            {"value": "is_within_next_days", "label": "Is Within Next X Days", "types": ["date"]},
            {"value": "is_null", "label": "Is Empty", "types": ["text", "number", "date"]},
        ]
    }


# --- PHASE 2: NEW ENDPOINT FOR POLICY UPLOAD ---
@router.post("/upload-policy", summary="Upload and parse a policy document")
async def upload_and_parse_policy(
    file: UploadFile = File(...),
    rule_level: str = Query("system", enum=["system", "segment", "customer"]),
    segment: Optional[str] = Query(None),
    customer_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """
    Uploads a policy document (PDF), extracts text, parses it with AI to create rules,
    and saves them with a 'pending_review' status.
    """
    try:
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported.")

        # Extract text from PDF
        pdf_bytes = await file.read()
        policy_text = ""
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            for page in doc:
                policy_text += page.get_text()

        if not policy_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from PDF.")

        # Parse text to rules using the AI service
        extracted_rules = policy_parser_service.parse_policy_to_rules(policy_text)
        if not extracted_rules:
            raise HTTPException(status_code=400, detail="AI could not extract any valid rules from the document.")

        # Save rules as 'pending_review'
        new_rules_count = 0
        for rule_data in extracted_rules:
            new_rule = models.AutomationRule(
                rule_name=rule_data.get("rule_name", "Unnamed AI Rule"),
                description=rule_data.get("description", ""),
                conditions=rule_data.get("conditions", {}),
                action=rule_data.get("action", "Send Reminder"),
                is_active=0,  # Rules are inactive until approved
                source="policy_upload",
                status="pending_review",
                rule_level=rule_level,
                segment=segment if rule_level == "segment" else None,
                customer_id=customer_id if rule_level == "customer" else None,
                source_document=file.filename,
            )
            db.add(new_rule)
            new_rules_count += 1
        
        db.commit()

        return {
            "message": f"Successfully uploaded and created {new_rules_count} rules for review.",
            "rules_created": new_rules_count,
            "filename": file.filename,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error during policy upload: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# --- SAMPLE DATA SYNC ENDPOINT ---
@router.post("/sync-sample-data", response_model=schemas.Job, status_code=status.HTTP_202_ACCEPTED)
def sync_sample_data_endpoint(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Triggers a comprehensive sync of all sample data including contract notes, 
    customer Excel files, and loan documents from the sample_data directory.
    """
    try:
        # Create a new job record
        new_job = models.Job(
            status="processing",
            total_files=0,  # Will be updated by the background task
            processed_files=0,
            created_at=datetime.utcnow()
        )
        db.add(new_job)
        db.commit()
        db.refresh(new_job)
        
        logger.info(f"🚀 Starting sample data sync job {new_job.id} for user {current_user.email}")
        
        # Collect all sample data files
        sample_data_path = os.path.join(os.getcwd(), "sample_data")
        files_data = []
        
        if not os.path.exists(sample_data_path):
            raise HTTPException(status_code=404, detail="Sample data directory not found")
        
        # Process contract notes
        contract_notes_path = os.path.join(sample_data_path, "contract note")
        if os.path.exists(contract_notes_path):
            for filename in os.listdir(contract_notes_path):
                if filename.lower().endswith('.pdf'):
                    file_path = os.path.join(contract_notes_path, filename)
                    with open(file_path, 'rb') as f:
                        files_data.append({
                            "filename": filename,
                            "content": f.read(),
                            "file_type": "contract_note",
                            "source_folder": "contract note"
                        })
        
        # Process customer data Excel files
        customer_data_path = os.path.join(sample_data_path, "customer_data")
        if os.path.exists(customer_data_path):
            for filename in os.listdir(customer_data_path):
                if filename.lower().endswith(('.xlsx', '.xls')):
                    file_path = os.path.join(customer_data_path, filename)
                    with open(file_path, 'rb') as f:
                        files_data.append({
                            "filename": filename,
                            "content": f.read(),
                            "file_type": "customer_data",
                            "source_folder": "customer_data"
                        })
        
        # Process loan policy documents
        loan_policy_path = os.path.join(sample_data_path, "invoices")  # Note: invoices folder contains loan policies
        if os.path.exists(loan_policy_path):
            for filename in os.listdir(loan_policy_path):
                if filename.lower().endswith('.pdf') and 'policy' in filename.lower():
                    file_path = os.path.join(loan_policy_path, filename)
                    with open(file_path, 'rb') as f:
                        files_data.append({
                            "filename": filename,
                            "content": f.read(),
                            "file_type": "loan_document",
                            "source_folder": "invoices"
                        })
        
        # Update job with total files count
        new_job.total_files = len(files_data)
        db.commit()
        
        if not files_data:
            new_job.status = "completed"
            new_job.completed_at = datetime.utcnow()
            new_job.summary = [{"filename": "No files found", "status": "error", "message": "No sample data files found to process", "extracted_id": None, "document_type": None}]
            db.commit()
            return new_job
        
        # Start background processing in a separate thread
        def run_background_task():
            process_all_sample_data(new_job.id, files_data)
        
        thread = threading.Thread(target=run_background_task)
        thread.daemon = True
        thread.start()
        
        # Log audit event
        log_audit_event(
            db=db,
            user=current_user.email,
            action="Sample Data Sync Started",
            entity_type="Job",
            entity_id=str(new_job.id),
            summary=f"Started comprehensive sample data sync with {len(files_data)} files",
            details={
                "job_id": new_job.id,
                "total_files": len(files_data),
                "file_types": list(set(f["file_type"] for f in files_data))
            }
        )
        
        return new_job
        
    except Exception as e:
        logger.error(f"Error starting sample data sync: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start sample data sync: {str(e)}")


# --- JOB STATUS ENDPOINTS ---
@router.get("/jobs/{job_id}", response_model=schemas.Job)
def get_job_status(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Get the status of a specific job by ID.
    """
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job


@router.get("/jobs", response_model=List[schemas.Job])
def get_all_jobs(
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Get a list of recent jobs with pagination.
    """
    jobs = (
        db.query(models.Job)
        .order_by(models.Job.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return jobs

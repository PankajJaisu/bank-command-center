# src/app/modules/copilot/tools.py
import json
import os
from typing import Any, Dict, List, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session
from google import genai
from google.genai import types as genai_types

from app.db import models, schemas
from app.utils import data_formatting
from app.config import settings

# --- Import API logic and audit logger ---
from app.api.endpoints import (
    configuration,
    learning,
    notifications,
    collection,
)
from app.services import dashboard_service
from app.utils.auditing import log_audit_event

# Use centralized configuration for generated documents
GENERATED_DOCS_DIR = settings.generated_pdf_storage_path

# Ensure directory exists on module import with error handling
try:
    os.makedirs(GENERATED_DOCS_DIR, exist_ok=True)
except OSError as e:
    print(
        f"Warning: Could not create generated documents directory {GENERATED_DOCS_DIR}: {e}"
    )


# --- Helper Function ---
def make_json_serializable(data: Any) -> Any:
    """Converts a Python object into a JSON-serializable version."""
    return json.loads(json.dumps(data, default=str))


# --- Helper to create a system user context for service calls ---
def get_system_user_context(db: Session) -> models.User:
    """Creates a temporary admin user context for service calls."""
    admin_role = db.query(models.Role).filter(models.Role.name == "admin").first()
    if not admin_role:
        raise ValueError("Admin role not found, cannot execute system-level requests.")
    return models.User(id=-1, role=admin_role, email="system@agent")


# ==============================================================================
# SECTION 1: READ-ONLY & ANALYSIS TOOLS
# ==============================================================================

get_system_kpis_declaration = genai_types.FunctionDeclaration(
    name="get_system_kpis",
    description="Retrieves high-level collection KPIs and system performance metrics.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={},
    ),
)

def get_system_kpis(db: Session) -> Dict[str, Any]:
    """Get collection system KPIs."""
    try:
        kpis = collection.get_collection_kpis(db=db, current_user=get_system_user_context(db))
        metrics = collection.get_collection_metrics(db=db, current_user=get_system_user_context(db))
        
        return {
            "collection_kpis": kpis,
            "collection_metrics": metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {"error": f"Failed to retrieve system KPIs: {str(e)}"}


find_customers_declaration = genai_types.FunctionDeclaration(
    name="find_customers",
    description="Search for customers by name, customer number, risk level, or other criteria.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "search_term": genai_types.Schema(type=genai_types.Type.STRING),
            "risk_level": genai_types.Schema(type=genai_types.Type.STRING),
            "limit": genai_types.Schema(type=genai_types.Type.INTEGER),
        },
    ),
)

def find_customers(db: Session, search_term: str = "", risk_level: str = "", limit: int = 20) -> List[Dict[str, Any]]:
    """Search for customers based on criteria."""
    try:
        system_user_context = get_system_user_context(db)
        customers = collection.get_customers(
            limit=limit,
            search=search_term if search_term else None,
            risk_level=risk_level if risk_level else None,
            db=db,
            current_user=system_user_context
        )
        return make_json_serializable([customer.__dict__ for customer in customers])
    except Exception as e:
        return [{"error": f"Customer search failed: {str(e)}"}]


get_loan_accounts_declaration = genai_types.FunctionDeclaration(
    name="get_loan_accounts",
    description="Retrieves loan accounts with contract information and collection status.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "status": genai_types.Schema(type=genai_types.Type.STRING),
            "risk_level": genai_types.Schema(type=genai_types.Type.STRING),
            "limit": genai_types.Schema(type=genai_types.Type.INTEGER),
        },
    ),
)

def get_loan_accounts(db: Session, status: str = "", risk_level: str = "", limit: int = 50) -> List[Dict[str, Any]]:
    """Get loan accounts with contract details."""
    try:
        system_user_context = get_system_user_context(db)
        accounts = collection.get_loan_accounts_with_contracts(
            limit=limit,
            status=status if status else None,
            risk_level=risk_level if risk_level else None,
            db=db,
            current_user=system_user_context
        )
        return make_json_serializable(accounts)
    except Exception as e:
        return [{"error": f"Failed to retrieve loan accounts: {str(e)}"}]


get_customer_details_declaration = genai_types.FunctionDeclaration(
    name="get_customer_details",
    description="Retrieves complete customer profile including loan details, contract notes, and risk assessment.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={"customer_id": genai_types.Schema(type=genai_types.Type.INTEGER)},
    ),
)

def get_customer_details(db: Session, customer_id: int) -> Dict[str, Any]:
    """Get detailed customer information."""
    try:
        customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
        if not customer:
            return {"error": f"Customer with ID {customer_id} not found"}
        
        # Get associated loan and contract note
        loan = db.query(models.Loan).filter(models.Loan.customer_id == customer_id).first()
        contract_note = db.query(models.ContractNote).filter(models.ContractNote.customer_id == customer_id).first()
        
        result = {
            "customer": make_json_serializable(customer.__dict__),
            "loan": make_json_serializable(loan.__dict__) if loan else None,
            "contract_note": make_json_serializable(contract_note.__dict__) if contract_note else None,
        }
        
        return result
    except Exception as e:
        return {"error": f"Failed to retrieve customer details: {str(e)}"}


get_notifications_declaration = genai_types.FunctionDeclaration(
    name="get_notifications",
    description="Retrieves system notifications and alerts.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "limit": genai_types.Schema(type=genai_types.Type.INTEGER),
            "unread_only": genai_types.Schema(type=genai_types.Type.BOOLEAN),
        },
    ),
)

def get_notifications(db: Session, limit: int = 10, unread_only: bool = False) -> List[Dict[str, Any]]:
    """Get system notifications."""
    try:
        system_user_context = get_system_user_context(db)
        notifications_list = notifications.get_notifications(
            limit=limit,
            unread_only=unread_only,
            db=db,
            current_user=system_user_context
        )
        return make_json_serializable([notif.__dict__ for notif in notifications_list])
    except Exception as e:
        return [{"error": f"Failed to retrieve notifications: {str(e)}"}]


# ==============================================================================
# SECTION 2: COLLECTION ACTION TOOLS
# ==============================================================================

update_collection_status_declaration = genai_types.FunctionDeclaration(
    name="update_collection_status",
    description="Updates the collection status of a loan account.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "account_id": genai_types.Schema(type=genai_types.Type.INTEGER),
            "status": genai_types.Schema(type=genai_types.Type.STRING),
            "notes": genai_types.Schema(type=genai_types.Type.STRING),
        },
        required=["account_id", "status"],
    ),
)

def update_collection_status(db: Session, account_id: int, status: str, notes: str = "") -> Dict[str, Any]:
    """Update collection status for a loan account."""
    try:
        # Find the customer/loan account
        customer = db.query(models.Customer).filter(models.Customer.id == account_id).first()
        if not customer:
            return {"error": f"Account with ID {account_id} not found"}
        
        # Log the status update
        log_audit_event(
            db=db,
            user="AI Agent",
            action=f"Collection Status Updated to {status}",
            entity_type="Customer",
            entity_id=str(customer.customer_no),
            summary=f"Status changed to {status}",
            details={"new_status": status, "notes": notes}
        )
        
        db.commit()
        return {"success": True, "message": f"Collection status updated to {status}"}
    except Exception as e:
        db.rollback()
        return {"error": f"Failed to update collection status: {str(e)}"}


log_customer_contact_declaration = genai_types.FunctionDeclaration(
    name="log_customer_contact",
    description="Logs a contact attempt or communication with a customer.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "customer_id": genai_types.Schema(type=genai_types.Type.INTEGER),
            "contact_type": genai_types.Schema(type=genai_types.Type.STRING),
            "outcome": genai_types.Schema(type=genai_types.Type.STRING),
            "notes": genai_types.Schema(type=genai_types.Type.STRING),
        },
        required=["customer_id", "contact_type"],
    ),
)

def log_customer_contact(db: Session, customer_id: int, contact_type: str, outcome: str = "", notes: str = "") -> Dict[str, Any]:
    """Log a customer contact interaction."""
    try:
        customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
        if not customer:
            return {"error": f"Customer with ID {customer_id} not found"}
        
        # Log the contact
        log_audit_event(
            db=db,
            user="AI Agent",
            action=f"Customer Contact: {contact_type}",
            entity_type="Customer",
            entity_id=str(customer.customer_no),
            summary=f"{contact_type} - {outcome}",
            details={"contact_type": contact_type, "outcome": outcome, "notes": notes}
        )
        
        db.commit()
        return {"success": True, "message": "Customer contact logged successfully"}
    except Exception as e:
        db.rollback()
        return {"error": f"Failed to log customer contact: {str(e)}"}


# ==============================================================================
# SECTION 3: RISK ASSESSMENT & AUTOMATION TOOLS
# ==============================================================================

create_risk_rule_declaration = genai_types.FunctionDeclaration(
    name="create_risk_rule",
    description="Creates a new risk assessment rule for loan collection management.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "rule_name": genai_types.Schema(type=genai_types.Type.STRING),
            "conditions": genai_types.Schema(type=genai_types.Type.STRING),
            "risk_level": genai_types.Schema(type=genai_types.Type.STRING),
            "action": genai_types.Schema(type=genai_types.Type.STRING),
            "description": genai_types.Schema(type=genai_types.Type.STRING),
        },
        required=["rule_name", "conditions", "risk_level"],
    ),
)

def create_risk_rule(db: Session, rule_name: str, conditions: str, risk_level: str, action: str = "", description: str = "") -> Dict[str, Any]:
    """Create a new risk assessment rule."""
    try:
        # Parse conditions JSON
        try:
            conditions_dict = json.loads(conditions)
        except json.JSONDecodeError:
            return {"error": "Invalid JSON format for conditions"}
        
        # Create the automation rule
        new_rule = models.AutomationRule(
            rule_name=rule_name,
            conditions=conditions_dict,
            action=action or "flag_for_review",
            is_active=True,
            source="ai_agent",
            description=description
        )
        
        db.add(new_rule)
        db.commit()
        
        return {"success": True, "rule_id": new_rule.id, "message": f"Risk rule '{rule_name}' created successfully"}
    except Exception as e:
        db.rollback()
        return {"error": f"Failed to create risk rule: {str(e)}"}


# ==============================================================================
# TOOL REGISTRY
# ==============================================================================

# Collection of all available tools for the AI agent
COLLECTION_TOOLS = [
    # Read-only tools
    get_system_kpis_declaration,
    find_customers_declaration,
    get_loan_accounts_declaration,
    get_customer_details_declaration,
    get_notifications_declaration,
    
    # Action tools
    update_collection_status_declaration,
    log_customer_contact_declaration,
    
    # Risk management tools
    create_risk_rule_declaration,
]

# Function mapping for tool execution
TOOL_FUNCTIONS = {
    "get_system_kpis": get_system_kpis,
    "find_customers": find_customers,
    "get_loan_accounts": get_loan_accounts,
    "get_customer_details": get_customer_details,
    "get_notifications": get_notifications,
    "update_collection_status": update_collection_status,
    "log_customer_contact": log_customer_contact,
    "create_risk_rule": create_risk_rule,
}

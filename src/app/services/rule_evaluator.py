# src/app/services/rule_evaluator.py
from datetime import datetime, timedelta, date
from app.db.models import Invoice, Customer
from sqlalchemy.orm import Session


def evaluate_condition(invoice: Invoice, condition: dict, db: Session = None) -> bool:
    """Evaluates a single condition against an invoice."""
    field = condition.get("field")
    operator = condition.get("operator")
    value = condition.get("value")

    if not all([field, operator]):
        return False

    # Handle contract-related fields
    if field.startswith("contract.") and db:
        return evaluate_contract_condition(invoice, field, operator, value, db)
    
    # Handle customer-related fields  
    if field.startswith("customer.") and db:
        return evaluate_customer_condition(invoice, field, operator, value, db)

    invoice_value = getattr(invoice, field, None)

    # Handle specific operators
    try:
        if operator == "is_null":
            return invoice_value is None
        if invoice_value is None:
            return False  # For all other operators, if the invoice value is null, it's a fail.

        if operator == "equals":
            return str(invoice_value).lower() == str(value).lower()
        if operator == "not_equals":
            return str(invoice_value).lower() != str(value).lower()
        if operator == "contains":
            return str(value).lower() in str(invoice_value).lower()
        if operator == ">":
            return float(invoice_value) > float(value)
        if operator == "<":
            return float(invoice_value) < float(value)
        if operator == ">=":
            return float(invoice_value) >= float(value)
        if operator == "<=":
            return float(invoice_value) <= float(value)
        if operator == "is_within_next_days":
            if isinstance(invoice_value, (datetime, date)):
                future_date = datetime.utcnow() + timedelta(days=int(value))
                return invoice_value <= future_date.date()
    except (ValueError, TypeError):
        return False

    return False


def evaluate_contract_condition(invoice: Invoice, field: str, operator: str, value, db: Session) -> bool:
    """Evaluate conditions against contract data fields"""
    try:
        # Find the customer associated with this invoice (this would need to be implemented
        # based on your business logic for linking invoices to customers)
        # For now, let's assume we can find it via vendor_name or another field
        
        # This is a placeholder - you'll need to implement the actual logic
        # to find the customer associated with an invoice
        customer = find_customer_for_invoice(invoice, db)
        if not customer or not customer.contract_note:
            return False
        
        contract_field = field.replace("contract.", "contract_")
        contract_value = getattr(customer.contract_note, contract_field, None)
        
        return apply_operator(contract_value, operator, value)
        
    except Exception:
        return False


def evaluate_customer_condition(invoice: Invoice, field: str, operator: str, value, db: Session) -> bool:
    """Evaluate conditions against customer CBS data fields"""
    try:
        customer = find_customer_for_invoice(invoice, db)
        if not customer:
            return False
        
        customer_field = field.replace("customer.", "cbs_")
        customer_value = getattr(customer, customer_field, None)
        
        return apply_operator(customer_value, operator, value)
        
    except Exception:
        return False


def find_customer_for_invoice(invoice: Invoice, db: Session) -> Customer:
    """
    Find the customer associated with an invoice.
    This is a placeholder implementation - you'll need to implement
    the actual business logic for linking invoices to customers.
    """
    # This could be based on vendor_name, customer ID in invoice metadata, etc.
    # For now, return None as this needs to be implemented based on your data model
    return None


def apply_operator(field_value, operator: str, comparison_value) -> bool:
    """Apply the comparison operator to field and comparison values"""
    try:
        if operator == "is_null":
            return field_value is None
        if field_value is None:
            return False

        if operator == "equals":
            return str(field_value).lower() == str(comparison_value).lower()
        if operator == "not_equals":
            return str(field_value).lower() != str(comparison_value).lower()
        if operator == "contains":
            return str(comparison_value).lower() in str(field_value).lower()
        if operator == ">":
            return float(field_value) > float(comparison_value)
        if operator == "<":
            return float(field_value) < float(comparison_value)
        if operator == ">=":
            return float(field_value) >= float(comparison_value)
        if operator == "<=":
            return float(field_value) <= float(comparison_value)
        if operator == "is_within_next_days":
            if isinstance(field_value, (datetime, date)):
                future_date = datetime.utcnow() + timedelta(days=int(comparison_value))
                return field_value <= future_date.date()
        
        # New operators for contract-specific conditions
        if operator == "multiple_of":
            # Check if field_value is a multiple of comparison_value
            return float(field_value) % float(comparison_value) == 0
        if operator == "percentage_greater_than":
            # Check if field_value (as percentage) is greater than comparison_value
            return float(field_value) > float(comparison_value)
            
    except (ValueError, TypeError):
        return False

    return False


def evaluate_policy(invoice: Invoice, policy: dict, db: Session = None) -> bool:
    """
    Evaluates a full policy (with logical operators) against an invoice.
    """
    conditions = policy.get("conditions", [])
    if not conditions:
        return False  # A policy must have conditions to be valid.

    logical_operator = policy.get("logical_operator", "AND").upper()

    if logical_operator == "AND":
        # For AND, all conditions must be true.
        return all(evaluate_condition(invoice, cond, db) for cond in conditions)
    elif logical_operator == "OR":
        # For OR, at least one condition must be true.
        return any(evaluate_condition(invoice, cond, db) for cond in conditions)

    return False


def get_available_contract_fields():
    """Return available contract fields for rule building"""
    return [
        {"field": "contract.emi_amount", "display": "Contract EMI Amount", "type": "number"},
        {"field": "contract.due_day", "display": "Contract Due Day", "type": "number"},
        {"field": "contract.late_fee_percent", "display": "Contract Late Fee %", "type": "number"},
        {"field": "contract.interest_rate", "display": "Contract Interest Rate", "type": "number"},
        {"field": "contract.loan_amount", "display": "Contract Loan Amount", "type": "number"},
        {"field": "contract.tenure_months", "display": "Contract Tenure (Months)", "type": "number"},
        {"field": "contract.default_clause", "display": "Contract Default Clause", "type": "text"},
        {"field": "contract.governing_law", "display": "Contract Governing Law", "type": "text"},
    ]


def get_available_customer_fields():
    """Return available customer CBS fields for rule building"""
    return [
        {"field": "customer.emi_amount", "display": "CBS EMI Amount", "type": "number"},
        {"field": "customer.due_day", "display": "CBS Due Day", "type": "number"},
        {"field": "customer.outstanding_amount", "display": "CBS Outstanding Amount", "type": "number"},
        {"field": "customer.risk_level", "display": "CBS Risk Level", "type": "text"},
        {"field": "customer.last_payment_date", "display": "CBS Last Payment Date", "type": "date"},
    ]

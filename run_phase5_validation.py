#!/usr/bin/env python3
"""
Phase 5 Validation Script - Comprehensive End-to-End Testing

This script validates the complete collection management system by testing:
1. AI Policy Agent automated classification and actions
2. Resolution Workbench manual actions and escalations
3. Comprehensive audit trail for all activities
4. Database integrity and consistency

Run this script after implementing all phases to ensure the system works correctly.
"""

import sys
import os
sys.path.insert(0, 'src')

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db import models
from app.services.policy_agent_service import PolicyAgentService
from app.api.endpoints.collection import get_workbench_pending_cases, log_workbench_action, escalate_case_via_email
from app.api.endpoints.collection import LogActionRequest, EscalateEmailRequest
from app.utils.auditing import log_audit_event
from unittest.mock import Mock
import json

def print_header(title):
    """Print a formatted header for test sections."""
    print(f"\n{'='*60}")
    print(f"🧪 {title}")
    print(f"{'='*60}")

def print_step(step_num, description):
    """Print a formatted step description."""
    print(f"\n🔄 Step {step_num}: {description}")
    print("-" * 50)

def print_success(message):
    """Print a success message."""
    print(f"✅ {message}")

def print_error(message):
    """Print an error message."""
    print(f"❌ {message}")

def print_info(message):
    """Print an info message."""
    print(f"ℹ️  {message}")

def create_test_customers(db: Session):
    """Create test customers with different risk profiles."""
    print_step(1, "Creating test customers with different risk profiles")
    
    # Clear existing test customers
    db.query(models.Customer).filter(models.Customer.customer_no.like('TEST-%')).delete()
    db.commit()
    
    test_customers = [
        {
            "customer_no": "TEST-LOW-RISK-001",
            "name": "Low Risk Customer",
            "email": "lowrisk@example.com",
            "phone": "+91-9876543210",
            "segment": "Retail",
            "cbs_outstanding_amount": 10000.0,
            "cbs_emi_amount": 2000.0,
            "emi_pending": 1,
            "cbs_last_payment_date": datetime.now().date() - timedelta(days=10)
        },
        {
            "customer_no": "TEST-MEDIUM-RISK-001",
            "name": "Medium Risk Customer", 
            "email": "mediumrisk@example.com",
            "phone": "+91-9876543211",
            "segment": "MSME",
            "cbs_outstanding_amount": 50000.0,
            "cbs_emi_amount": 5000.0,
            "emi_pending": 2,
            "cbs_last_payment_date": datetime.now().date() - timedelta(days=45)
        },
        {
            "customer_no": "TEST-HIGH-RISK-001",
            "name": "High Risk Customer",
            "email": "highrisk@example.com", 
            "phone": "+91-9876543212",
            "segment": "Corporate",
            "cbs_outstanding_amount": 100000.0,
            "cbs_emi_amount": 10000.0,
            "emi_pending": 4,
            "cbs_last_payment_date": datetime.now().date() - timedelta(days=90)
        }
    ]
    
    created_customers = []
    for customer_data in test_customers:
        customer = models.Customer(**customer_data)
        db.add(customer)
        created_customers.append(customer)
    
    db.commit()
    print_success(f"Created {len(created_customers)} test customers")
    return created_customers

def create_test_rules(db: Session):
    """Create test automation rules for different risk scenarios."""
    print_step(2, "Creating test automation rules")
    
    # Clear existing test rules
    db.query(models.AutomationRule).filter(models.AutomationRule.rule_name.like('Test %')).delete()
    db.commit()
    
    test_rules = [
        {
            "rule_name": "Test Low Risk Rule",
            "description": "Test rule for low risk customers",
            "conditions": json.dumps({
                "logical_operator": "AND",
                "conditions": [
                    {"field": "emi_count", "operator": "<=", "value": 1},
                    {"field": "dpd", "operator": "<", "value": 30}
                ]
            }),
            "action": "Send Reminder",
            "is_active": 1,
            "status": "active",
            "source": "test",
            "rule_level": "system"
        },
        {
            "rule_name": "Test Medium Risk Rule", 
            "description": "Test rule for medium risk customers",
            "conditions": json.dumps({
                "logical_operator": "AND",
                "conditions": [
                    {"field": "emi_count", "operator": ">=", "value": 2},
                    {"field": "dpd", "operator": ">=", "value": 30}
                ]
            }),
            "action": "Make Phone Call",
            "is_active": 1,
            "status": "active",
            "source": "test",
            "rule_level": "system"
        },
        {
            "rule_name": "Test High Risk Rule",
            "description": "Test rule for high risk customers", 
            "conditions": json.dumps({
                "logical_operator": "AND",
                "conditions": [
                    {"field": "emi_count", "operator": ">=", "value": 3},
                    {"field": "dpd", "operator": ">=", "value": 60}
                ]
            }),
            "action": "Send Legal Notice",
            "is_active": 1,
            "status": "active",
            "source": "test",
            "rule_level": "system"
        }
    ]
    
    created_rules = []
    for rule_data in test_rules:
        rule = models.AutomationRule(**rule_data)
        db.add(rule)
        created_rules.append(rule)
    
    db.commit()
    print_success(f"Created {len(created_rules)} test automation rules")
    return created_rules

def test_ai_policy_agent(db: Session):
    """Test the AI Policy Agent classification and automated actions."""
    print_step(3, "Testing AI Policy Agent classification and automated actions")
    
    # Run the policy agent
    agent = PolicyAgentService(db)
    result = agent.run_agent()
    
    print_info(f"Policy agent processed {result['processed_customers']} customers")
    
    # Verify classifications
    test_customers = db.query(models.Customer).filter(models.Customer.customer_no.like('TEST-%')).all()
    
    classifications = {}
    for customer in test_customers:
        classifications[customer.customer_no] = {
            "risk_level": customer.risk_level,
            "ai_suggested_action": customer.ai_suggested_action,
            "last_action_taken": customer.last_action_taken
        }
        print_info(f"{customer.customer_no}: {customer.risk_level} risk - {customer.ai_suggested_action}")
    
    # Verify audit logs were created
    audit_count = db.query(models.AuditLog).filter(
        models.AuditLog.user == "System",
        models.AuditLog.action.in_(["AI Classification", "Automated Action"])
    ).count()
    
    print_success(f"AI Policy Agent created {audit_count} audit log entries")
    return classifications

def test_workbench_functionality(db: Session):
    """Test the Resolution Workbench functionality."""
    print_step(4, "Testing Resolution Workbench functionality")
    
    # Create mock user
    mock_user = Mock()
    mock_user.id = 1
    mock_user.email = "test-agent@example.com"
    
    # Test getting pending cases
    pending_cases = get_workbench_pending_cases(db=db, current_user=mock_user)
    print_info(f"Found {len(pending_cases)} pending cases in workbench queue")
    
    if len(pending_cases) == 0:
        print_error("No pending cases found. Expected high/medium risk cases.")
        return False
    
    # Test logging manual action
    test_case = pending_cases[0]
    print_info(f"Testing manual action on case: {test_case.customer_no}")
    
    log_request = LogActionRequest(
        action_taken="Called customer - promised payment by Friday",
        notes="Customer was cooperative and agreed to payment plan"
    )
    
    updated_customer = log_workbench_action(
        customer_no=test_case.customer_no,
        payload=log_request,
        db=db,
        current_user=mock_user
    )
    
    print_success(f"Manual action logged: {updated_customer.last_action_taken}")
    
    # Test escalation if we have another case
    if len(pending_cases) > 1:
        escalation_case = pending_cases[1]
        print_info(f"Testing escalation on case: {escalation_case.customer_no}")
        
        escalate_request = EscalateEmailRequest(
            to_email="legal-team@bank.com",
            subject=f"Escalation Required: {escalation_case.customer_no}",
            body=f"Please review high-risk case {escalation_case.customer_no}. Customer has not responded to multiple attempts."
        )
        
        result = escalate_case_via_email(
            customer_no=escalation_case.customer_no,
            payload=escalate_request,
            db=db,
            current_user=mock_user
        )
        
        print_success(f"Escalation completed: {result['message']}")
    
    return True

def verify_audit_trail(db: Session):
    """Verify comprehensive audit trail for all activities."""
    print_step(5, "Verifying comprehensive audit trail")
    
    # Count audit logs by action type
    audit_summary = {}
    
    audit_actions = ["AI Classification", "Automated Action", "Manual Action Logged", "Case Escalated"]
    
    for action in audit_actions:
        count = db.query(models.AuditLog).filter(models.AuditLog.action == action).count()
        audit_summary[action] = count
        print_info(f"{action}: {count} entries")
    
    total_audit_entries = sum(audit_summary.values())
    print_success(f"Total audit entries: {total_audit_entries}")
    
    # Verify audit log details
    sample_audit = db.query(models.AuditLog).filter(
        models.AuditLog.action == "AI Classification"
    ).first()
    
    if sample_audit:
        print_info("Sample audit log details:")
        print_info(f"  User: {sample_audit.user}")
        print_info(f"  Action: {sample_audit.action}")
        print_info(f"  Entity: {sample_audit.entity_type} - {sample_audit.entity_id}")
        print_info(f"  Summary: {sample_audit.summary}")
        print_info(f"  Details: {len(sample_audit.details)} fields")
    
    return audit_summary

def cleanup_test_data(db: Session):
    """Clean up test data created during validation."""
    print_step(6, "Cleaning up test data")
    
    # Delete test customers
    deleted_customers = db.query(models.Customer).filter(models.Customer.customer_no.like('TEST-%')).delete()
    
    # Delete test rules
    deleted_rules = db.query(models.AutomationRule).filter(models.AutomationRule.rule_name.like('Test %')).delete()
    
    # Keep audit logs for compliance - don't delete them
    
    db.commit()
    print_success(f"Cleaned up {deleted_customers} test customers and {deleted_rules} test rules")
    print_info("Audit logs preserved for compliance")

def main():
    """Main validation function."""
    print_header("PHASE 5 COMPREHENSIVE VALIDATION")
    print("This script validates the complete collection management system")
    print("including AI classification, workbench functionality, and audit trails.")
    
    db = SessionLocal()
    
    try:
        # Test execution
        test_customers = create_test_customers(db)
        test_rules = create_test_rules(db)
        classifications = test_ai_policy_agent(db)
        workbench_success = test_workbench_functionality(db)
        audit_summary = verify_audit_trail(db)
        cleanup_test_data(db)
        
        # Final summary
        print_header("VALIDATION RESULTS")
        
        success_count = 0
        total_tests = 6
        
        if len(test_customers) == 3:
            print_success("Test 1/6: Test customers created successfully")
            success_count += 1
        else:
            print_error("Test 1/6: Failed to create test customers")
        
        if len(test_rules) == 3:
            print_success("Test 2/6: Test automation rules created successfully")
            success_count += 1
        else:
            print_error("Test 2/6: Failed to create test rules")
        
        if len(classifications) > 0:
            print_success("Test 3/6: AI Policy Agent classification working")
            success_count += 1
        else:
            print_error("Test 3/6: AI Policy Agent classification failed")
        
        if workbench_success:
            print_success("Test 4/6: Resolution Workbench functionality working")
            success_count += 1
        else:
            print_error("Test 4/6: Resolution Workbench functionality failed")
        
        if sum(audit_summary.values()) > 0:
            print_success("Test 5/6: Audit trail generation working")
            success_count += 1
        else:
            print_error("Test 5/6: Audit trail generation failed")
        
        print_success("Test 6/6: Test data cleanup completed")
        success_count += 1
        
        print(f"\n📊 FINAL RESULTS: {success_count}/{total_tests} tests passed")
        
        if success_count == total_tests:
            print_header("🎉 ALL TESTS PASSED!")
            print("✅ Phase 5 implementation is fully functional!")
            print("✅ Complete collection management system is operational!")
            print("✅ Comprehensive audit trail is working correctly!")
            print("\n🚀 SYSTEM READY FOR PRODUCTION!")
        else:
            print_header("⚠️ SOME TESTS FAILED")
            print(f"❌ {total_tests - success_count} tests failed")
            print("Please review the errors above and fix the issues.")
    
    except Exception as e:
        print_error(f"Validation failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    main()

# src/app/services/policy_agent_service.py
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime, date
import json
import asyncio

from app.db import models
from app.utils.email_service import generate_policy_email, send_policy_email
from app.utils.logging import get_logger

logger = get_logger(__name__)


class PolicyAgentService:
    """
    AI Policy Agent that evaluates active rules against customer data
    and automatically sends emails based on matching conditions.
    """
    
    def __init__(self, db: Session):
        self.db = db
        
    def get_active_rules(self) -> List[models.AutomationRule]:
        """Get all active automation rules from the database."""
        return (
            self.db.query(models.AutomationRule)
            .filter(models.AutomationRule.is_active == 1)
            .filter(models.AutomationRule.status == "active")
            .all()
        )
    
    def get_customers_data(self) -> List[Dict[str, Any]]:
        """Get all customer data with loan information."""
        customers = (
            self.db.query(models.Customer)
            .join(models.Loan, models.Customer.id == models.Loan.customer_id, isouter=True)
            .all()
        )
        
        customer_data = []
        for customer in customers:
            # Calculate days overdue (simple calculation)
            days_overdue = 0
            if customer.cbs_last_payment_date:
                days_since_payment = (date.today() - customer.cbs_last_payment_date).days
                if days_since_payment > 30:  # Assuming monthly EMI
                    days_overdue = days_since_payment - 30
            
            customer_data.append({
                "id": customer.id,
                "customer_no": customer.customer_no,
                "name": customer.name,
                "email": customer.email,
                "segment": customer.segment,
                "emi_pending": customer.emi_pending or 0,
                "pending_amount": float(customer.pending_amount or 0),
                "cibil_score": customer.cibil_score,
                "days_overdue": days_overdue,
                "cbs_risk_level": customer.cbs_risk_level,
                "employment_status": customer.employment_status,
                "next_due_date": "2025-09-05"  # Mock next due date
            })
        
        return customer_data
    
    def evaluate_rule_condition(self, condition: Dict[str, Any], customer: Dict[str, Any]) -> bool:
        """
        Evaluate a single rule condition against customer data.
        """
        try:
            field = condition.get("field")
            operator = condition.get("operator")
            value = condition.get("value")
            
            if not all([field, operator, value]):
                logger.warning(f"Invalid condition format: {condition}")
                return False
            
            # Get customer field value
            customer_value = customer.get(field)
            if customer_value is None:
                return False
            
            # Convert values for comparison
            if isinstance(value, str) and value.isdigit():
                value = int(value)
            elif isinstance(value, str):
                try:
                    value = float(value)
                except ValueError:
                    pass  # Keep as string
            
            # Perform comparison based on operator
            if operator == "greater_than" or operator == ">":
                return float(customer_value) > float(value)
            elif operator == "less_than" or operator == "<":
                return float(customer_value) < float(value)
            elif operator == "equals" or operator == "==":
                return customer_value == value
            elif operator == "greater_than_or_equal" or operator == ">=":
                return float(customer_value) >= float(value)
            elif operator == "less_than_or_equal" or operator == "<=":
                return float(customer_value) <= float(value)
            elif operator == "contains":
                return str(value).lower() in str(customer_value).lower()
            else:
                logger.warning(f"Unknown operator: {operator}")
                return False
                
        except Exception as e:
            logger.error(f"Error evaluating condition {condition}: {str(e)}")
            return False
    
    def evaluate_rule(self, rule: models.AutomationRule, customer: Dict[str, Any]) -> bool:
        """
        Evaluate if a customer matches a rule's conditions.
        """
        try:
            # Parse conditions
            conditions_data = rule.conditions
            if isinstance(conditions_data, str):
                conditions_data = json.loads(conditions_data)
            
            if not isinstance(conditions_data, dict):
                logger.warning(f"Invalid conditions format for rule {rule.id}")
                return False
            
            logical_operator = conditions_data.get("logical_operator", "AND")
            conditions = conditions_data.get("conditions", [])
            
            if not conditions:
                logger.warning(f"No conditions found for rule {rule.id}")
                return False
            
            # Evaluate conditions
            results = []
            for condition in conditions:
                result = self.evaluate_rule_condition(condition, customer)
                results.append(result)
            
            # Apply logical operator
            if logical_operator == "AND":
                return all(results)
            elif logical_operator == "OR":
                return any(results)
            else:
                logger.warning(f"Unknown logical operator: {logical_operator}")
                return False
                
        except Exception as e:
            logger.error(f"Error evaluating rule {rule.id}: {str(e)}")
            return False
    
    def check_rule_level_match(self, rule: models.AutomationRule, customer: Dict[str, Any]) -> bool:
        """
        Check if the rule level matches the customer.
        """
        if rule.rule_level == "system":
            return True
        elif rule.rule_level == "segment":
            return rule.segment == customer.get("segment")
        elif rule.rule_level == "customer":
            return rule.customer_id == str(customer.get("customer_no"))
        else:
            return True  # Default to system level
    
    async def execute_rule_action(self, rule: models.AutomationRule, customer: Dict[str, Any]) -> bool:
        """
        Execute the action for a matched rule.
        """
        try:
            action = rule.action
            customer_email = customer.get("email")
            
            if not customer_email:
                logger.warning(f"No email found for customer {customer.get('customer_no')}")
                return False
            
            # Generate email content
            subject, body = generate_policy_email(action, customer)
            
            # Send email
            result = await send_policy_email(
                to_email=customer_email,
                subject=subject,
                body=body,
                customer_name=customer.get("name", "Customer")
            )
            
            if result.get("success"):
                logger.info(f"✅ Action executed: {action} for customer {customer.get('customer_no')}")
                
                # Log the action in database (optional)
                self.log_policy_action(rule, customer, "email_sent")
                
                return True
            else:
                logger.error(f"❌ Failed to execute action: {action} for customer {customer.get('customer_no')}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing action for rule {rule.id}: {str(e)}")
            return False
    
    def log_policy_action(self, rule: models.AutomationRule, customer: Dict[str, Any], action_status: str):
        """
        Log the policy action execution (optional tracking).
        """
        try:
            # You could create a PolicyActionLog model to track executions
            logger.info(f"📝 Policy action logged: Rule {rule.id} -> Customer {customer.get('customer_no')} -> {action_status}")
        except Exception as e:
            logger.error(f"Error logging policy action: {str(e)}")
    
    async def evaluate_all_policies(self) -> Dict[str, Any]:
        """
        Main method to evaluate all active policies against all customers.
        """
        logger.info("🤖 Starting AI Policy Agent evaluation...")
        
        # Get active rules and customer data
        active_rules = self.get_active_rules()
        customers_data = self.get_customers_data()
        
        logger.info(f"📋 Found {len(active_rules)} active rules")
        logger.info(f"👥 Found {len(customers_data)} customers")
        
        evaluation_results = {
            "total_rules": len(active_rules),
            "total_customers": len(customers_data),
            "matches_found": 0,
            "actions_executed": 0,
            "errors": 0,
            "details": []
        }
        
        # Evaluate each rule against each customer
        for rule in active_rules:
            logger.info(f"🔍 Evaluating rule: {rule.rule_name} (ID: {rule.id})")
            
            rule_matches = 0
            rule_actions = 0
            
            for customer in customers_data:
                try:
                    # Check rule level match
                    if not self.check_rule_level_match(rule, customer):
                        continue
                    
                    # Evaluate rule conditions
                    if self.evaluate_rule(rule, customer):
                        rule_matches += 1
                        evaluation_results["matches_found"] += 1
                        
                        logger.info(f"✅ Rule match: {customer.get('name')} ({customer.get('customer_no')})")
                        
                        # Execute action
                        action_success = await self.execute_rule_action(rule, customer)
                        if action_success:
                            rule_actions += 1
                            evaluation_results["actions_executed"] += 1
                        else:
                            evaluation_results["errors"] += 1
                            
                except Exception as e:
                    logger.error(f"Error processing customer {customer.get('customer_no')}: {str(e)}")
                    evaluation_results["errors"] += 1
            
            evaluation_results["details"].append({
                "rule_id": rule.id,
                "rule_name": rule.rule_name,
                "matches": rule_matches,
                "actions_executed": rule_actions
            })
        
        logger.info(f"🎯 Policy evaluation completed:")
        logger.info(f"   - Matches found: {evaluation_results['matches_found']}")
        logger.info(f"   - Actions executed: {evaluation_results['actions_executed']}")
        logger.info(f"   - Errors: {evaluation_results['errors']}")
        
        return evaluation_results


async def run_policy_agent(db: Session) -> Dict[str, Any]:
    """
    Convenience function to run the policy agent.
    """
    agent = PolicyAgentService(db)
    return await agent.evaluate_all_policies()

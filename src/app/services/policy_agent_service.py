# src/app/services/policy_agent_service.py
import json
from datetime import datetime
from sqlalchemy.orm import Session
from app.db import models
from app.services.rule_evaluator import evaluate_customer_rule
from app.utils.email_service import generate_collection_email, send_email
from app.utils.auditing import log_audit_event
from app.utils.logging import get_logger

logger = get_logger(__name__)

class PolicyAgentService:
    def __init__(self, db: Session):
        self.db = db

    def run_agent(self):
        """
        Main function to run the policy agent. It classifies all customers
        and triggers actions for low-risk cases.
        """
        logger.info("🤖 Starting AI Policy Agent run...")
        
        active_rules = self.db.query(models.AutomationRule).filter_by(is_active=1, status="active").all()
        customers = self.db.query(models.Customer).all()

        logger.info(f"Found {len(active_rules)} active rules and {len(customers)} customers to process.")

        processed_count = 0
        for customer in customers:
            try:
                # --- PHASE 5: Process only customers who haven't had a manual action yet ---
                if customer.last_action_taken is None:
                    self._process_customer(customer, active_rules)
                    processed_count += 1
                # --- END PHASE 5 ---
            except Exception as e:
                logger.error(f"Failed to process customer {customer.customer_no}: {e}", exc_info=True)
        
        self.db.commit()
        logger.info(f"✅ AI Policy Agent run finished. Processed {processed_count} customers.")
        
        return {
            "processed_customers": processed_count,
            "active_rules": len(active_rules),
            "timestamp": datetime.utcnow().isoformat()
        }

    def _process_customer(self, customer: models.Customer, rules: list[models.AutomationRule]):
        """Processes a single customer against the rule set."""
        
        # Calculate days past due (DPD)
        dpd = 0
        if customer.cbs_last_payment_date:
            days_since_payment = (datetime.utcnow().date() - customer.cbs_last_payment_date).days
            # Assume 30-day payment cycle, so DPD = days since last payment - 30
            dpd = max(0, days_since_payment - 30)
        
        customer_data = {
            "dpd": dpd,
            "emi_count": customer.emi_pending or 0,
            "collateral": "unsecured",  # Placeholder, extend model if needed
            "segment": customer.segment or "Retail",
            "cibil_score": customer.cibil_score or 0,
            "outstanding_amount": customer.cbs_outstanding_amount or 0,
            "pending_amount": customer.pending_amount or 0,
            "employment_status": customer.employment_status or "Unknown"
        }

        # Find the first matching rule for the customer's segment
        matching_rule = None
        for rule in rules:
            # Rule must match customer segment or be a system-wide rule
            if rule.segment is None or rule.segment == customer.segment:
                # Ensure conditions are loaded as dict
                conditions = json.loads(rule.conditions) if isinstance(rule.conditions, str) else rule.conditions
                rule_dict = {"id": rule.id, "conditions": conditions}

                if evaluate_customer_rule(customer_data, rule_dict):
                    matching_rule = rule
                    break  # Stop at the first match

        if matching_rule:
            # A rule matched, now determine risk and action
            action = matching_rule.action
            
            # Simple logic to map action to risk level. This can be more sophisticated.
            if "Legal Notice" in action or "Block Account" in action:
                risk_level = "High"
            elif "Phone Call" in action or "Escalate" in action:
                risk_level = "Medium"
            else:
                risk_level = "Low"

            # Update customer record
            customer.cbs_risk_level = risk_level
            customer.ai_suggested_action = action
            
            # --- PHASE 5: ENHANCED AUDIT LOGGING FOR AI CLASSIFICATION ---
            log_audit_event(
                self.db, "System", "AI Classification", "Customer", customer.customer_no,
                summary=f"Classified as {risk_level} risk by rule '{matching_rule.rule_name}'.",
                details={
                    "suggested_action": action, 
                    "rule_id": matching_rule.id,
                    "rule_name": matching_rule.rule_name,
                    "customer_segment": customer.segment,
                    "outstanding_amount": customer.cbs_outstanding_amount,
                    "dpd": customer_data.get("dpd", 0)
                }
            )
            # --- END PHASE 5 ---

            # If low risk, perform automated action
            if risk_level == "Low" and "Reminder" in action:
                self._perform_automated_action(customer, action)
        else:
            # No rules matched, classify as Low risk by default
            customer.cbs_risk_level = "Low"
            customer.ai_suggested_action = "Monitor"
            
            # --- PHASE 5: ENHANCED AUDIT LOGGING FOR DEFAULT CLASSIFICATION ---
            log_audit_event(
                self.db, "System", "AI Classification", "Customer", customer.customer_no,
                summary="No specific rule matched. Classified as Low risk for monitoring.",
                details={
                    "suggested_action": "Monitor",
                    "customer_segment": customer.segment,
                    "outstanding_amount": customer.cbs_outstanding_amount,
                    "dpd": customer_data.get("dpd", 0),
                    "rules_evaluated": len(rules)
                }
            )
            # --- END PHASE 5 ---

    def _perform_automated_action(self, customer: models.Customer, action: str):
        """Sends an automated email for a low-risk customer."""
        logger.info(f"Performing automated action '{action}' for low-risk customer {customer.customer_no}")
        
        if not customer.email:
            logger.warning(f"Customer {customer.customer_no} has no email address. Skipping automated email.")
            customer.last_action_taken = f"Automated Action Skipped: No Email"
            return
        
        try:
            subject, body = generate_collection_email(action, customer)
            
            # Send email (fire-and-forget)
            send_email(
                to_email=customer.email,
                subject=subject,
                body=body
            )
            
            action_summary = f"Automated Email: {action}"
            customer.last_action_taken = action_summary
            
            # --- PHASE 5: ENHANCED AUDIT LOGGING FOR AUTOMATED ACTION ---
            log_audit_event(
                self.db, "System", "Automated Action", "Customer", customer.customer_no,
                summary=action_summary,
                details={
                    "recipient": customer.email,
                    "subject": subject,
                    "action_type": action,
                    "email_template": "collection_reminder",
                    "automation_trigger": "low_risk_classification"
                }
            )
            # --- END PHASE 5 ---
        except Exception as e:
            logger.error(f"Failed to send automated email to customer {customer.customer_no}: {e}")
            customer.last_action_taken = f"Automated Email Failed: {str(e)[:100]}"


# Convenience function for API endpoints
async def run_policy_agent(db: Session):
    """
    Async wrapper for running the policy agent from API endpoints.
    """
    agent = PolicyAgentService(db)
    return agent.run_agent()
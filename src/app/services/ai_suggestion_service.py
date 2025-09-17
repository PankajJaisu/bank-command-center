# src/app/services/ai_suggestion_service.py
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime, date
import json

from app.db import models
from app.utils.logging import get_logger
from app.config import settings
from app.modules.copilot.agent import client

logger = get_logger(__name__)


class AISuggestionService:
    """
    AI Suggestion Service that generates personalized recommendations for customers
    based on their contract notes, customer details, and applicable rules.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_customer_suggestion(self, customer_id: int) -> Dict[str, Any]:
        """
        Generate AI-powered suggestions for a specific customer based on:
        - Customer details (CIBIL score, payment history, risk level)
        - Contract note information (EMI amount, due dates, terms)
        - Applicable automation rules and policies
        """
        try:
            # Get customer data
            customer = self.db.query(models.Customer).filter(
                models.Customer.id == customer_id
            ).first()
            
            if not customer:
                return {"error": "Customer not found"}
            
            # Get contract note if available (through customer relationship)
            contract_note = customer.contract_note
            
            # Get applicable automation rules
            applicable_rules = self._get_applicable_rules(customer)
            
            # Generate AI suggestion
            suggestion = self._generate_ai_suggestion(customer, contract_note, applicable_rules)
            
            return {
                "customer_id": customer_id,
                "customer_name": customer.name,
                "suggestion": suggestion,
                "generated_at": datetime.utcnow().isoformat(),
                "confidence_score": self._calculate_confidence_score(customer, contract_note)
            }
            
        except Exception as e:
            logger.error(f"Error generating customer suggestion for {customer_id}: {str(e)}")
            return {"error": f"Failed to generate suggestion: {str(e)}"}
    
    def _get_applicable_rules(self, customer: models.Customer) -> List[models.AutomationRule]:
        """Get automation rules that apply to this customer."""
        rules = []
        
        # Get system-level rules
        system_rules = self.db.query(models.AutomationRule).filter(
            models.AutomationRule.is_active == 1,
            models.AutomationRule.rule_level == "system"
        ).all()
        rules.extend(system_rules)
        
        # Get segment-level rules
        if customer.segment:
            segment_rules = self.db.query(models.AutomationRule).filter(
                models.AutomationRule.is_active == 1,
                models.AutomationRule.rule_level == "segment",
                models.AutomationRule.segment == customer.segment
            ).all()
            rules.extend(segment_rules)
        
        # Get customer-specific rules
        customer_rules = self.db.query(models.AutomationRule).filter(
            models.AutomationRule.is_active == 1,
            models.AutomationRule.rule_level == "customer",
            models.AutomationRule.customer_id == str(customer.customer_no)
        ).all()
        rules.extend(customer_rules)
        
        return rules
    
    def _generate_ai_suggestion(
        self, 
        customer: models.Customer, 
        contract_note: Optional[models.ContractNote],
        applicable_rules: List[models.AutomationRule]
    ) -> Dict[str, Any]:
        """Generate AI-powered suggestion using Gemini."""
        
        if not client:
            return self._generate_fallback_suggestion(customer, contract_note)
        
        try:
            # Calculate days overdue from available data (fallback to 0 if not calculable)
            days_overdue = 0
            if customer.cbs_last_payment_date:
                from datetime import date
                days_overdue = (date.today() - customer.cbs_last_payment_date).days
            elif customer.cbs_risk_level == "red":
                days_overdue = 90  # Assume high risk means significant overdue
            elif customer.cbs_risk_level == "amber":
                days_overdue = 30  # Assume medium risk means moderate overdue
            
            # Prepare customer context
            customer_context = {
                "customer_no": customer.customer_no,
                "name": customer.name,
                "cibil_score": customer.cibil_score,
                "risk_level": customer.cbs_risk_level,
                "outstanding_amount": customer.cbs_outstanding_amount,
                "pending_amount": customer.pending_amount,
                "emi_pending": customer.emi_pending,
                "days_overdue": days_overdue,
                "employment_status": customer.employment_status,
                "segment": customer.segment,
                "email": customer.email,
                "phone": customer.phone
            }
            
            # Prepare contract context
            contract_context = {}
            if contract_note:
                contract_context = {
                    "emi_amount": contract_note.contract_emi_amount,
                    "due_day": contract_note.contract_due_day,
                    "late_fee_percent": contract_note.contract_late_fee_percent,
                    "loan_amount": contract_note.contract_loan_amount,
                    "tenure_months": contract_note.contract_tenure_months,
                    "interest_rate": contract_note.contract_interest_rate
                }
            
            # Prepare rules context
            rules_context = []
            for rule in applicable_rules:
                rules_context.append({
                    "name": rule.name,
                    "description": rule.description,
                    "action": rule.action,
                    "risk_level": rule.risk_level,
                    "priority": rule.priority
                })
            
            # Create AI prompt
            prompt = f"""
            You are a senior collection specialist AI assistant. Analyze the following customer data and provide personalized collection recommendations.

            **Customer Information:**
            {json.dumps(customer_context, indent=2)}

            **Contract Details:**
            {json.dumps(contract_context, indent=2)}

            **Applicable Rules:**
            {json.dumps(rules_context, indent=2)}

            **Instructions:**
            1. Analyze the customer's risk profile, payment behavior, and contract terms
            2. Consider the applicable rules and their recommended actions
            3. Generate a personalized collection strategy that balances recovery with customer relationship
            4. Provide specific, actionable recommendations
            5. Include suggested email content if email communication is recommended

            **Response Format (JSON):**
            {{
                "risk_assessment": "Brief risk assessment of the customer",
                "recommended_action": "Primary recommended action (e.g., 'Send Reminder', 'Make Phone Call', 'Send Legal Notice')",
                "strategy": "Detailed collection strategy explanation",
                "priority_level": "high|medium|low",
                "suggested_timeline": "When to take action (e.g., 'Within 24 hours', 'Within 3 days')",
                "email_subject": "Suggested email subject line if email is recommended",
                "email_content": "Suggested email content if email is recommended",
                "alternative_actions": ["List of alternative actions if primary fails"],
                "success_probability": "Estimated success probability (e.g., '75%')",
                "notes": "Additional notes or considerations"
            }}

            Generate the recommendation now:
            """
            
            # Call Gemini API
            response = client.generate_content(prompt)
            
            if response and response.text:
                # Try to parse JSON response
                try:
                    suggestion_data = json.loads(response.text.strip())
                    return suggestion_data
                except json.JSONDecodeError:
                    # If JSON parsing fails, return the text as strategy
                    return {
                        "risk_assessment": "AI analysis completed",
                        "recommended_action": "Review Required",
                        "strategy": response.text.strip(),
                        "priority_level": "medium",
                        "suggested_timeline": "Within 24 hours",
                        "success_probability": "Unknown"
                    }
            else:
                return self._generate_fallback_suggestion(customer, contract_note)
                
        except Exception as e:
            logger.error(f"Error calling Gemini API for suggestion: {str(e)}")
            return self._generate_fallback_suggestion(customer, contract_note)
    
    def _generate_fallback_suggestion(
        self, 
        customer: models.Customer, 
        contract_note: Optional[models.ContractNote]
    ) -> Dict[str, Any]:
        """Generate rule-based fallback suggestion when AI is not available."""
        
        # Calculate days overdue from available data
        days_overdue = 0
        if customer.cbs_last_payment_date:
            from datetime import date
            days_overdue = (date.today() - customer.cbs_last_payment_date).days
        elif customer.cbs_risk_level == "red":
            days_overdue = 90  # Assume high risk means significant overdue
        elif customer.cbs_risk_level == "amber":
            days_overdue = 30  # Assume medium risk means moderate overdue
        
        # Determine risk level and recommended action
        risk_level = customer.cbs_risk_level or "yellow"
        pending_amount = customer.pending_amount or 0
        
        if risk_level == "red" or days_overdue > 90:
            recommended_action = "Send Legal Notice"
            priority_level = "high"
            timeline = "Within 24 hours"
            strategy = f"Customer {customer.name} is high-risk with {days_overdue} days overdue and ₹{pending_amount:,.2f} pending. Immediate legal action consideration required."
        elif risk_level == "amber" or days_overdue > 30:
            recommended_action = "Make Phone Call"
            priority_level = "medium"
            timeline = "Within 48 hours"
            strategy = f"Customer {customer.name} requires direct contact. Phone call recommended to discuss payment plan and resolve ₹{pending_amount:,.2f} outstanding amount."
        else:
            recommended_action = "Send Reminder"
            priority_level = "low"
            timeline = "Within 3 days"
            strategy = f"Customer {customer.name} needs gentle reminder. Send friendly payment reminder for ₹{pending_amount:,.2f} due amount."
        
        return {
            "risk_assessment": f"Customer classified as {risk_level} risk with {days_overdue} days overdue",
            "recommended_action": recommended_action,
            "strategy": strategy,
            "priority_level": priority_level,
            "suggested_timeline": timeline,
            "email_subject": f"Payment Reminder - Account {customer.customer_no}",
            "email_content": f"Dear {customer.name},\n\nThis is a reminder regarding your account {customer.customer_no}. Please contact us to discuss your payment options.\n\nBest regards,\nCollections Team",
            "alternative_actions": ["Send Email", "Field Visit", "Payment Plan"],
            "success_probability": "65%",
            "notes": "Generated using rule-based fallback system"
        }
    
    def _calculate_confidence_score(
        self, 
        customer: models.Customer, 
        contract_note: Optional[models.ContractNote]
    ) -> float:
        """Calculate confidence score for the suggestion based on available data."""
        score = 0.5  # Base score
        
        # Add points for available data
        if customer.cibil_score:
            score += 0.1
        if customer.cbs_risk_level:
            score += 0.1
        if customer.cbs_last_payment_date:  # Use last payment date instead of days_overdue
            score += 0.1
        if customer.pending_amount:
            score += 0.1
        if contract_note:
            score += 0.2
        
        return min(score, 1.0)
    
    def generate_email_content(
        self, 
        customer_id: int, 
        action_type: str,
        custom_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate email content for a specific customer and action type."""
        
        try:
            customer = self.db.query(models.Customer).filter(
                models.Customer.id == customer_id
            ).first()
            
            if not customer:
                return {"error": "Customer not found"}
            
            # Get contract note for additional context (through customer relationship)
            contract_note = customer.contract_note
            
            # Generate AI-powered email content
            email_content = self._generate_ai_email_content(customer, contract_note, action_type, custom_message)
            
            return {
                "customer_id": customer_id,
                "action_type": action_type,
                "email_content": email_content,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating email content for customer {customer_id}: {str(e)}")
            return {"error": f"Failed to generate email content: {str(e)}"}
    
    def _generate_ai_email_content(
        self,
        customer: models.Customer,
        contract_note: Optional[models.ContractNote],
        action_type: str,
        custom_message: Optional[str] = None
    ) -> Dict[str, str]:
        """Generate AI-powered email content."""
        
        if not client:
            return self._generate_fallback_email_content(customer, action_type)
        
        try:
            # Calculate days overdue from available data
            days_overdue = 0
            if customer.cbs_last_payment_date:
                from datetime import date
                days_overdue = (date.today() - customer.cbs_last_payment_date).days
            elif customer.cbs_risk_level == "red":
                days_overdue = 90
            elif customer.cbs_risk_level == "amber":
                days_overdue = 30
            
            # Prepare context
            customer_context = {
                "name": customer.name,
                "customer_no": customer.customer_no,
                "pending_amount": customer.pending_amount or 0,
                "days_overdue": days_overdue,
                "emi_pending": customer.emi_pending or 0
            }
            
            contract_context = {}
            if contract_note:
                contract_context = {
                    "emi_amount": contract_note.contract_emi_amount,
                    "due_day": contract_note.contract_due_day
                }
            
            prompt = f"""
            Generate a professional, empathetic email for a bank collection scenario.

            **Customer Details:**
            {json.dumps(customer_context, indent=2)}

            **Contract Details:**
            {json.dumps(contract_context, indent=2)}

            **Action Type:** {action_type}
            **Custom Message:** {custom_message or "None"}

            **Instructions:**
            1. Create a professional, respectful tone
            2. Be clear about the outstanding amount and consequences
            3. Offer solutions and payment options
            4. Include contact information for assistance
            5. Maintain empathy while being firm about payment obligations

            **Response Format (JSON):**
            {{
                "subject": "Professional email subject line",
                "body": "Complete email body in HTML format with proper formatting"
            }}

            Generate the email now:
            """
            
            response = client.generate_content(prompt)
            
            if response and response.text:
                try:
                    email_data = json.loads(response.text.strip())
                    return email_data
                except json.JSONDecodeError:
                    return self._generate_fallback_email_content(customer, action_type)
            else:
                return self._generate_fallback_email_content(customer, action_type)
                
        except Exception as e:
            logger.error(f"Error generating AI email content: {str(e)}")
            return self._generate_fallback_email_content(customer, action_type)
    
    def _generate_fallback_email_content(self, customer: models.Customer, action_type: str) -> Dict[str, str]:
        """Generate fallback email content using templates."""
        
        from app.utils.email_service import generate_policy_email
        
        # Calculate days overdue from available data
        days_overdue = 0
        if customer.cbs_last_payment_date:
            from datetime import date
            days_overdue = (date.today() - customer.cbs_last_payment_date).days
        elif customer.cbs_risk_level == "red":
            days_overdue = 90
        elif customer.cbs_risk_level == "amber":
            days_overdue = 30
        
        customer_data = {
            "name": customer.name,
            "customer_no": customer.customer_no,
            "pending_amount": customer.pending_amount or 0,
            "emi_pending": customer.emi_pending or 0,
            "days_overdue": days_overdue
        }
        
        subject, body = generate_policy_email(action_type, customer_data)
        
        return {
            "subject": subject,
            "body": body
        }

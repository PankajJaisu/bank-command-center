# src/app/services/ai_suggestion_service.py
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime, date
import json

from app.db import models
from app.utils.logging import get_logger
from app.config import settings
from app.modules.copilot.agent import client
from google import genai

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
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating customer suggestion for {customer_id}: {str(e)}")
            return {"error": f"Failed to generate suggestion: {str(e)}"}
    
    def _get_applicable_rules(self, customer: models.Customer) -> Dict[str, List]:
        """Get both collection rules and automation rules that apply to this customer."""
        rules = {
            "collection_rules": [],
            "automation_rules": []
        }
        
        # Get active collection rules (from policy documents) - PRIORITY
        collection_rules = self.db.query(models.CollectionRule).filter(
            models.CollectionRule.is_active == True
        ).all()
        rules["collection_rules"] = collection_rules
        
        # Get system-level automation rules
        system_rules = self.db.query(models.AutomationRule).filter(
            models.AutomationRule.is_active == 1,
            models.AutomationRule.rule_level == "system"
        ).all()
        rules["automation_rules"].extend(system_rules)
        
        # Get segment-level automation rules
        if customer.segment:
            segment_rules = self.db.query(models.AutomationRule).filter(
                models.AutomationRule.is_active == 1,
                models.AutomationRule.rule_level == "segment",
                models.AutomationRule.segment == customer.segment
            ).all()
            rules["automation_rules"].extend(segment_rules)
        
        # Get customer-specific automation rules
        customer_rules = self.db.query(models.AutomationRule).filter(
            models.AutomationRule.is_active == 1,
            models.AutomationRule.rule_level == "customer",
            models.AutomationRule.customer_id == str(customer.customer_no)
        ).all()
        rules["automation_rules"].extend(customer_rules)
        
        return rules
    
    def _generate_ai_suggestion(
        self, 
        customer: models.Customer, 
        contract_note: Optional[models.ContractNote],
        applicable_rules: Dict[str, List]
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
            
            # Prepare rules context - prioritize collection rules from policy documents
            rules_context = {
                "collection_rules": [],
                "automation_rules": []
            }
            
            # Process collection rules (from policy documents) - PRIORITY
            for rule in applicable_rules.get("collection_rules", []):
                try:
                    # Parse conditions and actions if they're JSON strings
                    conditions = rule.conditions
                    actions = rule.actions
                    if isinstance(conditions, str):
                        import json
                        conditions = json.loads(conditions)
                    if isinstance(actions, str):
                        actions = json.loads(actions)
                    
                    rules_context["collection_rules"].append({
                        "rule_name": rule.rule_name,
                        "rule_type": rule.rule_type,
                        "conditions": conditions,
                        "actions": actions,
                        "priority": rule.priority,
                        "description": rule.description,
                        "success_rate": rule.success_rate
                    })
                except Exception as e:
                    logger.warning(f"Failed to parse collection rule {rule.id}: {str(e)}")
            
            # Process automation rules (legacy)
            for rule in applicable_rules.get("automation_rules", []):
                rules_context["automation_rules"].append({
                    "rule_name": rule.rule_name,
                    "description": rule.description,
                    "action": rule.action,
                    "conditions": rule.conditions
                })
            
            # Create AI prompt
            prompt = f"""
            You are a senior collection specialist AI assistant. Analyze the following customer data and provide personalized collection recommendations.

            **Customer Information:**
            {json.dumps(customer_context, indent=2)}

            **Contract Details:**
            {json.dumps(contract_context, indent=2)}

            **Active Collection Rules (PRIORITY - Use These First):**
            {json.dumps(rules_context.get("collection_rules", []), indent=2)}

            **Legacy Automation Rules:**
            {json.dumps(rules_context.get("automation_rules", []), indent=2)}

            **CRITICAL INSTRUCTIONS:**
            1. **FIRST PRIORITY**: Check if any active Collection Rules match this customer's situation
               - Collection Rules are derived from bank policy documents and must be followed
               - Match customer conditions (days overdue, risk level, amount) to rule conditions
               - If a Collection Rule matches, use its specified actions and recommendations
            
            2. **SECOND PRIORITY**: If no Collection Rules match, use these guidelines:
               - HIGH PRIORITY (90+ days overdue OR red risk level): Recommend "Send Legal Notice"
               - MEDIUM PRIORITY (30-89 days overdue OR amber risk level): Recommend "Make Phone Call" or "Payment Plan"
               - LOW PRIORITY (<30 days overdue OR green/yellow risk level): Recommend "Send SMS" or "Email Reminder"
            
            3. **Always reference which rule(s) influenced your recommendation**
            4. Keep the strategy concise and focused (2-3 sentences maximum)
            5. Base recommendations on customer's specific situation and applicable rules

            **Response Format (JSON):**
            {{
                "risk_assessment": "Brief 1-sentence risk assessment",
                "recommended_action": "ONE specific action (e.g., 'Send Legal Notice' for high priority, 'Make Phone Call' for medium, 'Send SMS' for low)",
                "strategy": "Concise 2-3 sentence strategy explanation",
                "priority_level": "high|medium|low",
                "suggested_timeline": "Timeline (e.g., 'Within 24 hours', 'Within 3 days')",
                "specific_action_steps": ["Step 1: Brief action", "Step 2: Brief action", "Step 3: Brief action"],
                "applied_rule": "Name of the Collection Rule that was applied, or 'Default Guidelines' if no specific rule matched"
            }}

            Generate the recommendation now:
            """
            
            # Call Gemini API
            logger.info(f"=== AI SUGGESTION API CALL DEBUG ===")
            logger.info(f"Customer ID: {customer.customer_no}")
            logger.info(f"Customer Context: {json.dumps(customer_context, indent=2)}")
            logger.info(f"Contract Context: {json.dumps(contract_context, indent=2)}")
            logger.info(f"Rules Context: {json.dumps(rules_context, indent=2)}")
            logger.info(f"Prompt sent to Gemini: {prompt}")
            
            # Use the Google GenAI SDK client
            response = client.models.generate_content(
                model='gemini-1.5-flash',
                contents=prompt
            )
            
            if response and response.text:
                logger.info(f"Gemini API Response: {response.text}")
            else:
                logger.warning("No response from Gemini API")
            
            if response and response.text:
                # Try to parse JSON response
                try:
                    # Clean the response text to extract JSON
                    response_text = response.text.strip()
                    
                    # If response contains JSON within markdown code blocks, extract it
                    if "```json" in response_text:
                        start = response_text.find("```json") + 7
                        end = response_text.find("```", start)
                        response_text = response_text[start:end].strip()
                    elif "```" in response_text:
                        start = response_text.find("```") + 3
                        end = response_text.rfind("```")
                        response_text = response_text[start:end].strip()
                    
                    suggestion_data = json.loads(response_text)
                    
                    # Ensure strategy is concise (limit to 200 characters)
                    if "strategy" in suggestion_data and len(suggestion_data["strategy"]) > 200:
                        suggestion_data["strategy"] = suggestion_data["strategy"][:197] + "..."
                    
                    return suggestion_data
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse AI response as JSON: {str(e)}")
                    logger.error(f"Raw response: {response.text}")
                    # Return fallback instead of raw text
                    return self._generate_fallback_suggestion(customer, contract_note)
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
            strategy = f"High-risk customer with {days_overdue} days overdue. Immediate legal action required for ₹{pending_amount:,.2f}."
            action_steps = [
                "Contact customer immediately by phone",
                "Send formal legal notice via registered mail",
                "Document all communication attempts",
                "Escalate to legal team if no response within 7 days"
            ]
        elif risk_level == "amber" or days_overdue > 30:
            recommended_action = "Make Phone Call"
            priority_level = "medium"
            timeline = "Within 48 hours"
            strategy = f"Direct contact needed. Phone call to discuss payment plan for ₹{pending_amount:,.2f} outstanding."
            action_steps = [
                "Call customer to discuss payment status",
                "Offer flexible payment plan options",
                "Send payment plan agreement via email",
                "Schedule follow-up call in 7 days"
            ]
        else:
            recommended_action = "Send Payment Reminder"
            priority_level = "low"
            timeline = "Within 3 days"
            strategy = f"Send friendly payment reminder for ₹{pending_amount:,.2f} due amount."
            action_steps = [
                "Send friendly payment reminder email",
                "Include payment options and contact details",
                "Follow up with SMS reminder after 3 days",
                "Monitor account for payment activity"
            ]
        
        return {
            "risk_assessment": f"Customer classified as {risk_level} risk with {days_overdue} days overdue",
            "recommended_action": recommended_action,
            "strategy": strategy,
            "priority_level": priority_level,
            "suggested_timeline": timeline,
            "specific_action_steps": action_steps,
            "applied_rule": "Default Guidelines (Fallback)"
        }
    
    
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
            Generate a professional collection ticket for a collection agent. This is an INTERNAL work assignment, NOT a customer email.

            **Customer Details:**
            {json.dumps(customer_context, indent=2)}

            **Contract Details:**
            {json.dumps(contract_context, indent=2)}

            **Action Type:** {action_type}
            **Custom Message:** {custom_message or "None"}

            **CRITICAL INSTRUCTIONS - READ CAREFULLY:**
            1. This is an INTERNAL work ticket for the collection agent - DO NOT address the customer
            2. NEVER start with "Dear {customer.name}" or "Dear Customer" or "Dear Sir/Madam"
            3. ALWAYS start with "Dear Collection Agent" - this is mandatory
            4. Write as if you are the system assigning work to the collection agent
            5. Include what the agent should do to contact/handle the customer
            6. Provide customer details for the agent's reference only
            7. The customer will NEVER see this email - it's purely internal

            **PRIORITY-BASED ACTIONS:**
            - HIGH PRIORITY (90+ days overdue or red risk): Recommend "Legal Notice" as primary action
            - MEDIUM PRIORITY (30-90 days or amber risk): Recommend "Payment Plan Negotiation"
            - LOW PRIORITY (<30 days or green risk): Recommend "Friendly Reminder Call"

            **EXAMPLE FORMAT (MANDATORY TO FOLLOW):**
            Subject: "Collection Assignment - Amit Sharma (CUST-8802) - MEDIUM PRIORITY"
            Body: "Dear Collection Agent,

            You have been assigned a new collection case requiring immediate attention.

            CUSTOMER INFORMATION:
            • Name: Amit Sharma
            • Customer No: CUST-8802
            • Outstanding Amount: ₹75,000
            • Days Overdue: 45 days
            • Risk Level: Medium

            YOUR ASSIGNMENT:
            Please contact this customer to discuss payment plan options. The customer has missed 2 EMI payments and requires immediate follow-up.

            ACTION REQUIRED:
            1. Call customer at [phone number] between 9 AM - 6 PM
            2. Discuss payment restructuring options
            3. Document conversation outcome in system
            4. Schedule follow-up if needed

            IMPORTANT NOTES:
            - Customer has shown willingness to pay in past
            - Avoid aggressive language
            - Focus on finding mutually acceptable solution

            Please handle this case within 24 hours and update the system with results.

            Best regards,
            Collections Management System"

            **Response Format (JSON):**
            {{
                "subject": "Collection Assignment - [Customer Name] ([Customer No]) - [Priority Level]",
                "body": "Dear Collection Agent,\\n\\nYou have been assigned a new collection case requiring attention.\\n\\nCUSTOMER INFORMATION:\\n[Customer details for agent reference]\\n\\nYOUR ASSIGNMENT:\\n[What the agent needs to do]\\n\\nACTION REQUIRED:\\n[Step by step actions]\\n\\nBest regards,\\nCollections Management System"
            }}

            Generate the collection ticket now:
            """
            
            logger.info(f"=== EMAIL GENERATION API CALL DEBUG ===")
            logger.info(f"Customer ID: {customer_id}")
            logger.info(f"Action Type: {action_type}")
            logger.info(f"Customer Context: {json.dumps(customer_context, indent=2)}")
            logger.info(f"Contract Context: {json.dumps(contract_context, indent=2)}")
            logger.info(f"Email Prompt sent to Gemini: {prompt}")
            
            # Use the Google GenAI SDK client for email generation
            response = client.models.generate_content(
                model='gemini-1.5-flash',
                contents=prompt
            )
            
            if response and response.text:
                logger.info(f"Email Generation API Response: {response.text}")
            else:
                logger.warning("No response from Gemini API for email generation")
            
            # TEMPORARY FIX: AI keeps generating customer emails despite instructions
            # Force use of fallback template until AI behavior is corrected
            logger.info("Using fallback email template to ensure proper collection agent format")
            return self._generate_fallback_email_content(customer, action_type)
            
            # TODO: Re-enable AI generation once it consistently follows instructions
            # if response and response.text:
            #     try:
            #         # Extract JSON from markdown code blocks if present
            #         response_text = response.text.strip()
            #         if "```json" in response_text:
            #             start = response_text.find("```json") + 7
            #             end = response_text.find("```", start)
            #             response_text = response_text[start:end].strip()
            #         elif "```" in response_text:
            #             start = response_text.find("```") + 3
            #             end = response_text.find("```", start)
            #             response_text = response_text[start:end].strip()
            #         
            #         email_data = json.loads(response_text)
            #         
            #         # Validate that the email is addressed to collection agent, not customer
            #         if email_data.get("body"):
            #             body = email_data["body"]
            #             # Check if it's incorrectly addressed to customer (multiple variations)
            #             customer_greetings = [
            #                 f"Dear {customer.name}",
            #                 f"Dear Mr. {customer.name.split()[-1] if customer.name else ''}",
            #                 f"Dear Ms. {customer.name.split()[-1] if customer.name else ''}",
            #                 f"Hello {customer.name}",
            #                 "Dear Customer",
            #                 "Dear Sir/Madam"
            #             ]
            #             
            #             is_customer_addressed = any(greeting in body for greeting in customer_greetings if greeting.strip())
            #             
            #             if is_customer_addressed:
            #                 logger.warning(f"AI generated customer-addressed email, using fallback")
            #                 return self._generate_fallback_email_content(customer, action_type)
            #             
            #             # Ensure it starts with "Dear Collection Agent"
            #             if not body.startswith("Dear Collection Agent"):
            #                 logger.warning(f"AI email doesn't start with 'Dear Collection Agent', using fallback")
            #                 return self._generate_fallback_email_content(customer, action_type)
            #         
            #         return email_data
            #     except json.JSONDecodeError:
            #         logger.warning("Failed to parse AI email response as JSON, using fallback")
            #         return self._generate_fallback_email_content(customer, action_type)
            # else:
            #     return self._generate_fallback_email_content(customer, action_type)
                
        except Exception as e:
            logger.error(f"Error generating AI email content: {str(e)}")
            return self._generate_fallback_email_content(customer, action_type)
    
    def _generate_fallback_email_content(self, customer: models.Customer, action_type: str) -> Dict[str, str]:
        """Generate fallback collection ticket content for collection agent."""
        
        # Calculate days overdue from available data
        days_overdue = 0
        if customer.cbs_last_payment_date:
            from datetime import date
            days_overdue = (date.today() - customer.cbs_last_payment_date).days
        elif customer.cbs_risk_level == "red":
            days_overdue = 90
        elif customer.cbs_risk_level == "amber":
            days_overdue = 30
        
        # Determine priority based on risk level and days overdue
        if customer.cbs_risk_level == "red" or days_overdue > 90:
            priority = "HIGH PRIORITY"
            priority_color = "red"
        elif customer.cbs_risk_level == "amber" or days_overdue > 30:
            priority = "MEDIUM PRIORITY"
            priority_color = "orange"
        else:
            priority = "LOW PRIORITY"
            priority_color = "green"
        
        subject = f"Collection Assignment - {customer.name} ({customer.customer_no}) - {priority}"
        
        # Update action steps based on priority
        if priority == "HIGH PRIORITY":
            action_steps = f"""1. Initiate Legal Notice proceedings immediately
2. Contact customer at phone: {customer.phone or 'Not available'} to inform about legal action
3. Document all communication and legal proceedings in the system
4. Coordinate with legal department for next steps
5. Follow up within 24 hours on legal notice status"""
        else:
            action_steps = f"""1. Contact customer at phone: {customer.phone or 'Not available'}
2. Discuss payment options and create payment plan
3. Document all communication in the system
4. Follow up within 48 hours if no response"""

        body = f"""<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: {priority_color}; border-bottom: 2px solid {priority_color}; padding-bottom: 10px;">
        🎫 COLLECTION TICKET - {priority}
    </h2>
    
    <p><strong>Dear Collection Agent,</strong></p>
    
    <p>A new collection case has been assigned to you with <strong style="color: {priority_color};">{priority}</strong> priority.</p>
    
    <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #007bff; margin: 20px 0;">
        <h3 style="color: #007bff; margin-top: 0;">📋 CUSTOMER DETAILS</h3>
        <ul style="list-style: none; padding: 0;">
            <li style="margin: 8px 0;"><strong>Name:</strong> {customer.name}</li>
            <li style="margin: 8px 0;"><strong>Customer No:</strong> {customer.customer_no}</li>
            <li style="margin: 8px 0;"><strong>Risk Level:</strong> <span style="color: {priority_color}; font-weight: bold;">{customer.cbs_risk_level or 'Unknown'}</span></li>
            <li style="margin: 8px 0;"><strong>Days Overdue:</strong> {days_overdue} days</li>
            <li style="margin: 8px 0;"><strong>Pending Amount:</strong> <strong style="color: #dc3545;">₹{(customer.pending_amount or 0):,.2f}</strong></li>
            <li style="margin: 8px 0;"><strong>EMIs Pending:</strong> {customer.emi_pending or 0}</li>
            <li style="margin: 8px 0;"><strong>CIBIL Score:</strong> {customer.cibil_score or 'N/A'}</li>
        </ul>
    </div>
    
    <div style="background-color: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 20px 0;">
        <h3 style="color: #856404; margin-top: 0;">⚡ RECOMMENDED ACTION</h3>
        <p style="font-size: 16px; font-weight: bold; color: #856404;">{action_type}</p>
    </div>
    
    <div style="background-color: #d1ecf1; padding: 15px; border-left: 4px solid #17a2b8; margin: 20px 0;">
        <h3 style="color: #0c5460; margin-top: 0;">📝 ACTION STEPS FOR YOU</h3>
        <ol style="padding-left: 20px;">
            {chr(10).join(f'<li style="margin: 8px 0;">{step}</li>' for step in action_steps.split(chr(10)))}
        </ol>
    </div>
    
    <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #6c757d; margin: 20px 0;">
        <h3 style="color: #495057; margin-top: 0;">📞 CUSTOMER CONTACT DETAILS</h3>
        <ul style="list-style: none; padding: 0;">
            <li style="margin: 8px 0;"><strong>Phone:</strong> {customer.phone or 'Not available'}</li>
            <li style="margin: 8px 0;"><strong>Email:</strong> {customer.email or 'Not available'}</li>
            <li style="margin: 8px 0;"><strong>Address:</strong> {customer.address or 'Not available'}</li>
        </ul>
    </div>
    
    <div style="background-color: #d4edda; padding: 15px; border-left: 4px solid #28a745; margin: 20px 0;">
        <p style="margin: 0; color: #155724;"><strong>⏰ Please take action within the recommended timeline and update the case status in the system.</strong></p>
    </div>
    
    <hr style="margin: 30px 0; border: none; border-top: 1px solid #dee2e6;">
    
    <p style="color: #6c757d; font-size: 14px;">
        <strong>Best regards,</strong><br>
        Collections Management System<br>
        <em>Ticket generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</em>
    </p>
</body>
</html>"""
        
        return {
            "subject": subject,
            "body": body
        }

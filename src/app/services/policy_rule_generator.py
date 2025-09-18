"""
Policy Rule Generator Service

This service uses AI to analyze bank policy documents and generate actionable collection rules
that map specific customer conditions to appropriate collection actions.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from app.db import models
from app.modules.copilot.agent import client
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class PolicyRuleGenerator:
    """
    Service to generate collection rules from policy documents using AI analysis.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_rules_from_policy(self, policy_content: str, policy_type: str = "collection") -> Dict[str, Any]:
        """
        Generate actionable collection rules from a policy document.
        
        Args:
            policy_content: The full text content of the policy document
            policy_type: Type of policy (collection, repossession, etc.)
            
        Returns:
            Dictionary containing generated rules and metadata
        """
        try:
            logger.info(f"=== POLICY RULE GENERATION START ===")
            logger.info(f"Policy type: {policy_type}")
            logger.info(f"Policy content length: {len(policy_content)} characters")
            
            # Create comprehensive prompt for rule generation
            prompt = self._create_rule_generation_prompt(policy_content, policy_type)
            
            # Call Gemini AI for rule generation
            response = client.models.generate_content(
                model='gemini-1.5-flash',
                contents=prompt
            )
            
            if response and response.text:
                logger.info(f"AI Response received: {len(response.text)} characters")
                
                # Parse the AI response
                rules_data = self._parse_ai_response(response.text)
                
                # Validate and structure the rules
                structured_rules = self._structure_rules(rules_data, policy_type)
                
                logger.info(f"Generated {len(structured_rules.get('rules', []))} rules from policy")
                return structured_rules
                
            else:
                logger.warning("No response from Gemini AI for rule generation")
                return self._generate_fallback_rules(policy_type)
                
        except Exception as e:
            logger.error(f"Error generating rules from policy: {str(e)}")
            return self._generate_fallback_rules(policy_type)
    
    def _create_rule_generation_prompt(self, policy_content: str, policy_type: str) -> str:
        """Create a comprehensive prompt for AI rule generation."""
        
        prompt = f"""
        You are an expert banking compliance and collections specialist. Analyze the following {policy_type} policy document and generate specific, actionable collection rules.

        **POLICY DOCUMENT:**
        {policy_content}

        **TASK:**
        Generate collection rules that map specific customer conditions to appropriate actions. Each rule should follow this structure:

        **RULE STRUCTURE REQUIRED:**
        1. **Condition**: Specific customer situation (loan type, days overdue, security status, amount, etc.)
        2. **Action Sequence**: Step-by-step actions to take
        3. **Timing**: When to take each action
        4. **Restrictions**: What NOT to do (compliance requirements)
        5. **Escalation**: When to escalate to next level

        **EXAMPLES OF REQUIRED RULE FORMAT:**
        - "Unsecured personal loan, 2 EMIs due (≈60 DPD) → soft dunning → written reminder/SMS → field visit controls → no calls before 08:00/after 19:00 → offer restructuring if hardship; no threat/harassment; do not initiate SARFAESI (no security)"
        
        - "Secured auto loan, 6+ months overdue (NPA), collateral available → serve 60-day s.13(2) demand → consider objections (s.13(3A)) → on default, take measures under s.13(4), conduct valuation & auction with notices; ensure repossession conduct per bank policy"
        
        - "Home loan, 3-6 months overdue, secured by property → send demand notice → wait 60 days → initiate SARFAESI proceedings → issue possession notice → conduct property valuation → auction with 30-day notice; follow RBI guidelines"
        
        - "Credit card, 90+ DPD, unsecured → soft reminder calls → written notice → field visit → settlement negotiation → no harassment; respect privacy; follow RBI collection guidelines"

        **CUSTOMER CONDITION PARAMETERS TO CONSIDER:**
        - Loan type (secured/unsecured, auto, home, personal, etc.)
        - Days Past Due (DPD) ranges
        - EMI count overdue
        - Outstanding amount ranges
        - Security/collateral status
        - Customer segment (retail, MSME, etc.)
        - Previous payment behavior
        - Risk level (red, amber, yellow)
        - NPA classification status

        **ACTION TYPES TO INCLUDE:**
        - Communication (SMS, email, call, letter)
        - Field visits
        - Legal notices (Section 13(2), demand notices)
        - Restructuring offers
        - Recovery agent engagement
        - Asset repossession procedures
        - Auction processes
        - Settlement negotiations

        **COMPLIANCE RESTRICTIONS TO INCLUDE:**
        - Timing restrictions (no calls before 8 AM or after 7 PM)
        - No harassment or threats
        - Privacy protection
        - Proper notice periods
        - Legal procedure requirements
        - Documentation requirements

        **OUTPUT FORMAT (JSON):**
        {{
            "policy_analysis": {{
                "document_type": "{policy_type}",
                "key_sections_identified": ["section1", "section2", ...],
                "compliance_requirements": ["requirement1", "requirement2", ...],
                "escalation_triggers": ["trigger1", "trigger2", ...]
            }},
            "generated_rules": [
                {{
                    "rule_id": "RULE_001",
                    "rule_name": "Unsecured Personal Loan Early Stage Collection",
                    "rule_text": "Unsecured personal loan, 1-2 EMIs due (≈30-60 DPD) → soft dunning → SMS reminder → written notice after 7 days → field visit if no response → no calls before 08:00/after 19:00 → offer restructuring if genuine hardship; no threats/harassment; do not initiate SARFAESI (no security)",
                    "conditions": {{
                        "loan_type": "unsecured_personal",
                        "days_overdue_min": 30,
                        "days_overdue_max": 60,
                        "emi_pending_min": 1,
                        "emi_pending_max": 2,
                        "security_available": false
                    }},
                    "priority_level": "medium",
                    "estimated_success_rate": "70%"
                }},
                {{
                    "rule_id": "RULE_002",
                    "rule_name": "Secured Auto Loan NPA Collection",
                    "rule_text": "Secured auto loan, 6+ months overdue (NPA), collateral available → serve 60-day s.13(2) demand → consider objections (s.13(3A)) → on default, take measures under s.13(4), conduct valuation & auction with notices; ensure repossession conduct per bank policy",
                    "conditions": {{
                        "loan_type": "secured_auto",
                        "days_overdue_min": 180,
                        "security_available": true,
                        "npa_status": true
                    }},
                    "priority_level": "high",
                    "estimated_success_rate": "85%"
                }}
            ]
        }}

        **CRITICAL INSTRUCTIONS:**
        1. Generate at least 8-12 comprehensive rules covering different scenarios
        2. Each rule MUST follow the exact format: "Condition → Action1 → Action2 → Action3; restrictions; compliance notes"
        3. Use arrow symbols (→) to separate sequential actions
        4. Use semicolons (;) to separate restrictions and compliance requirements
        5. Include specific timing (e.g., "60-day", "after 7 days", "within 30 days")
        6. Reference specific legal sections (e.g., "s.13(2)", "s.13(3A)", "s.13(4)")
        7. Include DPD ranges in parentheses (e.g., "≈60 DPD", "≈180 DPD")
        8. Specify loan types clearly (unsecured personal, secured auto, home loan, etc.)
        9. Include compliance restrictions (timing, harassment, privacy, legal procedures)
        10. Make rules actionable for collection agents to follow step-by-step

        Generate the rules now in the specified JSON format:
        """
        
        return prompt
    
    def _parse_ai_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the AI response and extract structured rule data."""
        try:
            # Extract JSON from markdown code blocks if present
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()
            
            # Parse JSON
            rules_data = json.loads(response_text)
            return rules_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {str(e)}")
            logger.error(f"Response text: {response_text[:500]}...")
            raise
    
    def _structure_rules(self, rules_data: Dict[str, Any], policy_type: str) -> Dict[str, Any]:
        """Structure and validate the generated rules."""
        
        structured_data = {
            "policy_type": policy_type,
            "generated_at": datetime.utcnow().isoformat(),
            "policy_analysis": rules_data.get("policy_analysis", {}),
            "rules": [],
            "total_rules_generated": 0,
            "rule_categories": []
        }
        
        generated_rules = rules_data.get("generated_rules", [])
        categories = set()
        
        for rule in generated_rules:
            # Validate required fields
            if not all(key in rule for key in ["rule_id", "rule_name", "conditions", "action_sequence"]):
                logger.warning(f"Skipping invalid rule: {rule.get('rule_id', 'unknown')}")
                continue
            
            # Structure the rule
            structured_rule = {
                "rule_id": rule["rule_id"],
                "rule_name": rule["rule_name"],
                "conditions": rule["conditions"],
                "action_sequence": rule["action_sequence"],
                "restrictions": rule.get("restrictions", []),
                "escalation_criteria": rule.get("escalation_criteria", []),
                "priority_level": rule.get("priority_level", "medium"),
                "estimated_success_rate": rule.get("estimated_success_rate", "unknown"),
                "created_at": datetime.utcnow().isoformat(),
                "is_active": True
            }
            
            structured_data["rules"].append(structured_rule)
            
            # Track categories
            if "loan_type" in rule["conditions"]:
                categories.add(rule["conditions"]["loan_type"])
        
        structured_data["total_rules_generated"] = len(structured_data["rules"])
        structured_data["rule_categories"] = list(categories)
        
        return structured_data
    
    def _generate_fallback_rules(self, policy_type: str) -> Dict[str, Any]:
        """Generate basic fallback rules if AI generation fails."""
        
        fallback_rules = {
            "policy_type": policy_type,
            "generated_at": datetime.utcnow().isoformat(),
            "policy_analysis": {
                "document_type": policy_type,
                "key_sections_identified": ["general_guidelines", "collection_procedures"],
                "compliance_requirements": ["no_harassment", "timing_restrictions", "privacy_protection"],
                "escalation_triggers": ["no_response", "legal_action_required"]
            },
            "rules": [
                {
                    "rule_id": "FALLBACK_001",
                    "rule_name": "Basic Early Stage Collection",
                    "rule_text": "Any loan, 1-30 days overdue (≈30 DPD) → SMS reminder → courtesy call after 3 days → written notice after 7 days; no calls before 08:00/after 19:00; no threats/harassment; maintain professional tone",
                    "conditions": {
                        "days_overdue_min": 1,
                        "days_overdue_max": 30,
                        "emi_pending_min": 1,
                        "emi_pending_max": 2
                    },
                    "priority_level": "low",
                    "estimated_success_rate": "60%",
                    "created_at": datetime.utcnow().isoformat(),
                    "is_active": True
                },
                {
                    "rule_id": "FALLBACK_002", 
                    "rule_name": "Medium Risk Collection",
                    "rule_text": "Any loan, 30-90 days overdue (≈60 DPD) → formal written notice → field visit after 14 days → settlement discussion → legal notice if no response; no harassment; respect privacy; document all interactions",
                    "conditions": {
                        "days_overdue_min": 30,
                        "days_overdue_max": 90,
                        "emi_pending_min": 2,
                        "emi_pending_max": 4
                    },
                    "priority_level": "medium",
                    "estimated_success_rate": "45%",
                    "created_at": datetime.utcnow().isoformat(),
                    "is_active": True
                }
            ],
            "total_rules_generated": 2,
            "rule_categories": ["general"]
        }
        
        return fallback_rules
    
    def save_generated_rules(self, rules_data: Dict[str, Any]) -> List[models.CollectionRule]:
        """Save generated rules to the database."""
        saved_rules = []
        
        try:
            for rule_data in rules_data.get("rules", []):
                # Create collection rule record
                collection_rule = models.CollectionRule(
                    rule_name=rule_data["rule_name"],
                    rule_type="collection",
                    conditions=json.dumps(rule_data["conditions"]),
                    actions=rule_data.get("rule_text", ""),  # Store the workflow text as actions
                    priority=rule_data.get("priority_level", "medium"),
                    is_active=rule_data.get("is_active", True),
                    description=rule_data.get("rule_text", f"Auto-generated from policy: {rule_data['rule_name']}"),
                    success_rate=rule_data.get("estimated_success_rate", "unknown"),
                    created_at=datetime.utcnow()
                )
                
                self.db.add(collection_rule)
                saved_rules.append(collection_rule)
            
            self.db.commit()
            logger.info(f"Saved {len(saved_rules)} generated rules to database")
            
        except Exception as e:
            logger.error(f"Error saving generated rules: {str(e)}")
            self.db.rollback()
            raise
        
        return saved_rules
    
    def generate_and_save_rules(self, policy_content: str, policy_type: str = "collection") -> Dict[str, Any]:
        """
        Complete workflow: generate rules from policy and save to database.
        
        Returns:
            Dictionary with generation results and saved rule IDs
        """
        # Generate rules
        rules_data = self.generate_rules_from_policy(policy_content, policy_type)
        
        # Save to database
        saved_rules = self.save_generated_rules(rules_data)
        
        # Return summary
        return {
            "success": True,
            "rules_generated": len(rules_data.get("rules", [])),
            "rules_saved": len(saved_rules),
            "saved_rule_ids": [rule.id for rule in saved_rules],
            "policy_analysis": rules_data.get("policy_analysis", {}),
            "generation_timestamp": rules_data.get("generated_at"),
            "rule_categories": rules_data.get("rule_categories", [])
        }

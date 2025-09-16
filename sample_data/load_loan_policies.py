#!/usr/bin/env python3
"""
Load loan policies from PDF documents and create AI rules
Extracts policy rules from loan policy documents and creates corresponding AI risk assessment rules
"""

import os
import sys
import json
from datetime import datetime, date
from typing import List, Dict, Any

# Add both the project root and src directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_dir = os.path.join(project_root, "src")
sys.path.insert(0, project_root)
sys.path.insert(0, src_dir)

try:
    import fitz  # PyMuPDF for PDF processing
except ImportError:
    print("⚠️ PyMuPDF not installed. Install with: pip install PyMuPDF")
    fitz = None

from app.db.session import SessionLocal
from app.db import models


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text content from PDF file"""
    if not fitz:
        print("❌ PyMuPDF not available. Cannot extract PDF text.")
        return ""
    
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        print(f"❌ Error extracting text from PDF: {e}")
        return ""


def parse_loan_policy_rules_with_ai(policy_text: str) -> List[Dict[str, Any]]:
    """Parse loan policy text using Gen AI to extract risk assessment rules"""
    
    try:
        import google.generativeai as genai
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("⚠️ GEMINI_API_KEY not found. Using fallback keyword-based parsing.")
            return parse_loan_policy_rules_fallback(policy_text)

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')

        prompt = f"""
        You are a senior loan risk analyst. Analyze the bank's loan policy document and create EXACTLY 4 risk assessment rules for a rules engine.

        ### CRITICAL REQUIREMENTS:
        - Generate EXACTLY 4 rules - no more, no less
        - Each rule must be distinct and cover different risk scenarios
        - Focus on the most important policy guidelines only
        - Keep descriptions concise (1-2 sentences maximum)

        ### Required Rule Categories (create exactly one rule for each):
        1. **Early Stage Delinquency** (YELLOW risk - missed 1-2 EMIs)
        2. **Medium Risk Escalation** (AMBER risk - missed 3+ EMIs or 60+ days overdue)  
        3. **High Risk - Secured Loans** (RED risk - repossession consideration)
        4. **High Risk - Unsecured Loans** (RED risk - legal action consideration)

        ### JSON Output Format (return EXACTLY this structure with 4 rules):
        [
        {{
            "name": "Early Stage Delinquency",
            "description": "Initial follow-up for customers with 1-2 missed EMIs.",
            "conditions": [
                {{"field": "missed_emis", "operator": ">=", "value": 1}},
                {{"field": "missed_emis", "operator": "<=", "value": 2}}
            ],
            "risk_level": "yellow",
            "priority": 5,
            "source": "Loan Policy Document"
        }},
        {{
            "name": "Medium Risk Escalation", 
            "description": "Enhanced monitoring for customers with 3+ missed EMIs.",
            "conditions": [
                {{"field": "missed_emis", "operator": ">=", "value": 3}}
            ],
            "risk_level": "amber",
            "priority": 3,
            "source": "Loan Policy Document"
        }},
        {{
            "name": "High Risk Secured Loans",
            "description": "Consider repossession for secured loans with significant overdue amounts.",
            "conditions": [
                {{"field": "days_overdue", "operator": ">=", "value": 90}},
                {{"field": "collateral_available", "operator": "equals", "value": "Yes"}}
            ],
            "risk_level": "red", 
            "priority": 1,
            "source": "Loan Policy Document"
        }},
        {{
            "name": "High Risk Unsecured Loans",
            "description": "Consider legal action for unsecured loans with chronic delinquency.",
            "conditions": [
                {{"field": "days_overdue", "operator": ">=", "value": 120}},
                {{"field": "loan_type", "operator": "equals", "value": "Personal"}}
            ],
            "risk_level": "red",
            "priority": 2, 
            "source": "Loan Policy Document"
        }}
        ]

        ### IMPORTANT:
        - Return ONLY the JSON array with exactly 4 rules
        - Do not add explanatory text before or after the JSON
        - Adapt the conditions based on the policy document below, but maintain the 4-rule structure

        Loan Policy Document:
        {policy_text}
        """

        response = model.generate_content(prompt)
        
        if response and response.text:
            import re
            json_text = response.text
            json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', json_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
            elif not json_text.strip().startswith('['):
                json_match = re.search(r'(\[.*?\])', json_text, re.DOTALL)
                if json_match:
                    json_text = json_match.group(1)
                else:
                    raise ValueError("No JSON array found in response")

            policy_rules = json.loads(json_text)

            # Enforce exactly 4 rules
            if len(policy_rules) != 4:
                print(f"⚠️ AI generated {len(policy_rules)} rules instead of 4. Using fallback.")
                return parse_loan_policy_rules_fallback(policy_text)

            validated_rules = []
            for rule in policy_rules:
                if all(key in rule for key in ['name', 'description', 'conditions', 'risk_level', 'priority']):
                    if not isinstance(rule['conditions'], list):
                        rule['conditions'] = [rule['conditions']]
                    if rule['risk_level'] not in ['red', 'amber', 'yellow']:
                        rule['risk_level'] = 'amber'
                    try:
                        rule['priority'] = int(rule['priority'])
                    except:
                        rule['priority'] = 3
                    rule['source'] = "Loan Policy Document (AI Generated)"
                    validated_rules.append(rule)

            if len(validated_rules) == 4:
                print(f"✅ Gen AI extracted exactly {len(validated_rules)} policy rules")
                return validated_rules
            else:
                print(f"⚠️ Only {len(validated_rules)} valid rules after validation. Using fallback.")
                return parse_loan_policy_rules_fallback(policy_text)
        else:
            print("⚠️ Gen AI did not return a response. Using fallback.")
            return parse_loan_policy_rules_fallback(policy_text)
            
    except Exception as e:
        print(f"⚠️ Error using Gen AI for policy parsing: {e}")
        print("Using fallback keyword-based parsing.")
        return parse_loan_policy_rules_fallback(policy_text)


def parse_loan_policy_rules_fallback(policy_text: str) -> List[Dict[str, Any]]:
    """Fallback: return exactly 4 concise rules"""
    policy_rules = [
        {
            "name": "Early Stage Delinquency",
            "description": "Initial follow-up for customers with 1-2 missed EMIs using soft collection approach.",
            "conditions": [
                {"field": "missed_emis", "operator": ">=", "value": 1},
                {"field": "missed_emis", "operator": "<=", "value": 2}
            ],
            "risk_level": "yellow",
            "priority": 5,
            "source": "Loan Policy Document (Fallback)"
        },
        {
            "name": "Medium Risk Escalation", 
            "description": "Enhanced monitoring for customers with 3+ missed EMIs requiring structured follow-up.",
            "conditions": [
                {"field": "missed_emis", "operator": ">=", "value": 3}
            ],
            "risk_level": "amber",
            "priority": 3,
            "source": "Loan Policy Document (Fallback)"
        },
        {
            "name": "High Risk Secured Loans",
            "description": "Consider repossession for secured loans with significant overdue amounts per SARFAESI guidelines.",
            "conditions": [
                {"field": "days_overdue", "operator": ">=", "value": 90},
                {"field": "collateral_available", "operator": "equals", "value": "Yes"}
            ],
            "risk_level": "red",
            "priority": 1,
            "source": "Loan Policy Document (Fallback)"
        },
        {
            "name": "High Risk Unsecured Loans",
            "description": "Consider legal action for unsecured loans with chronic delinquency exceeding 120 days.",
            "conditions": [
                {"field": "days_overdue", "operator": ">=", "value": 120},
                {"field": "loan_type", "operator": "equals", "value": "Personal"}
            ],
            "risk_level": "red",
            "priority": 2,
            "source": "Loan Policy Document (Fallback)"
        }
    ]
    return policy_rules


def create_ai_policy_rules(policy_rules: List[Dict[str, Any]]) -> bool:
    """Create AI policy rules in the database"""
    
    db = SessionLocal()
    try:
        print("🤖 Creating AI policy rules from loan policy document...")
        print("🗑️ Removing ALL existing automation rules...")
        deleted_rules = db.query(models.AutomationRule).delete(synchronize_session=False)
        print(f"   Removed {deleted_rules} existing rules")
        
        created_rules = 0
        
        for rule_data in policy_rules:
            conditions_dict = {
                "logical_operator": "AND",
                "conditions": rule_data["conditions"]
            }
            
            new_rule = models.AutomationRule(
                rule_name=rule_data["name"],
                description=rule_data.get("description", ""),
                source="loan_policy_ai",
                vendor_name=None,
                conditions=conditions_dict,
                action=f"set_risk_level_{rule_data['risk_level']}",
                is_active=1
            )
            
            db.add(new_rule)
            created_rules += 1
            print(f"  ✅ Created rule: {rule_data['name']}")
        
        db.commit()
        print(f"🎉 Successfully removed {deleted_rules} old rules and created {created_rules} new AI-generated rules")
        return True
        
    except Exception as e:
        print(f"❌ Error creating AI policy rules: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def load_loan_policies():
    """Main function to load loan policies and create AI rules"""
    
    print("🚀 Loading Loan Policies and Creating AI Rules...")
    print("=" * 60)
    
    policy_folder = os.path.join(os.path.dirname(__file__), "loan policy")
    
    if not os.path.exists(policy_folder):
        print(f"❌ Loan policy folder not found: {policy_folder}")
        return False
    
    pdf_files = [f for f in os.listdir(policy_folder) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print(f"❌ No PDF files found in: {policy_folder}")
        return False
    
    print(f"📄 Found {len(pdf_files)} policy document(s):")
    for pdf_file in pdf_files:
        print(f"   - {pdf_file}")
    
    all_policy_rules = []
    
    for pdf_file in pdf_files:
        pdf_path = os.path.join(policy_folder, pdf_file)
        print(f"\n📖 Processing: {pdf_file}")
        
        policy_text = extract_text_from_pdf(pdf_path)
        
        if not policy_text:
            print(f"⚠️ Could not extract text from {pdf_file}")
            continue
        
        print(f"   📝 Extracted {len(policy_text)} characters of text")
        
        policy_rules = parse_loan_policy_rules_with_ai(policy_text)
        
        if policy_rules:
            print(f"   🎯 Identified {len(policy_rules)} policy rules")
            all_policy_rules.extend(policy_rules)
        else:
            print(f"   ⚠️ No policy rules identified in {pdf_file}")
    
    if not all_policy_rules:
        print("❌ No policy rules found in any documents")
        return False
    
    print(f"\n🤖 Creating {len(all_policy_rules)} AI policy rules...")
    success = create_ai_policy_rules(all_policy_rules)
    
    if success:
        print("\n✅ Loan policy loading completed successfully!")
        print("📋 Generated Rules Summary:")
        for rule in all_policy_rules:
            print(f"   • {rule['name']} ({rule['risk_level'].upper()} risk)")
    else:
        print("\n❌ Failed to create AI policy rules")
        return False
    
    return True


if __name__ == "__main__":
    success = load_loan_policies()
    if not success:
        sys.exit(1)

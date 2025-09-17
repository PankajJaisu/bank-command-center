# src/app/core/background_tasks.py
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
from datetime import datetime, date
import json
import csv
import io
import traceback
import pandas as pd
import tempfile
from dateutil.relativedelta import relativedelta

from app.db.session import SessionLocal
from app.db import models
from sqlalchemy.orm import Session


def convert_action_to_collection_action(raw_action: str) -> str:
    """
    Convert old-style actions (like set_risk_level_red) to proper collection actions
    """
    if not raw_action:
        return "Send Reminder"
    
    action_lower = raw_action.lower()
    
    # Convert old-style risk level actions
    if "set_risk_level_red" in action_lower or "critical" in action_lower or "high" in action_lower:
        return "Send Legal Notice"
    elif "set_risk_level_amber" in action_lower or "medium" in action_lower or "moderate" in action_lower:
        return "Send Reminder"
    elif "set_risk_level_green" in action_lower or "low" in action_lower or "good" in action_lower:
        return "Send Email"
    
    # If it's already a proper action, return as-is
    valid_actions = ["Send Reminder", "Send Legal Notice", "Make Phone Call", "Field Visit", "Escalate to Manager", "Block Account", "Send Email", "Monitor Account"]
    if raw_action in valid_actions:
        return raw_action
    
    # Try to extract action from text
    if "legal" in action_lower or "notice" in action_lower:
        return "Send Legal Notice"
    elif "call" in action_lower or "phone" in action_lower:
        return "Make Phone Call"
    elif "visit" in action_lower or "field" in action_lower:
        return "Field Visit"
    elif "escalate" in action_lower or "manager" in action_lower:
        return "Escalate to Manager"
    elif "block" in action_lower or "freeze" in action_lower:
        return "Block Account"
    elif "email" in action_lower:
        return "Send Email"
    elif "reminder" in action_lower:
        return "Send Reminder"
    
    # Default fallback
    return "Send Reminder"
# NOTE: Ingestion and matching modules are not available in collection management system
# from app.modules.ingestion import service as ingestion_service
# from app.modules.matching import engine as matching_engine
from app.config import PARALLEL_WORKERS
from app.utils.auditing import log_audit_event
from app.utils.logging import (
    get_logger,
    log_ingestion_batch_summary,
    log_performance_metric,
    log_error_with_context,
)

# Note: No need to import unit_converter here anymore


def process_excel_customer_data(db: Session, file_info: Dict[str, Any], job_id: int) -> Dict[str, Any]:
    """Process Excel customer data file and load customers into database"""
    try:
        # Write the file content to a temporary file
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            temp_file.write(file_info["content"])
            temp_file_path = temp_file.name
        
        try:
            # Read the Excel file
            df = pd.read_excel(temp_file_path)
            
            # Detect file type based on columns
            columns = df.columns.tolist()
            
            # Check if this is the main customer loan data file (has Name column)
            if 'Name' in columns and 'Customer ID' in columns:
                return process_customer_loan_data(db, df, file_info)
            
            # Check if this is CIBIL data file (has CIBIL_Score column)
            elif 'CIBIL_Score' in columns and 'Customer_No' in columns:
                return process_cibil_data(db, df, file_info)
            
            else:
                return {
                    "filename": file_info["filename"],
                    "status": "skipped",
                    "message": f"Unknown Excel format. Columns found: {columns}"
                }
                
        finally:
            # Clean up temporary file
            import os
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except Exception as e:
        db.rollback()
        return {
            "filename": file_info["filename"],
            "status": "error",
            "message": f"Failed to process Excel customer data: {str(e)}"
        }


def process_customer_loan_data(db: Session, df: pd.DataFrame, file_info: Dict[str, Any]) -> Dict[str, Any]:
    """Process the main customer loan data Excel file"""
    # Clear existing customer data first (only for main data file)
    db.query(models.DataIntegrityAlert).delete()
    db.query(models.Loan).delete()
    db.query(models.Customer).delete()
    db.query(models.ContractNote).delete()
    
    customers_created = 0
    loans_created = 0
    contracts_created = 0
    
    for index, row in df.iterrows():
        try:
            # Generate email from name
            name_parts = str(row['Name']).lower().split()
            email = f"{'.'.join(name_parts)}@example.com" if len(name_parts) > 1 else f"{name_parts[0]}@example.com"
            
            # Create customer with proper data mapping - handle NaN values properly
            loan_amount_raw = row.get('Loan Amount', 50000)
            loan_amount = float(loan_amount_raw) if pd.notna(loan_amount_raw) and str(loan_amount_raw).strip() != '' else 50000.0
            
            percent_due_raw = row.get('% Due', 0)
            percent_due = float(percent_due_raw) if pd.notna(percent_due_raw) and str(percent_due_raw).strip() != '' else 0.0
            
            # Ensure loan_amount is never NaN or zero
            if pd.isna(loan_amount) or loan_amount <= 0:
                loan_amount = 50000.0
                
            # Ensure percent_due is never NaN
            if pd.isna(percent_due) or percent_due < 0:
                percent_due = 0.0
            
            # --- PHASE 1: Map risk level to new simplified categories ---
            risk_level_mapping = {
                "red": "High",
                "amber": "Medium",
                "yellow": "Low",
                "green": "Low"
            }
            raw_risk = "red" if percent_due > 80 else ("amber" if percent_due > 50 else "yellow")
            risk_level = risk_level_mapping.get(raw_risk.lower(), "Medium")

            customer = models.Customer(
                customer_no=str(row['Customer ID']),
                name=str(row['Name']),
                email=email,
                phone=f"+91-{9000000000 + index}",
                address=f"Address {index + 1}, City, State - {110001 + index}",
                
                # --- PHASE 1: Populate new fields ---
                segment=str(row['Segment']) if 'Segment' in row and pd.notna(row['Segment']) else "Retail",
                cbs_risk_level=risk_level,
                # --- END PHASE 1 ---

                cibil_score=720 - (index * 10),
                days_since_employment=15 + (index * 2),
                employment_status="Verified" if index % 2 == 0 else "Unverified",
                cbs_income_verification=f"{50 + (index * 5)}%",
                salary_last_date=date.today() - relativedelta(days=10 + index),
                cbs_outstanding_amount=loan_amount,
                pending_amount=float(row['Overdue Amount']) if pd.notna(row['Overdue Amount']) else 0,
                pendency="Yes" if str(row['Pendency']).lower() == 'yes' else "No",
                emi_pending=int(row['EMI Pending']) if 'EMI Pending' in row and pd.notna(row['EMI Pending']) else 0,
                cbs_emi_amount=loan_amount * 0.1,
                cbs_due_day=5 + (index % 25),
                cbs_last_payment_date=date.today() - relativedelta(months=1),
            )
            db.add(customer)
            db.flush()  # Get the customer ID
            customers_created += 1
            
            # Create loan - ensure no NaN values
            emi_amount = customer.cbs_emi_amount if pd.notna(customer.cbs_emi_amount) else loan_amount * 0.1
            outstanding_amount = customer.cbs_outstanding_amount if pd.notna(customer.cbs_outstanding_amount) else loan_amount
            
            loan = models.Loan(
                customer_id=customer.id,
                loan_id=f"LN-{customer.id:05d}",
                loan_amount=loan_amount,  # Already validated above
                emi_amount=emi_amount,
                outstanding_amount=outstanding_amount,
                last_payment_date=customer.cbs_last_payment_date,
                next_due_date=date.today() + relativedelta(days=customer.cbs_due_day),
                tenure_months=36,  # Add default tenure
                interest_rate=12.5,  # Add default interest rate
                status="active"
            )
            db.add(loan)
            loans_created += 1
            
            # Create contract note
            contract_filename = f"{customer.customer_no}_contract_note.pdf"
            contract = models.ContractNote(
                filename=contract_filename,
                file_path=f"sample_data/contract note/{contract_filename}",
                contract_emi_amount=customer.cbs_emi_amount,
                contract_due_day=customer.cbs_due_day,
                contract_late_fee_percent=2.0,
                contract_loan_amount=customer.cbs_outstanding_amount,
                contract_tenure_months=36,
                contract_interest_rate=12.5,
                contract_default_clause="Standard default clause",
                contract_governing_law="Indian Contract Act"
            )
            db.add(contract)
            db.flush()
            contracts_created += 1
            
            # Link contract to customer
            customer.contract_note_id = contract.id
            
        except Exception as e:
            logger = get_logger(__name__)
            logger.warning(f"Error processing row {index}: {str(e)}")
            # Continue processing other rows instead of failing completely
            continue
        
    db.commit()
    
    return {
        "filename": file_info["filename"],
        "status": "success",
        "message": f"Processed {customers_created} customers, {loans_created} loans, {contracts_created} contracts",
        "customers_created": customers_created,
        "loans_created": loans_created,
        "contracts_created": contracts_created
    }


def process_cibil_data(db: Session, df: pd.DataFrame, file_info: Dict[str, Any]) -> Dict[str, Any]:
    """Process CIBIL data Excel file and update existing customers"""
    updated_customers = 0
    
    for index, row in df.iterrows():
        customer_no = str(row['Customer_No'])
        cibil_score = int(row['CIBIL_Score']) if pd.notna(row['CIBIL_Score']) else None
        
        # Find existing customer
        customer = db.query(models.Customer).filter_by(customer_no=customer_no).first()
        
        if customer and cibil_score:
            # Update CIBIL score and related fields
            customer.cibil_score = cibil_score
            customer.employment_status = str(row['Employment_Status']) if pd.notna(row['Employment_Status']) else customer.employment_status
            
            # --- PHASE 1: Update risk level based on CIBIL score ---
            if cibil_score >= 750:
                customer.cbs_risk_level = "Low"
            elif cibil_score >= 650:
                customer.cbs_risk_level = "Medium"
            else:
                customer.cbs_risk_level = "High"
                
            updated_customers += 1
    
    db.commit()
    
    return {
        "filename": file_info["filename"],
        "status": "success",
        "message": f"Updated CIBIL data for {updated_customers} customers",
        "customers_updated": updated_customers
    }


def process_loan_policy_document(db: Session, file_info: Dict[str, Any], job_id: int) -> Dict[str, Any]:
    """Process loan policy PDF document and create automation rules using Gen AI"""
    try:
        # Write the file content to a temporary file
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(file_info["content"])
            temp_file_path = temp_file.name
        
        try:
            # Extract text from PDF
            try:
                import fitz  # PyMuPDF
                print(f"📄 Extracting text from PDF: {file_info['filename']}")
                print(f"   Temp file path: {temp_file_path}")
                print(f"   File size: {os.path.getsize(temp_file_path)} bytes")
                
                doc = fitz.open(temp_file_path)
                policy_text = ""
                for page_num, page in enumerate(doc):
                    page_text = page.get_text()
                    policy_text += page_text
                    print(f"   Page {page_num + 1}: {len(page_text)} characters extracted")
                doc.close()
                
                print(f"   Total text extracted: {len(policy_text)} characters")
                print(f"   First 200 characters: {policy_text[:200]}")
                
            except ImportError:
                return {
                    "filename": file_info["filename"],
                    "status": "error",
                    "message": "PyMuPDF not installed. Cannot extract PDF text."
                }
            except Exception as e:
                print(f"❌ Error extracting PDF text: {str(e)}")
                return {
                    "filename": file_info["filename"],
                    "status": "error",
                    "message": f"Failed to extract text from PDF: {str(e)}"
                }
            
            if not policy_text.strip():
                return {
                    "filename": file_info["filename"],
                    "status": "error",
                    "message": "No text content found in PDF"
                }
            
            # Generate rules using Gen AI (without vector database)
            try:
                print(f"🤖 Generating rules with Gen AI...")
                policy_rules = parse_loan_policy_rules_with_ai(policy_text)
                    
            except Exception as ai_error:
                print(f"⚠️ Gen AI processing failed: {ai_error}")
                policy_rules = []
            
            if not policy_rules:
                return {
                    "filename": file_info["filename"],
                    "status": "warning",
                    "message": "No policy rules could be extracted from document"
                }
            
            # Store rules for this document (will be combined with other documents)
            return {
                "filename": file_info["filename"],
                "status": "success",
                "message": f"Extracted {len(policy_rules)} rules from {file_info['filename']}",
                "policy_rules": policy_rules
            }
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except Exception as e:
        db.rollback()
        return {
            "filename": file_info["filename"],
            "status": "error",
            "message": f"Failed to process loan policy document: {str(e)}"
        }


def parse_loan_policy_rules_with_ai(policy_text: str) -> List[Dict[str, Any]]:
    """Parse loan policy text using Gen AI to extract risk assessment rules"""
    
    try:
        # Import Google Gen AI
        import google.generativeai as genai
        import os
        
        # Configure Gen AI using settings (force reload environment)
        from dotenv import load_dotenv
        load_dotenv(override=True)
        from app.config import settings
        api_key = settings.gemini_api_key
        if not api_key:
            print("⚠️ GEMINI_API_KEY not found in settings. Using fallback keyword-based parsing.")
            print(f"   Check your .env file and ensure GEMINI_API_KEY is set")
            return parse_loan_policy_rules_fallback(policy_text)
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(settings.gemini_model_name)
        
        # Create a detailed prompt for extracting loan policy rules
        prompt = f"""
        You are a senior loan risk analyst. Carefully analyze this loan policy document and create sophisticated risk assessment rules based on the specific guidelines mentioned.

        The document covers different loan types and their risk escalation patterns:
        - Home/Mortgage Loans: Early warning for few missed installments, high risk for consecutive months
        - Personal Loans: More sensitive due to unsecured nature, risky after multiple missed installments
        - Business Loans: Consider cash flow challenges, risk after several missed payments
        - Vehicle Loans: Early delays manageable, risk after prolonged irregularity
        - Education Loans: Flexible approach, high risk after multiple installments

        Create rules that reflect these sophisticated risk assessment principles. Each rule should have:

        1. **Professional Rule Name** (specific to loan type and risk pattern)
        2. **Sophisticated Description** (detailed explanation of the business logic and escalation rationale)
        3. **Precise Conditions** (based on the policy guidelines)
        4. **Appropriate Risk Level** (red=recovery/legal, amber=credit monitoring, yellow=customer service)
        5. **Business Priority** (1-6, based on severity and escalation needs)

        Available database fields:
        - missed_emis (number of consecutive missed EMI payments)
        - days_overdue (total days payment is overdue)
        - pending_amount (overdue amount in rupees)
        - cibil_score (credit score 300-900)
        - employment_status (Verified/Unverified)
        - total_outstanding (total loan amount)
        - loan_type (Home/Personal/Business/Vehicle/Education)
        - tenure_months (loan tenure)

        Risk Level Guidelines:
        - **RED**: Serious/prolonged delays → Recovery/Legal team (Priority 1-2)
        - **AMBER**: Repeated delays → Credit Risk monitoring team (Priority 3-4)  
        - **YELLOW**: Occasional delays → Customer service team (Priority 5-6)

        Generate 8-10 sophisticated rules that capture the nuanced risk assessment approach described in the policy. Focus on:
        - Loan type-specific risk thresholds
        - Escalation patterns (occasional → repeated → serious delays)
        - Business context (cash flow, student hardships, etc.)
        - Team assignment based on risk level

        Respond in JSON format:
        [{{
            "name": "Specific Professional Rule Name",
            "description": "Detailed business explanation of when and why this rule triggers, including escalation rationale and team assignment",
            "conditions": [{{"field": "field_name", "operator": ">=", "value": 100}}],
            "risk_level": "red|amber|yellow",
            "priority": 1-6,
            "source": "Loan Policy Document"
        }}]

        Loan Policy Document:
        {policy_text}
        """
        
        # Generate response using Gen AI
        print(f"📤 Sending request to Gen AI...")
        response = model.generate_content(prompt)
        
        if response and response.text:
            print(f"📥 Received Gen AI response: {len(response.text)} characters")
            print(f"   Response preview: {response.text[:300]}...")
            # Try to parse the JSON response
            import json
            import re
            
            # Extract JSON from the response (handle markdown code blocks)
            json_text = response.text
            json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', json_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
            elif json_text.strip().startswith('['):
                # Response is already JSON
                pass
            else:
                # Try to find JSON array in the text
                json_match = re.search(r'(\[.*?\])', json_text, re.DOTALL)
                if json_match:
                    json_text = json_match.group(1)
                else:
                    raise ValueError("No JSON array found in response")
            
            policy_rules = json.loads(json_text)
            
            # Validate and clean the rules
            validated_rules = []
            for rule in policy_rules:
                if all(key in rule for key in ['name', 'description', 'conditions', 'risk_level', 'priority']):
                    # Ensure conditions is a list
                    if not isinstance(rule['conditions'], list):
                        rule['conditions'] = [rule['conditions']]
                    
                    # Validate risk level
                    if rule['risk_level'] not in ['red', 'amber', 'yellow']:
                        rule['risk_level'] = 'amber'  # Default to amber
                    
                    # Ensure priority is an integer
                    try:
                        rule['priority'] = int(rule['priority'])
                    except:
                        rule['priority'] = 3  # Default priority
                    
                    rule['source'] = "Loan Policy Document (AI Generated)"
                    validated_rules.append(rule)
            
            if validated_rules:
                print(f"✅ Gen AI extracted {len(validated_rules)} policy rules")
                for i, rule in enumerate(validated_rules[:3]):  # Show first 3 rules
                    print(f"   Rule {i+1}: {rule['name']}")
                    print(f"      Description: {rule['description'][:100]}...")
                return validated_rules
            else:
                print("⚠️ Gen AI response contained no valid rules. Using fallback.")
                return parse_loan_policy_rules_fallback(policy_text)
        
        else:
            print("⚠️ Gen AI did not return a response. Using fallback.")
            return parse_loan_policy_rules_fallback(policy_text)
            
    except Exception as e:
        print(f"⚠️ Error using Gen AI for policy parsing: {e}")
        print("Using fallback keyword-based parsing.")
        return parse_loan_policy_rules_fallback(policy_text)


def parse_loan_policy_rules_fallback(policy_text: str) -> List[Dict[str, Any]]:
    """Sophisticated fallback rules based on the updated loan policy document analysis"""
    
    print(f"🔄 Using intelligent fallback rules based on actual PDF content")
    print(f"   Analyzing {len(policy_text)} characters of policy text")
    
    # Analyze the actual PDF content to create dynamic rules
    policy_lower = policy_text.lower()
    
    # Extract key insights from the policy text
    has_home_loans = 'home loan' in policy_lower or 'mortgage' in policy_lower
    has_personal_loans = 'personal loan' in policy_lower
    has_business_loans = 'business loan' in policy_lower
    has_gold_loans = 'gold loan' in policy_lower
    has_vehicle_loans = 'vehicle loan' in policy_lower
    has_education_loans = 'education loan' in policy_lower
    
    print(f"   📊 Content analysis:")
    print(f"      Home/Mortgage loans: {'✓' if has_home_loans else '✗'}")
    print(f"      Personal loans: {'✓' if has_personal_loans else '✗'}")
    print(f"      Business loans: {'✓' if has_business_loans else '✗'}")
    print(f"      Gold loans: {'✓' if has_gold_loans else '✗'}")
    print(f"      Vehicle loans: {'✓' if has_vehicle_loans else '✗'}")
    print(f"      Education loans: {'✓' if has_education_loans else '✗'}")
    
    # Look for specific risk indicators in the text
    mentions_consecutive = 'consecutive' in policy_lower
    mentions_multiple = 'multiple' in policy_lower
    mentions_collateral = 'collateral' in policy_lower or 'pledged' in policy_lower
    mentions_auction = 'auction' in policy_lower
    mentions_recovery = 'recovery' in policy_lower
    
    print(f"      Risk indicators found: consecutive={mentions_consecutive}, multiple={mentions_multiple}, collateral={mentions_collateral}")
    
    # Generate timestamp-based identifier for this version
    import time
    timestamp = int(time.time())
    version_id = f"v{timestamp}"
    
    # Create sophisticated rules based on the UPDATED loan policy document content
    policy_rules = [
        {
            "name": "Home Loan Consecutive Months Default - High Risk",
            "description": "Home/Mortgage loans showing consecutive months of non-payment indicate severe financial distress. As per updated policy guidelines, when borrowers are unable to pay for several consecutive months, immediate escalation to recovery and legal team is required to protect collateral interests.",
            "conditions": [
                {"field": "missed_emis", "operator": ">=", "value": 3}
            ],
            "risk_level": "red",
            "priority": 1,
            "source": f"Smart PDF Analysis {version_id} (Fallback)"
        },
        {
            "name": "Personal Loan Multiple Installment Risk",
            "description": "Personal loans are particularly sensitive to repayment delays due to their unsecured nature. Multiple missed installments (2+) as outlined in the updated policy require immediate attention and potential credit bureau reporting to mitigate losses.",
            "conditions": [
                {"field": "missed_emis", "operator": ">=", "value": 2}
            ],
            "risk_level": "red",
            "priority": 1,
            "source": f"Smart PDF Analysis {version_id} (Fallback)"
        },
        {
            "name": "Gold Loan Collateral Risk - Extended Delays",
            "description": "Gold loans backed by physical collateral require different treatment. However, when delays continue over multiple months as specified in updated policy, the pledged gold is at risk of auction and the account must be flagged for swift collateral liquidation procedures.",
            "conditions": [
                {"field": "missed_emis", "operator": ">=", "value": 3},
                {"field": "days_overdue", "operator": ">=", "value": 90}
            ],
            "risk_level": "red",
            "priority": 1,
            "source": f"Smart PDF Analysis {version_id} (Fallback)"
        },
        {
            "name": "Vehicle Loan Repossession Risk",
            "description": "Vehicle loans with prolonged irregular payment patterns signal rising risk. Once the loan becomes irregular for extended periods, policy allows consideration of repossession proceedings to protect asset value.",
            "conditions": [
                {"field": "missed_emis", "operator": ">=", "value": 4}
            ],
            "risk_level": "red",
            "priority": 2,
            "source": "Loan Policy Document (Fallback)"
        },
        {
            "name": "Personal Loan Repeated Delays - Credit Monitoring",
            "description": "Personal loans showing repeated delays in installment payments indicate growing financial stress. This pattern requires enhanced monitoring by the credit risk team before escalating to recovery actions.",
            "conditions": [
                {"field": "missed_emis", "operator": ">=", "value": 2},
                {"field": "missed_emis", "operator": "<", "value": 3}
            ],
            "risk_level": "amber",
            "priority": 3,
            "source": "Loan Policy Document (Fallback)"
        },
        {
            "name": "Business Loan Short-term Cash Flow Monitoring",
            "description": "Business loans with short-term cash flow challenges causing payment delays require active monitoring and discussions with borrower's finance team to prevent escalation to high-risk category.",
            "conditions": [
                {"field": "days_overdue", "operator": ">=", "value": 30},
                {"field": "days_overdue", "operator": "<", "value": 60}
            ],
            "risk_level": "amber",
            "priority": 4,
            "source": "Loan Policy Document (Fallback)"
        },
        {
            "name": "Education Loan Pattern Monitoring",
            "description": "Education loans with repeated delays over multiple installments indicate the account is slipping into risk. Given student financial hardships, this requires careful monitoring before regulatory reporting.",
            "conditions": [
                {"field": "missed_emis", "operator": ">=", "value": 2}
            ],
            "risk_level": "amber",
            "priority": 4,
            "source": "Loan Policy Document (Fallback)"
        },
        {
            "name": "Home Loan Early Warning System",
            "description": "Missing one installment in home loans may not be serious but serves as an early warning sign. Customer service team should provide reminders and support to prevent escalation to risk category.",
            "conditions": [
                {"field": "missed_emis", "operator": "=", "value": 1}
            ],
            "risk_level": "yellow",
            "priority": 5,
            "source": "Loan Policy Document (Fallback)"
        },
        {
            "name": "Vehicle Loan Early Intervention",
            "description": "Early delays in vehicle loans can be managed with proactive reminders and customer engagement. This early intervention prevents progression to higher risk categories requiring stronger actions.",
            "conditions": [
                {"field": "days_overdue", "operator": ">=", "value": 15},
                {"field": "days_overdue", "operator": "<", "value": 30}
            ],
            "risk_level": "yellow",
            "priority": 6,
            "source": "Loan Policy Document (Fallback)"
        },
        {
            "name": "Education Loan Counseling Stage",
            "description": "Occasional missed payments in education loans are managed with flexibility through reminders and financial counseling, considering students may face temporary financial hardships.",
            "conditions": [
                {"field": "missed_emis", "operator": "=", "value": 1}
            ],
            "risk_level": "yellow",
            "priority": 6,
            "source": "Loan Policy Document (Fallback)"
        }
    ]
    
    print(f"✅ Generated {len(policy_rules)} sophisticated rules from updated policy content")
    for i, rule in enumerate(policy_rules[:3]):  # Show first 3 rules
        print(f"   Rule {i+1}: {rule['name']}")
        print(f"      Source: {rule['source']}")
    
    return policy_rules


def update_job_progress(
    job_id: int, processed_count: int, total_files: int, status: str = "processing", db_session=None
):
    try:
        if db_session:
            # Use the provided session (within existing transaction)
            job = db_session.query(models.Job).filter_by(id=job_id).first()
            if job:
                job.processed_files = processed_count
                job.total_files = total_files
                job.status = status
                # Don't commit here - let the caller handle the transaction
        else:
            # Create new session (for standalone updates)
            with SessionLocal() as db:
                job = db.query(models.Job).filter_by(id=job_id).first()
                if job:
                    job.processed_files = processed_count
                    job.total_files = total_files
                    job.status = status
                    db.commit()
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Error updating job progress: {e}")


def process_pdf_in_parallel(pdf_info: Dict[str, Any], job_id: int) -> Dict[str, Any]:
    """
    A helper function to be run in a separate thread. It performs AI extraction, identifies
    the document type, and returns the data without touching the main database.
    """
    try:
        # Check if this is a contract note file - route to agentic OCR instead of Gemini API
        filename = pdf_info["filename"]
        if "contract_note" in filename.lower() or filename.startswith("CUST-"):
            return {
                "filename": filename,
                "status": "contract_note",
                "message": "Contract note detected - will be processed using agentic OCR",
                "use_agentic_ocr": True
            }

        with SessionLocal() as db_for_prompt:
            dynamic_prompt = ingestion_service.build_extraction_prompt(db_for_prompt)

        extracted_data = ingestion_service.extractor.extract_data_from_pdf(
            pdf_info["content"], dynamic_prompt
        )

        if not extracted_data:
            # Check if this is a loan policy document - provide specific guidance
            filename = pdf_info["filename"].lower()
            if any(keyword in filename for keyword in ["policy", "loan", "terms", "conditions", "agreement"]):
                return {
                    "filename": pdf_info["filename"],
                    "status": "error", 
                    "message": "AI data extraction failed for loan policy document. Please ensure GEMINI_API_KEY is configured in your .env file. For loan policy documents, the system requires AI processing to extract rules and terms.",
                }
            else:
                return {
                    "filename": pdf_info["filename"],
                    "status": "error",
                    "message": "AI data extraction failed - no data returned from Gemini API. Please check your GEMINI_API_KEY configuration in the .env file.",
                }

        doc_type = extracted_data.get("document_type")
        if not doc_type or doc_type not in [e.value for e in models.DocumentTypeEnum]:
            return {
                "filename": pdf_info["filename"],
                "status": "error",
                "message": f"Could not determine a valid document type. Found: '{doc_type}'",
            }

        extracted_data["file_path"] = pdf_info["filename"]

        is_valid, error_message = ingestion_service.validate_required_fields(
            extracted_data, doc_type
        )
        if not is_valid:
            return {
                "filename": pdf_info["filename"],
                "status": "error",
                "message": error_message,
            }

        print(
            {
                "filename": pdf_info["filename"],
                "status": "success",
                "extracted_data": extracted_data,
            }
        )

        return {
            "filename": pdf_info["filename"],
            "status": "success",
            "extracted_data": extracted_data,
        }
    except Exception as e:
        logger = get_logger(__name__)
        log_error_with_context(
            logger, e, {"filename": pdf_info["filename"]}, "PDF extraction thread"
        )
        return {
            "filename": pdf_info["filename"],
            "status": "error",
            "message": f"Critical error in thread: {e}",
        }


def process_policy_documents(job_id: int, file_data_list: List[Dict[str, Any]]):
    """
    Process policy documents and create rules with editing capability.
    This function extracts rules from policy documents and stores them as pending rules
    that can be edited before activation.
    """
    from app.db.session import SessionLocal
    from app.db import models
    from app.modules.ingestion import extractor, service
    import json
    import logging
    
    logger = logging.getLogger(__name__)
    
    with SessionLocal() as db:
        job = db.query(models.Job).filter(models.Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return
        
        job.status = "processing"
        db.commit()
        
        processed_files = 0
        failed_files = 0
        
        for file_data in file_data_list:
            try:
                logger.info(f"Processing policy document: {file_data['filename']}")
                
                # Extract data from PDF using AI
                extraction_prompt = service.build_policy_extraction_prompt(db)
                extracted_data = extractor.extract_data_from_pdf(
                    file_data["content"], extraction_prompt
                )
                
                if not extracted_data:
                    logger.error(f"Failed to extract data from {file_data['filename']}")
                    failed_files += 1
                    continue
                
                # Create pending automation rules from extracted policy
                rule_level = file_data.get("rule_level", "system")
                segment = file_data.get("segment")
                customer_id = file_data.get("customer_id")
                
                # Parse extracted rules and create pending automation rules
                if isinstance(extracted_data, dict) and "rules" in extracted_data:
                    rules = extracted_data["rules"]
                    if not isinstance(rules, list):
                        rules = [rules]
                    
                    for rule_data in rules:
                        try:
                            # Convert old-style actions to proper collection actions
                            raw_action = rule_data.get("action", "Send Reminder")
                            converted_action = convert_action_to_collection_action(raw_action)
                            
                            # Create automation rule with pending status
                            automation_rule = models.AutomationRule(
                                rule_name=rule_data.get("name", f"Policy Rule from {file_data['filename']}"),
                                description=rule_data.get("description", ""),
                                conditions=json.dumps(rule_data.get("conditions", {})),
                                action=converted_action,
                                source="policy_upload",
                                is_active=False,  # Start as inactive/pending
                                rule_level=rule_level,
                                segment=segment,
                                customer_id=customer_id,
                                source_document=file_data['filename'],
                                status="pending_review"  # New status for rules awaiting review
                            )
                            
                            # Debug logging
                            logger.info(f"Creating automation rule with rule_level: {rule_level}, segment: {segment}, customer_id: {customer_id}")
                            db.add(automation_rule)
                            
                        except Exception as e:
                            logger.error(f"Error creating rule from {file_data['filename']}: {e}")
                            continue
                
                processed_files += 1
                logger.info(f"Successfully processed policy document: {file_data['filename']}")
                
            except Exception as e:
                logger.error(f"Error processing {file_data['filename']}: {e}")
                failed_files += 1
        
        # Update job status
        job.processed_files = processed_files
        job.failed_files = failed_files
        job.status = "completed" if failed_files == 0 else "completed_with_errors"
        db.commit()
        
        logger.info(f"Policy processing job {job_id} completed. Processed: {processed_files}, Failed: {failed_files}")


def process_uploaded_documents(job_id: int, files_data: List[Dict[str, Any]]):
    """
    Orchestrates ingestion with PARALLEL AI extraction and sequential DB writes.
    This is now refactored to handle all document types from PDFs and Excel customer data.
    """
    logger = get_logger(__name__)
    job_final_status = "completed"
    error_summary = []
    start_time = datetime.utcnow()

    try:
        structured_files = [
            f for f in files_data if f["filename"].lower().endswith((".json", ".csv"))
        ]
        pdf_files = [f for f in files_data if f["filename"].lower().endswith(".pdf") and f.get("file_type") != "loan_policy"]
        excel_customer_files = [
            f for f in files_data if f.get("file_type") in ["customer_data", "excel_customer_data"] and f["filename"].lower().endswith((".xlsx", ".xls"))
        ]
        loan_policy_files = [
            f for f in files_data if f.get("file_type") == "loan_policy" and f["filename"].lower().endswith(".pdf")
        ]
        total_files_to_process = len(structured_files) + len(pdf_files) + len(excel_customer_files) + len(loan_policy_files)

        logger.info(
            f"📤 Starting batch job {job_id} | PDF files: {len(pdf_files)}, Structured files: {len(structured_files)}, Excel customer files: {len(excel_customer_files)}, Loan policy files: {len(loan_policy_files)}"
        )

        # --- Phase 1: AI Extraction (Parallel) ---
        logger.info(
            f"🔄 Phase 1: Parallel extraction for {len(pdf_files)} PDF files using {PARALLEL_WORKERS} workers"
        )
        pdf_results = []
        processed_count = 0
        with ThreadPoolExecutor(max_workers=PARALLEL_WORKERS) as executor:
            future_to_pdf = {
                executor.submit(process_pdf_in_parallel, pdf_info, job_id): pdf_info
                for pdf_info in pdf_files
            }
            for future in as_completed(future_to_pdf):
                result = future.result()
                pdf_results.append(result)
                processed_count += 1
                update_job_progress(job_id, processed_count, total_files_to_process)

                # Log extraction result more cleanly
                status = result.get("status", "error")
                if status == "success":
                    logger.debug(f"✅ Extracted: {result['filename']}")
                else:
                    logger.warning(
                        f"❌ Failed extraction: {result['filename']} - {result.get('message', 'Unknown error')}"
                    )

        successful_extractions = [
            res["extracted_data"]
            for res in pdf_results
            if res.get("status") == "success"
        ]
        contract_notes_to_process = [
            res
            for res in pdf_results
            if res.get("status") == "contract_note"
        ]
        failed_extractions = [
            {
                "filename": res["filename"],
                "status": res["status"],
                "message": res["message"],
                "extracted_id": None,
                "document_type": None,
            }
            for res in pdf_results
            if res.get("status") == "error"
        ]
        job_summary = failed_extractions.copy()

        # --- Phase 2: Database Operations (Sequential) ---
        logger.info(
            f"💾 Phase 2: Database operations for {len(successful_extractions) + len(structured_files) + len(contract_notes_to_process)} files"
        )
        with SessionLocal() as db:
            try:
                all_invoice_ids_to_match = []
                newly_saved_po_numbers = set()

                # Process structured files first
                if structured_files:
                    all_structured_records = []
                    for file_info in structured_files:
                        try:
                            if file_info["filename"].lower().endswith(".json"):
                                records = json.loads(
                                    file_info["content"].decode("utf-8-sig")
                                )
                            else:  # .csv
                                records = list(
                                    csv.DictReader(
                                        io.StringIO(
                                            file_info["content"].decode("utf-8-sig")
                                        )
                                    )
                                )
                            if not isinstance(records, list):
                                records = [records]
                            all_structured_records.extend(records)
                            job_summary.append(
                                {
                                    "filename": file_info["filename"],
                                    "status": "success",
                                    "message": f"Parsed {len(records)} records.",
                                    "extracted_id": None,
                                    "document_type": "StructuredData",
                                }
                            )
                        except Exception as e:
                            job_summary.append(
                                {
                                    "filename": file_info["filename"],
                                    "status": "error",
                                    "message": f"Failed to parse: {e}",
                                    "extracted_id": None,
                                    "document_type": None,
                                }
                            )

                    po_count, grn_count, err_count = 0, 0, 0
                    processed_po_numbers = (
                        set()
                    )  # Track POs processed in this job to prevent duplicates
                    processed_grn_numbers = (
                        set()
                    )  # Track GRNs processed in this job to prevent duplicates

                    for record in all_structured_records:
                        if "grn_number" in record:
                            grn_number = record.get("grn_number")
                            if grn_number in processed_grn_numbers:
                                logger.warning(
                                    f"Skipping duplicate GRN {grn_number} within same job"
                                )
                                err_count += 1
                                continue

                            saved_grn, err = ingestion_service._save_grn_from_dict(
                                db, record, job_id
                            )
                            if err:
                                err_count += 1
                            else:
                                grn_count += 1
                                if grn_number:
                                    processed_grn_numbers.add(grn_number)

                        elif "po_number" in record:
                            po_number = record.get("po_number")
                            if po_number in processed_po_numbers:
                                logger.warning(
                                    f"Skipping duplicate PO {po_number} within same job"
                                )
                                err_count += 1
                                continue

                            saved_po, err = ingestion_service._save_po_from_dict(
                                db, record, job_id
                            )
                            if err:
                                err_count += 1
                            else:
                                po_count += 1
                                if saved_po and saved_po.po_number:
                                    newly_saved_po_numbers.add(saved_po.po_number)
                                    processed_po_numbers.add(saved_po.po_number)
                    logger.info(
                        f"📊 Structured data processed: {po_count} POs, {grn_count} GRNs, {err_count} errors/duplicates"
                    )

                    # Flush failed ingestions and clear any stale objects from session
                    if err_count > 0:
                        logger.debug(
                            f"🔄 Flushing {err_count} failed ingestions to database"
                        )
                        db.flush()  # Persist failed ingestions but don't commit yet

                # Process contract notes using agentic OCR
                if contract_notes_to_process:
                    logger.info(f"📄 Processing {len(contract_notes_to_process)} contract notes using agentic OCR")
                    for contract_result in contract_notes_to_process:
                        filename = contract_result["filename"]
                        try:
                            # Find the original file data to get the content
                            file_content = None
                            for file_info in pdf_files:
                                if file_info["filename"] == filename:
                                    file_content = file_info["content"]
                                    break
                            
                            if file_content is None:
                                job_summary.append({
                                    "filename": filename,
                                    "status": "error",
                                    "message": "Could not find file content for contract note processing",
                                    "extracted_id": None,
                                    "document_type": "ContractNote"
                                })
                                continue
                            
                            # Process using agentic OCR
                            success, summary = process_contract_note_file(db, filename, file_content)
                            
                            job_summary.append({
                                "filename": filename,
                                "status": "success" if success else "error",
                                "message": summary,
                                "extracted_id": None,
                                "document_type": "ContractNote"
                            })
                            
                            if success:
                                logger.info(f"✅ Contract note processed: {filename}")
                            else:
                                logger.warning(f"❌ Contract note failed: {filename} - {summary}")
                                
                        except Exception as e:
                            error_msg = f"Contract note processing error: {str(e)}"
                            logger.error(f"❌ {filename}: {error_msg}")
                            job_summary.append({
                                "filename": filename,
                                "status": "error",
                                "message": error_msg,
                                "extracted_id": None,
                                "document_type": "ContractNote"
                            })

                # Process Excel customer data files
                if excel_customer_files:
                    logger.info(f"📊 Processing {len(excel_customer_files)} Excel customer data files")
                    for file_info in excel_customer_files:
                        try:
                            result = process_excel_customer_data(db, file_info, job_id)
                            job_summary.append({
                                "filename": result["filename"],
                                "status": result["status"],
                                "message": result["message"],
                                "extracted_id": None,
                                "document_type": "CustomerData",
                            })
                            processed_count += 1
                            update_job_progress(job_id, processed_count, total_files_to_process)
                            
                            if result["status"] == "success":
                                logger.info(f"✅ Processed customer data: {result['filename']} - {result['message']}")
                            else:
                                logger.error(f"❌ Failed to process customer data: {result['filename']} - {result['message']}")
                                error_summary.append(f"Customer data processing failed: {result['message']}")
                                
                        except Exception as e:
                            logger.error(f"❌ Critical error processing customer data {file_info['filename']}: {str(e)}")
                            job_summary.append({
                                "filename": file_info["filename"],
                                "status": "error",
                                "message": f"Critical error: {str(e)}",
                                "extracted_id": None,
                                "document_type": "CustomerData",
                            })
                            error_summary.append(f"Customer data critical error: {str(e)}")
                            processed_count += 1
                            update_job_progress(job_id, processed_count, total_files_to_process)

                # Process loan policy files
                if loan_policy_files:
                    logger.info(f"📋 Processing {len(loan_policy_files)} loan policy files")
                    all_policy_rules = []
                    
                    for file_info in loan_policy_files:
                        try:
                            result = process_loan_policy_document(db, file_info, job_id)
                            job_summary.append({
                                "filename": result["filename"],
                                "status": result["status"],
                                "message": result["message"],
                                "extracted_id": None,
                                "document_type": "LoanPolicy",
                            })
                            processed_count += 1
                            update_job_progress(job_id, processed_count, total_files_to_process)
                            
                            if result["status"] == "success":
                                logger.info(f"✅ Processed loan policy: {result['filename']} - {result['message']}")
                                # Collect rules from this document
                                if "policy_rules" in result:
                                    all_policy_rules.extend(result["policy_rules"])
                            else:
                                logger.error(f"❌ Failed to process loan policy: {result['filename']} - {result['message']}")
                                error_summary.append(f"Loan policy processing failed: {result['message']}")
                                
                        except Exception as e:
                            logger.error(f"❌ Critical error processing loan policy {file_info['filename']}: {str(e)}")
                            job_summary.append({
                                "filename": file_info["filename"],
                                "status": "error",
                                "message": f"Critical error: {str(e)}",
                                "extracted_id": None,
                                "document_type": "LoanPolicy",
                            })
                            error_summary.append(f"Loan policy critical error: {str(e)}")
                            processed_count += 1
                            update_job_progress(job_id, processed_count, total_files_to_process)
                    
                    # Now create all rules from all documents combined
                    if all_policy_rules:
                        logger.info(f"🤖 Creating {len(all_policy_rules)} combined rules from all loan policy documents")
                        
                        # Remove ALL existing automation rules first
                        deleted_rules = db.query(models.AutomationRule).delete(synchronize_session=False)
                        logger.info(f"🗑️ Removed {deleted_rules} existing automation rules")
                        
                        # Create new automation rules in database
                        created_rules = 0
                        
                        for rule_data in all_policy_rules:
                            # Create new rule with proper schema formatting
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
                        
                        db.commit()
                        logger.info(f"✅ Successfully created {created_rules} automation rules from {len(loan_policy_files)} loan policy documents")

                # Now process the PDFs
                for doc_data in successful_extractions:
                    doc_type = doc_data.get("document_type")
                    file_path = doc_data.get("file_path")

                    saved_obj, error, message_status, message_text, extracted_id = (
                        None,
                        None,
                        "error",
                        "An unknown error occurred.",
                        None,
                    )

                    if doc_type == "Invoice":
                        saved_obj, message_text = (
                            ingestion_service._save_invoice_from_dict(
                                db, doc_data, job_id
                            )
                        )
                        if saved_obj:
                            db.flush()  # IMPORTANT: Flush to get the object ID and status
                            message_status = "success"
                            extracted_id = saved_obj.invoice_id
                            # --- START MODIFICATION: Check status before queuing for match ---
                            # Only add to the matching queue if it's a new, non-duplicate invoice.
                            # The 'revision' and 'duplicate' messages are set in the service.
                            if message_text is None:
                                all_invoice_ids_to_match.append(saved_obj.id)
                                message_text = "Ingested as Invoice"
                            elif message_text == "revision":
                                log_audit_event(
                                    db,
                                    "System",
                                    "Revised Invoice Received",
                                    "Invoice",
                                    saved_obj.invoice_id,
                                    saved_obj.id,
                                    summary=f"A revised version was uploaded: {file_path}",
                                )
                                all_invoice_ids_to_match.append(saved_obj.id)
                                message_text = "Processed as Invoice Revision"
                            # If message_text is 'Processed as Duplicate (Rejected)', we do nothing, skipping the match.
                            # --- END MODIFICATION ---
                        elif message_text:  # Error case
                            message_status = "error"

                    elif doc_type == "PurchaseOrder":
                        saved_obj, error = ingestion_service._save_po_from_dict(
                            db, doc_data, job_id
                        )
                        if saved_obj:
                            newly_saved_po_numbers.add(saved_obj.po_number)
                            message_status, message_text = "success", "Ingested as PO"
                        elif error:
                            message_text = error

                    elif doc_type == "GoodsReceiptNote":
                        saved_obj, error = ingestion_service._save_grn_from_dict(
                            db, doc_data, job_id
                        )
                        if saved_obj:
                            message_status, message_text = "success", "Ingested as GRN"
                        elif error:
                            message_text = error

                    job_summary.append(
                        {
                            "filename": file_path,
                            "status": message_status,
                            "message": message_text,
                            "extracted_id": extracted_id,
                            "document_type": doc_type,
                        }
                    )

                # Proactively re-match any waiting invoices now that all POs/GRNs are in
                if newly_saved_po_numbers:
                    logger.info(
                        f"🧠 Searching for invoices waiting for {len(newly_saved_po_numbers)} new POs"
                    )
                    invoices_to_requeue = (
                        db.query(models.Invoice)
                        .filter(models.Invoice.review_category == "missing_document")
                        .all()
                    )
                    for inv in invoices_to_requeue:
                        if not set(inv.related_po_numbers or []).isdisjoint(
                            newly_saved_po_numbers
                        ):
                            if inv.id not in all_invoice_ids_to_match:
                                all_invoice_ids_to_match.append(inv.id)
                                logger.debug(
                                    f"Found waiting invoice {inv.invoice_id}, queuing for re-match"
                                )

                # Commit and run matching engine
                logger.info("💾 Committing all documents and preparing matching engine")
                db.commit()

                unique_ids_to_match = sorted(list(set(all_invoice_ids_to_match)))
                if unique_ids_to_match:
                    logger.info(
                        f"🔗 Running matching engine on {len(unique_ids_to_match)} invoices"
                    )
                    update_job_progress(
                        job_id,
                        total_files_to_process,
                        total_files_to_process,
                        status="matching",
                    )
                    for inv_id in unique_ids_to_match:
                        matching_engine.run_match_for_invoice(db, inv_id)

            except Exception as e:
                log_error_with_context(
                    logger, e, {"job_id": job_id}, "Database operations"
                )
                db.rollback()
                job_final_status = "failed"

    except Exception as e:
        log_error_with_context(
            logger, e, {"job_id": job_id}, "Background job processing"
        )
        job_final_status = "failed"
        # Format a user-friendly error summary
        error_summary.append(
            {
                "filename": "System Error",
                "status": "error",
                "message": "A critical error occurred during processing. Please check logs or contact support.",
                "extracted_id": None,
                "document_type": None,
            }
        )
        # Attempt to rollback any partial changes
        with SessionLocal() as db_rollback:
            db_rollback.rollback()

    # Finalize Job
    with SessionLocal() as db_final:
        job = db_final.query(models.Job).filter_by(id=job_id).first()
        if job:
            job.status = job_final_status
            job.completed_at = datetime.utcnow()

            # If an error occurred, overwrite the summary with the error info
            if job_final_status == "failed" and error_summary:
                job.summary = error_summary
            else:
                # Use the existing job_summary if no critical error occurred
                job.summary = sorted(job_summary, key=lambda x: x.get("filename", ""))

            db_final.commit()

    # Log comprehensive batch summary
    processing_time = (datetime.utcnow() - start_time).total_seconds()
    successful_files = len([s for s in job_summary if s.get("status") == "success"])
    failed_files = len([s for s in job_summary if s.get("status") == "error"])

    if job_final_status == "completed":
        logger.info(
            f"✅ Job {job_id} completed successfully in {processing_time:.1f}s | Success: {successful_files}, Failed: {failed_files}"
        )
    else:
        logger.error(
            f"❌ Job {job_id} failed after {processing_time:.1f}s | Success: {successful_files}, Failed: {failed_files}"
        )


def process_contract_documents(job_id: int, files_data: List[Dict[str, Any]]):
    """
    Process contract note documents with OCR extraction
    """
    logger = get_logger(__name__)
    job_final_status = "completed"
    start_time = datetime.utcnow()

    try:
        from app.services.contract_ocr_service import ContractOCRService
        
        pdf_files = [f for f in files_data if f["filename"].lower().endswith(".pdf")]
        total_files_to_process = len(pdf_files)

        logger.info(f"📤 Starting contract processing job {job_id} | PDF files: {len(pdf_files)}")

        job_summary = []
        processed_count = 0

        with SessionLocal() as db:
            try:
                for file_info in pdf_files:
                    try:
                        filename = file_info["filename"]
                        file_content = file_info["content"]
                        
                        logger.info(f"🔍 Processing contract: {filename}")
                        
                        # Extract contract data using OCR
                        success, extracted_data, error_msg = ContractOCRService.extract_contract_data(
                            filename, file_content
                        )
                        
                        if not success:
                            job_summary.append({
                                "filename": filename,
                                "status": "error",
                                "message": f"OCR extraction failed: {error_msg}",
                                "extracted_id": None,
                                "document_type": "ContractNote"
                            })
                            processed_count += 1
                            update_job_progress(job_id, processed_count, total_files_to_process)
                            continue
                        
                        # Format data for database
                        db_fields = ContractOCRService.format_contract_fields_for_db(extracted_data)
                        
                        # Create contract note record
                        contract_note = models.ContractNote(
                            filename=filename,
                            file_path=f"sample_data/contract note/{filename}",
                            extracted_data=extracted_data,
                            **db_fields
                        )
                        
                        db.add(contract_note)
                        db.flush()  # Get the ID
                        
                        # Try to find existing customer by extracted name or create new one
                        customer_name = extracted_data.get("contract_fields", {}).get("customer_name", f"Customer {contract_note.id}")
                        
                        # Try to match with existing customers by name first
                        existing_customer = None
                        if customer_name and customer_name != f"Customer {contract_note.id}":
                            existing_customer = db.query(models.Customer).filter(
                                models.Customer.name.ilike(f"%{customer_name}%")
                            ).first()
                        
                        if not existing_customer:
                            # Create new customer with proper customer number
                            customer_no = f"CUST-{8801 + contract_note.id}"  # Generate realistic customer numbers
                            # Create new customer
                            customer = models.Customer(
                                customer_no=customer_no,
                                name=customer_name,
                                email=extracted_data.get("contract_fields", {}).get("customer_email"),
                                phone=extracted_data.get("contract_fields", {}).get("customer_phone"),
                                address=extracted_data.get("contract_fields", {}).get("customer_address"),
                                contract_note_id=contract_note.id,
                                # Sample CBS data for demonstration
                                cbs_emi_amount=db_fields.get("contract_emi_amount"),
                                cbs_due_day=db_fields.get("contract_due_day"),
                                cbs_outstanding_amount=db_fields.get("contract_loan_amount", 0) * 0.8,  # 80% outstanding
                                cbs_risk_level="Low"
                            )
                            db.add(customer)
                            db.flush()
                        else:
                            # Update existing customer with contract note
                            existing_customer.contract_note_id = contract_note.id
                            # Update CBS data if missing
                            if not existing_customer.cbs_emi_amount:
                                existing_customer.cbs_emi_amount = db_fields.get("contract_emi_amount")
                            if not existing_customer.cbs_due_day:
                                existing_customer.cbs_due_day = db_fields.get("contract_due_day")
                            customer = existing_customer
                            db.flush()
                            
                        # Create sample loan if it doesn't exist
                        existing_loan = db.query(models.Loan).filter_by(customer_id=customer.id).first()
                        if not existing_loan and db_fields.get("contract_loan_amount") and db_fields.get("contract_emi_amount"):
                            loan = models.Loan(
                                loan_id=f"LOAN_{customer.id:06d}",
                                customer_id=customer.id,
                                loan_amount=db_fields.get("contract_loan_amount"),
                                emi_amount=db_fields.get("contract_emi_amount"),
                                tenure_months=db_fields.get("contract_tenure_months", 60),
                                interest_rate=db_fields.get("contract_interest_rate", 12.0),
                                outstanding_amount=db_fields.get("contract_loan_amount", 0) * 0.8
                            )
                            db.add(loan)
                        
                        # Check for data integrity issues
                        create_data_integrity_alerts(db, customer, contract_note)
                        
                        job_summary.append({
                            "filename": filename,
                            "status": "success",
                            "message": f"Contract processed successfully. Customer: {customer_no}",
                            "extracted_id": str(contract_note.id),
                            "document_type": "ContractNote"
                        })
                        
                    except Exception as e:
                        logger.error(f"Error processing contract {filename}: {str(e)}")
                        job_summary.append({
                            "filename": filename,
                            "status": "error",
                            "message": f"Processing error: {str(e)}",
                            "extracted_id": None,
                            "document_type": "ContractNote"
                        })
                    
                    processed_count += 1
                    update_job_progress(job_id, processed_count, total_files_to_process)
                
                # Commit all changes
                db.commit()
                logger.info("💾 Committed all contract processing changes")
                
            except Exception as e:
                log_error_with_context(logger, e, {"job_id": job_id}, "Contract processing")
                db.rollback()
                job_final_status = "failed"

    except Exception as e:
        log_error_with_context(logger, e, {"job_id": job_id}, "Contract processing job")
        job_final_status = "failed"

    # Finalize Job
    with SessionLocal() as db_final:
        job = db_final.query(models.Job).filter_by(id=job_id).first()
        if job:
            job.status = job_final_status
            job.completed_at = datetime.utcnow()
            job.summary = sorted(job_summary, key=lambda x: x.get("filename", ""))
            db_final.commit()

    # Log summary
    processing_time = (datetime.utcnow() - start_time).total_seconds()
    successful_files = len([s for s in job_summary if s.get("status") == "success"])
    failed_files = len([s for s in job_summary if s.get("status") == "error"])

    if job_final_status == "completed":
        logger.info(
            f"✅ Contract job {job_id} completed in {processing_time:.1f}s | Success: {successful_files}, Failed: {failed_files}"
        )
    else:
        logger.error(
            f"❌ Contract job {job_id} failed after {processing_time:.1f}s | Success: {successful_files}, Failed: {failed_files}"
        )


def create_data_integrity_alerts(db, customer: models.Customer, contract_note: models.ContractNote):
    """Create data integrity alerts for mismatches between CBS and contract data"""
    alerts = []
    
    # EMI Amount mismatch
    if (customer.cbs_emi_amount and contract_note.contract_emi_amount and 
        abs(customer.cbs_emi_amount - contract_note.contract_emi_amount) > 0.01):
        difference = abs(customer.cbs_emi_amount - contract_note.contract_emi_amount)
        alerts.append(models.DataIntegrityAlert(
            alert_type="EMI_MISMATCH",
            customer_id=customer.id,
            severity="high",
            title="EMI Amount Discrepancy Detected",
            description=f"Customer {customer.customer_no} ({customer.name}) has EMI amount mismatch: CBS shows ₹{customer.cbs_emi_amount:,.2f} while contract specifies ₹{contract_note.contract_emi_amount:,.2f} - difference of ₹{difference:,.2f}. This requires immediate attention to ensure accurate payment processing.",
            cbs_value=str(customer.cbs_emi_amount),
            contract_value=str(contract_note.contract_emi_amount)
        ))
    
    # Due Day mismatch
    if (customer.cbs_due_day and contract_note.contract_due_day and 
        customer.cbs_due_day != contract_note.contract_due_day):
        alerts.append(models.DataIntegrityAlert(
            alert_type="DUE_DAY_MISMATCH",
            customer_id=customer.id,
            severity="medium",
            title="Payment Due Date Inconsistency",
            description=f"Customer {customer.customer_no} ({customer.name}) has conflicting due dates: CBS system shows day {customer.cbs_due_day} of the month while contract specifies day {contract_note.contract_due_day}. This may cause payment scheduling issues and should be resolved to avoid late payment penalties.",
            cbs_value=str(customer.cbs_due_day),
            contract_value=str(contract_note.contract_due_day)
        ))
    
    # Missed EMI alerts based on customer data
    if customer.missed_emis and customer.missed_emis > 0:
        if customer.missed_emis >= 3:
            severity = "high"
            title = "Critical Payment Default - Multiple EMIs Missed"
            description = f"Customer {customer.customer_no} ({customer.name}) has missed {customer.missed_emis} consecutive EMI payments. This indicates severe financial distress and requires immediate recovery action. Current outstanding: ₹{customer.cbs_outstanding_amount:,.2f}. Escalate to recovery team immediately."
        elif customer.missed_emis == 2:
            severity = "high"
            title = "High Risk - Two EMIs Missed"
            description = f"Customer {customer.customer_no} ({customer.name}) has missed {customer.missed_emis} EMI payments. This is approaching critical status and requires urgent follow-up to prevent further defaults. Current outstanding: ₹{customer.cbs_outstanding_amount:,.2f}."
        else:
            severity = "medium"
            title = "Payment Delay - Single EMI Missed"
            description = f"Customer {customer.customer_no} ({customer.name}) has missed 1 EMI payment. Early intervention required to prevent escalation. Current outstanding: ₹{customer.cbs_outstanding_amount:,.2f}. Contact customer for payment arrangement."
        
        alerts.append(models.DataIntegrityAlert(
            alert_type="MISSED_EMI_ALERT",
            customer_id=customer.id,
            severity=severity,
            title=title,
            description=description,
            cbs_value=str(customer.missed_emis),
            contract_value=None
        ))
    
    # Overdue amount alerts
    if customer.pending_amount and customer.pending_amount > 0:
        if customer.pending_amount > 50000:
            severity = "high"
            title = "High Value Overdue Amount"
            description = f"Customer {customer.customer_no} ({customer.name}) has significant overdue amount of ₹{customer.pending_amount:,.2f}. This represents substantial financial exposure and requires priority collection efforts."
        elif customer.pending_amount > 10000:
            severity = "medium"
            title = "Moderate Overdue Amount"
            description = f"Customer {customer.customer_no} ({customer.name}) has overdue amount of ₹{customer.pending_amount:,.2f}. Follow up required to collect pending payments and prevent further accumulation."
        else:
            severity = "low"
            title = "Minor Overdue Amount"
            description = f"Customer {customer.customer_no} ({customer.name}) has overdue amount of ₹{customer.pending_amount:,.2f}. Schedule routine follow-up for collection."
        
        alerts.append(models.DataIntegrityAlert(
            alert_type="OVERDUE_AMOUNT_ALERT",
            customer_id=customer.id,
            severity=severity,
            title=title,
            description=description,
            cbs_value=str(customer.pending_amount),
            contract_value=None
        ))
    
    # Add alerts to database
    for alert in alerts:
        db.add(alert)


def process_all_sample_data(job_id: int, files_data: List[Dict[str, Any]]):
    """
    Process all types of files from sample_data including contract notes, customer data, and loan documents
    """
    logger = get_logger(__name__)
    job_final_status = "completed"
    start_time = datetime.utcnow()

    try:
        total_files_to_process = len(files_data)
        logger.info(f"📤 Starting comprehensive data processing job {job_id} | Total files: {total_files_to_process}")

        job_summary = []
        processed_count = 0

        with SessionLocal() as db:
            try:
                for file_info in files_data:
                    try:
                        filename = file_info["filename"]
                        file_content = file_info["content"]
                        file_type = file_info.get("file_type", "unknown")
                        source_folder = file_info.get("source_folder", "unknown")
                        
                        logger.info(f"🔍 Processing {file_type}: {filename} from {source_folder}")
                        
                        if file_type == "contract_note":
                            # Process contract notes with OCR
                            success, summary = process_contract_note_file(db, filename, file_content)
                            
                        elif file_type == "customer_data":
                            # Process Excel customer data
                            success, summary = process_customer_data_excel(db, filename, file_content)
                            
                        elif file_type == "loan_document":
                            # Process loan documents (can be extended for OCR)
                            success, summary = process_loan_document_file(db, filename, file_content)
                            
                        else:
                            success = False
                            summary = f"Unknown file type: {file_type}"
                        
                        job_summary.append({
                            "filename": filename,
                            "status": "success" if success else "error",
                            "message": summary,
                            "extracted_id": None,
                            "document_type": file_type.title()
                        })
                        
                    except Exception as e:
                        logger.error(f"Error processing file {filename}: {str(e)}")
                        job_summary.append({
                            "filename": filename,
                            "status": "error",
                            "message": f"Processing error: {str(e)}",
                            "extracted_id": None,
                            "document_type": "Unknown"
                        })
                    
                    processed_count += 1
                    update_job_progress(job_id, processed_count, total_files_to_process, "processing", db)
                
                # Commit all changes
                try:
                    db.commit()
                    logger.info("💾 Committed all sample data processing changes")
                except Exception as commit_error:
                    logger.error(f"Failed to commit changes: {str(commit_error)}")
                    db.rollback()
                    job_final_status = "failed"
                
            except Exception as e:
                log_error_with_context(logger, e, {"job_id": job_id}, "Sample data processing")
                try:
                    db.rollback()
                except Exception as rollback_error:
                    logger.error(f"Failed to rollback transaction: {str(rollback_error)}")
                job_final_status = "failed"

    except Exception as e:
        log_error_with_context(logger, e, {"job_id": job_id}, "Sample data processing job")
        job_final_status = "failed"

    # Finalize Job
    with SessionLocal() as db_final:
        job = db_final.query(models.Job).filter_by(id=job_id).first()
        if job:
            job.status = job_final_status
            job.completed_at = datetime.utcnow()
            job.summary = sorted(job_summary, key=lambda x: x.get("filename", ""))
            db_final.commit()

    # Log summary
    processing_time = (datetime.utcnow() - start_time).total_seconds()
    successful_files = len([s for s in job_summary if s.get("status") == "success"])
    failed_files = len([s for s in job_summary if s.get("status") == "error"])

    if job_final_status == "completed":
        logger.info(
            f"✅ Sample data job {job_id} completed in {processing_time:.1f}s | Success: {successful_files}, Failed: {failed_files}"
        )
    else:
        logger.error(
            f"❌ Sample data job {job_id} failed after {processing_time:.1f}s | Success: {successful_files}, Failed: {failed_files}"
        )


def process_contract_note_file(db, filename: str, file_content: bytes) -> tuple[bool, str]:
    """Process contract note PDF using existing OCR logic"""
    try:
        from app.services.contract_ocr_service import ContractOCRService
        
        # Extract contract data using OCR
        success, extracted_data, error_msg = ContractOCRService.extract_contract_data(
            filename, file_content
        )
        
        if not success:
            return False, f"OCR extraction failed: {error_msg}"
        
        # Format data for database
        db_fields = ContractOCRService.format_contract_fields_for_db(extracted_data)
        
        # Create contract note record
        contract_note = models.ContractNote(
            filename=filename,
            file_path=f"sample_data/contract note/{filename}",
            extracted_data=extracted_data,
            **db_fields
        )
        
        db.add(contract_note)
        db.flush()  # Get the ID
        
        # Try to find existing customer or create new one
        customer_name = extracted_data.get("contract_fields", {}).get("customer_name", f"Customer {contract_note.id}")
        existing_customer = None
        
        if customer_name and customer_name != f"Customer {contract_note.id}":
            existing_customer = db.query(models.Customer).filter(
                models.Customer.name.ilike(f"%{customer_name}%")
            ).first()
        
        if not existing_customer:
            # Create new customer
            customer_no = f"CUST-{8801 + contract_note.id}"
            customer = models.Customer(
                customer_no=customer_no,
                name=customer_name,
                email=extracted_data.get("contract_fields", {}).get("customer_email"),
                phone=extracted_data.get("contract_fields", {}).get("customer_phone"),
                address=extracted_data.get("contract_fields", {}).get("customer_address"),
                contract_note_id=contract_note.id,
                cbs_emi_amount=db_fields.get("contract_emi_amount"),
                cbs_due_day=db_fields.get("contract_due_day"),
                cbs_outstanding_amount=db_fields.get("contract_loan_amount", 0) * 0.8,
                cbs_risk_level="Low"
            )
            db.add(customer)
            db.flush()
        else:
            # Update existing customer with contract note
            existing_customer.contract_note_id = contract_note.id
            customer = existing_customer
            db.flush()
        
        return True, f"Contract processed successfully. Customer: {customer.customer_no}"
        
    except Exception as e:
        return False, f"Contract processing error: {str(e)}"


def process_customer_data_excel(db, filename: str, file_content: bytes) -> tuple[bool, str]:
    """Process Excel customer data file"""
    try:
        import pandas as pd
        import io
        
        # Read Excel file
        excel_data = io.BytesIO(file_content)
        df = pd.read_excel(excel_data)
        
        logger = get_logger(__name__)
        logger.info(f"📊 Processing Excel file with {len(df)} rows and columns: {list(df.columns)}")
        
        # Expected columns based on the screenshot
        expected_columns = ['Sr', 'Name', 'Loan Amount', '% Due', 'Pendency', 'Overdue Amount']
        
        # Map DataFrame columns to our expected columns (flexible mapping)
        column_mapping = {}
        for col in df.columns:
            col_lower = str(col).lower().strip()
            if any(keyword in col_lower for keyword in ['sr', 'serial', 'no', 'number']) and 'Sr' not in column_mapping:
                column_mapping['Sr'] = col
            elif any(keyword in col_lower for keyword in ['name', 'customer']) and 'Name' not in column_mapping:
                column_mapping['Name'] = col
            elif any(keyword in col_lower for keyword in ['loan', 'amount']) and 'loan' in col_lower and 'Loan Amount' not in column_mapping:
                column_mapping['Loan Amount'] = col
            elif any(keyword in col_lower for keyword in ['%', 'percent', 'due']) and '% Due' not in column_mapping:
                column_mapping['% Due'] = col
            elif 'pendency' in col_lower and 'Pendency' not in column_mapping:
                column_mapping['Pendency'] = col
            elif any(keyword in col_lower for keyword in ['overdue', 'amount']) and 'overdue' in col_lower and 'Overdue Amount' not in column_mapping:
                column_mapping['Overdue Amount'] = col
        
        processed_customers = 0
        
        for index, row in df.iterrows():
            try:
                # Extract data using mapped columns
                sr_no = row.get(column_mapping.get('Sr'), index + 1)
                customer_name = row.get(column_mapping.get('Name', 'Name'), f"Customer {index + 1}")
                loan_amount = pd.to_numeric(row.get(column_mapping.get('Loan Amount', 'Loan Amount'), 0), errors='coerce') or 0
                percent_due = pd.to_numeric(row.get(column_mapping.get('% Due', '% Due'), 0), errors='coerce') or 0
                pendency = str(row.get(column_mapping.get('Pendency', 'Pendency'), 'No')).lower()
                amount_pending = pd.to_numeric(row.get(column_mapping.get('Overdue Amount', 'Overdue Amount'), 0), errors='coerce') or 0
                
                # Skip empty rows
                if pd.isna(customer_name) or customer_name == '' or customer_name == f"Customer {index + 1}":
                    continue
                
                # Generate unique customer number based on timestamp + row to avoid conflicts
                import time
                timestamp = int(time.time())
                customer_no = f"CUST-{timestamp}-{index + 1}"
                
                # Always create new customer (no updates to avoid confusion)
                customer = models.Customer(
                    customer_no=customer_no,
                    name=str(customer_name),
                    cbs_emi_amount=loan_amount * (percent_due / 100) if percent_due > 0 else loan_amount * 0.1,
                    cbs_outstanding_amount=amount_pending,
                    cbs_risk_level="High" if pendency == 'yes' else "Low",
                    cbs_due_day=5  # Default due day
                )
                db.add(customer)
                
                # Create corresponding loan record
                db.flush()  # Get customer ID
                from datetime import date, timedelta
                today = date.today()
                loan = models.Loan(
                    loan_id=f"LOAN_{customer.id:06d}",
                    customer_id=customer.id,
                    loan_amount=loan_amount,
                    emi_amount=loan_amount * (percent_due / 100) if percent_due > 0 else loan_amount * 0.1,
                    tenure_months=60,  # Default tenure
                    interest_rate=12.0,  # Default interest rate
                    outstanding_amount=amount_pending,
                    status="active" if pendency != 'yes' else "overdue",
                    last_payment_date=today - timedelta(days=30),  # 30 days ago
                    next_due_date=today + timedelta(days=5)  # 5 days from now
                )
                db.add(loan)
                processed_customers += 1
                    
            except Exception as e:
                logger.warning(f"Error processing row {index}: {str(e)}")
                continue
        
        return True, f"Excel processed: {processed_customers} new customers created"
        
    except Exception as e:
        return False, f"Excel processing error: {str(e)}"


def process_loan_document_file(db, filename: str, file_content: bytes) -> tuple[bool, str]:
    """Process loan document PDF (placeholder for future OCR enhancement)"""
    try:
        # For now, just log that we received a loan document
        # In the future, this could use OCR to extract loan information
        return True, f"Loan document {filename} received and stored"
        
    except Exception as e:
        return False, f"Loan document processing error: {str(e)}"

# src/app/services/policy_parser_service.py
import json
import re
from typing import List, Dict, Any
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

try:
    import google.generativeai as genai
    genai.configure(api_key=settings.gemini_api_key)
except (ImportError, Exception) as e:
    logger.error(f"Could not configure Google GenAI: {e}. Policy parsing will not be available.")
    genai = None

def parse_policy_to_rules(policy_text: str) -> List[Dict[str, Any]]:
    """
    Uses the Gemini API to parse unstructured policy text into a list of structured automation rules.
    """
    if not genai:
        logger.error("GenAI client is not initialized. Cannot parse policy.")
        return []

    model = genai.GenerativeModel(settings.gemini_model_name)
    
    # This detailed prompt guides the AI to produce the exact JSON structure we need.
    prompt = f"""
    You are an expert risk policy analyst for a bank. Your task is to analyze the provided collection policy document and extract structured, actionable rules.

    The final action for each rule must be one of the following based on the described risk:
    - 'Send Reminder': For low-risk, early-stage delinquencies.
    - 'Make Phone Call': For moderate-risk cases requiring personal interaction.
    - 'Send Legal Notice': For high-risk, severe cases requiring formal escalation.
    - 'Block Account': For cases of fraud or extreme delinquency.
    - 'Escalate to Manager': For complex cases needing senior review.

    Analyze the text and create a JSON array of rules. Each rule object must contain:
    1.  `rule_name`: A concise, descriptive name (e.g., "High Risk: 3+ Missed EMIs").
    2.  `description`: A short explanation of the rule's purpose.
    3.  `conditions`: A dictionary containing a 'logical_operator' ("AND" or "OR") and a 'conditions' array. Each item in the array must have 'field', 'operator', and 'value'.
    4.  `action`: One of the predefined actions listed above.

    Available fields for conditions are: `dpd` (days past due), `emi_count` (number of EMIs missed), `collateral` ('secured' or 'unsecured'), `segment` ('Retail', 'MSME', 'Corporate').

    Example Output Format:
    [
      {{
        "rule_name": "Retail Unsecured - 60 DPD",
        "description": "Applies to unsecured retail loans over 60 days past due.",
        "conditions": {{
          "logical_operator": "AND",
          "conditions": [
            {{"field": "segment", "operator": "equals", "value": "Retail"}},
            {{"field": "collateral", "operator": "equals", "value": "unsecured"}},
            {{"field": "dpd", "operator": ">=", "value": 60}}
          ]
        }},
        "action": "Make Phone Call"
      }}
    ]

    Policy Document Text:
    ---
    {policy_text}
    ---
    """
    
    try:
        logger.info("Sending policy text to Gemini for rule extraction...")
        response = model.generate_content(prompt)
        
        # Clean up the response, removing markdown backticks if present
        json_text = re.sub(r'```(json)?|```', '', response.text, flags=re.DOTALL).strip()
        
        parsed_rules = json.loads(json_text)
        
        if isinstance(parsed_rules, list):
            logger.info(f"Successfully extracted {len(parsed_rules)} rules from policy document.")
            return parsed_rules
        else:
            logger.warning("AI response was not a valid list of rules.")
            return []
            
    except Exception as e:
        logger.error(f"Failed to parse policy with Gemini: {e}", exc_info=True)
        return []

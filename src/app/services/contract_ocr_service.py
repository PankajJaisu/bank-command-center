# src/app/services/contract_ocr_service.py
import requests
import json
import re
from typing import Dict, Any, Optional, Tuple
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# OCR API Configuration
OCR_API_URL = "http://4.236.205.190:8000/api/v1/new_agentic_ocr"
OCR_MODEL = "gemini-2.5-flash"

# Contract extraction prompt
CONTRACT_EXTRACTION_PROMPT = """
This is a loan contract document. Extract the following key details and return them in a JSON structure:

1. EMI Amount (monthly installment amount) - look for amounts like ₹8,500.00, Rs. 8500, etc.
2. EMI Due Day (day of month when EMI is due) - look for patterns like "5th of every month", "due on 15th", etc.
3. Late Fee Percentage - look for late fee, penalty charges, or overdue charges as percentage
4. Default Clause - conditions that constitute default (like "3 consecutive missed EMIs")
5. Governing Law - jurisdiction or state law that governs the contract
6. Interest Rate - annual or monthly interest rate
7. Loan Amount - principal loan amount
8. Tenure - loan tenure in months or years
9. Customer Name - borrower's name
10. Customer Details - address, phone, email if available

Return the data in this exact JSON format:
{
    "emi_amount": <float or null>,
    "due_day": <integer (1-31) or null>,
    "late_fee_percent": <float or null>,
    "default_clause": "<text or null>",
    "governing_law": "<text or null>",
    "interest_rate": <float or null>,
    "loan_amount": <float or null>,
    "tenure_months": <integer or null>,
    "customer_name": "<text or null>",
    "customer_address": "<text or null>",
    "customer_phone": "<text or null>",
    "customer_email": "<text or null>"
}

Important: Extract numerical values without currency symbols. Convert percentages to decimal format (e.g., 2% as 2.0).
"""


class ContractOCRService:
    """Service for extracting contract data using OCR API"""

    @staticmethod
    def extract_contract_data(file_path: str, file_content: bytes) -> Tuple[bool, Dict[str, Any], Optional[str]]:
        """
        Extract contract data from PDF using OCR API
        
        Args:
            file_path: Path to the contract file
            file_content: Binary content of the PDF file
            
        Returns:
            Tuple of (success, extracted_data, error_message)
        """
        try:
            # Prepare the request
            files = {
                'file': ('contract.pdf', file_content, 'application/pdf')
            }
            data = {
                'prompt': CONTRACT_EXTRACTION_PROMPT,
                'model': OCR_MODEL
            }
            
            logger.info(f"Sending contract for OCR extraction: {file_path}")
            
            # Make the API request
            response = requests.post(
                OCR_API_URL,
                files=files,
                data=data,
                timeout=120  # 2 minutes timeout for large files
            )
            
            if response.status_code != 200:
                error_msg = f"OCR API returned status {response.status_code}: {response.text}"
                logger.error(error_msg)
                return False, {}, error_msg
                
            # Parse the response
            ocr_result = response.json()
            logger.info(f"OCR API response received for {file_path}")
            
            # Extract and parse the contract data
            extracted_data = ContractOCRService._parse_ocr_response(ocr_result)
            
            return True, extracted_data, None
            
        except requests.RequestException as e:
            error_msg = f"Network error during OCR request: {str(e)}"
            logger.error(error_msg)
            return False, {}, error_msg
            
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse OCR response as JSON: {str(e)}"
            logger.error(error_msg)
            return False, {}, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error during contract extraction: {str(e)}"
            logger.error(error_msg)
            return False, {}, error_msg

    @staticmethod
    def _parse_ocr_response(ocr_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse the OCR API response and extract structured contract data
        
        Args:
            ocr_result: Raw response from OCR API
            
        Returns:
            Parsed contract data dictionary
        """
        extracted_data = {
            "raw_ocr_response": ocr_result,
            "contract_fields": {}
        }
        
        try:
            # The OCR API might return different response formats
            # Try to extract the text content from various possible response structures
            text_content = ""
            
            if isinstance(ocr_result, dict):
                # Look for common response fields
                if "response" in ocr_result:
                    text_content = str(ocr_result["response"])
                elif "text" in ocr_result:
                    text_content = str(ocr_result["text"])
                elif "result" in ocr_result:
                    text_content = str(ocr_result["result"])
                elif "extracted_text" in ocr_result:
                    text_content = str(ocr_result["extracted_text"])
                else:
                    # If it's a simple dict, try to extract JSON from it
                    text_content = json.dumps(ocr_result)
            else:
                text_content = str(ocr_result)
            
            # Try to extract JSON from the text content
            contract_fields = ContractOCRService._extract_json_from_text(text_content)
            
            if contract_fields:
                extracted_data["contract_fields"] = contract_fields
            else:
                # Fallback: try to extract individual fields using regex
                extracted_data["contract_fields"] = ContractOCRService._extract_fields_with_regex(text_content)
                
        except Exception as e:
            logger.warning(f"Error parsing OCR response: {str(e)}")
            extracted_data["contract_fields"] = {}
            
        return extracted_data

    @staticmethod
    def _extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
        """
        Try to extract JSON from text content
        """
        try:
            # Look for JSON patterns in the text
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            json_matches = re.findall(json_pattern, text, re.DOTALL)
            
            for match in json_matches:
                try:
                    parsed = json.loads(match)
                    if isinstance(parsed, dict):
                        # Validate that it contains expected contract fields
                        expected_fields = ['emi_amount', 'due_day', 'late_fee_percent']
                        if any(field in parsed for field in expected_fields):
                            return parsed
                except json.JSONDecodeError:
                    continue
                    
            # If no JSON found, try parsing the entire text as JSON
            return json.loads(text)
            
        except Exception:
            return None

    @staticmethod
    def _extract_fields_with_regex(text: str) -> Dict[str, Any]:
        """
        Fallback method to extract contract fields using regex patterns
        """
        fields = {}
        
        try:
            # EMI Amount patterns
            emi_patterns = [
                r'emi[^0-9]*(?:rs\.?|₹|rupees?)[^0-9]*([0-9,]+(?:\.[0-9]{2})?)',
                r'monthly[^0-9]*(?:rs\.?|₹|rupees?)[^0-9]*([0-9,]+(?:\.[0-9]{2})?)',
                r'installment[^0-9]*(?:rs\.?|₹|rupees?)[^0-9]*([0-9,]+(?:\.[0-9]{2})?)'
            ]
            
            for pattern in emi_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    emi_str = match.group(1).replace(',', '')
                    try:
                        fields['emi_amount'] = float(emi_str)
                        break
                    except ValueError:
                        continue
            
            # Due Day patterns
            due_day_patterns = [
                r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(?:every\s+)?month',
                r'due\s+(?:on\s+)?(\d{1,2})(?:st|nd|rd|th)?',
                r'payable\s+(?:on\s+)?(\d{1,2})(?:st|nd|rd|th)?'
            ]
            
            for pattern in due_day_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        day = int(match.group(1))
                        if 1 <= day <= 31:
                            fields['due_day'] = day
                            break
                    except ValueError:
                        continue
            
            # Late Fee patterns
            late_fee_patterns = [
                r'late\s+fee[^0-9]*([0-9]+(?:\.[0-9]+)?)%',
                r'penalty[^0-9]*([0-9]+(?:\.[0-9]+)?)%',
                r'overdue[^0-9]*([0-9]+(?:\.[0-9]+)?)%'
            ]
            
            for pattern in late_fee_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        fields['late_fee_percent'] = float(match.group(1))
                        break
                    except ValueError:
                        continue
            
            # Interest Rate patterns
            interest_patterns = [
                r'interest\s+rate[^0-9]*([0-9]+(?:\.[0-9]+)?)%',
                r'rate\s+of\s+interest[^0-9]*([0-9]+(?:\.[0-9]+)?)%'
            ]
            
            for pattern in interest_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        fields['interest_rate'] = float(match.group(1))
                        break
                    except ValueError:
                        continue
            
            # Loan Amount patterns
            loan_amount_patterns = [
                r'loan\s+amount[^0-9]*(?:rs\.?|₹|rupees?)[^0-9]*([0-9,]+(?:\.[0-9]{2})?)',
                r'principal[^0-9]*(?:rs\.?|₹|rupees?)[^0-9]*([0-9,]+(?:\.[0-9]{2})?)'
            ]
            
            for pattern in loan_amount_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    amount_str = match.group(1).replace(',', '')
                    try:
                        fields['loan_amount'] = float(amount_str)
                        break
                    except ValueError:
                        continue
            
        except Exception as e:
            logger.warning(f"Error in regex extraction: {str(e)}")
            
        return fields

    @staticmethod
    def format_contract_fields_for_db(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format extracted contract fields for database storage
        """
        contract_fields = extracted_data.get("contract_fields", {})
        
        # Map extracted fields to database column names
        db_fields = {}
        
        # Direct mappings
        field_mappings = {
            'emi_amount': 'contract_emi_amount',
            'due_day': 'contract_due_day',
            'late_fee_percent': 'contract_late_fee_percent',
            'default_clause': 'contract_default_clause',
            'governing_law': 'contract_governing_law',
            'interest_rate': 'contract_interest_rate',
            'loan_amount': 'contract_loan_amount',
            'tenure_months': 'contract_tenure_months'
        }
        
        for source_field, db_field in field_mappings.items():
            if source_field in contract_fields and contract_fields[source_field] is not None:
                db_fields[db_field] = contract_fields[source_field]
        
        return db_fields

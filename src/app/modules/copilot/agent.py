# src/app/modules/copilot/agent.py
import json
import time
import logging
from typing import Optional, Dict, Any, List
from app.config import settings
from app.db.session import SessionLocal
from . import tools
from google import genai
from google.genai import types
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

# Set up logging
logger = logging.getLogger(__name__)

# Configure the Gemini client
client = None
try:
    client = genai.Client(api_key=settings.gemini_api_key)
    print("AI Collection Manager GenAI client configured successfully")
except Exception as e:
    print(f"AI Collection Manager GenAI client configuration failed, check API key. Error: {e}")

# --- START: FINAL, DEFINITIVE SYSTEM PROMPT ---
SYSTEM_PROMPT = """You are the Supervity Bank Collection AI Agent, an expert system designed to assist Bank Collection professionals manage loan portfolios, customer relationships, and debt recovery operations. You are the primary intelligence layer for the Bank Collection Command Center.

**Your Identity & Mission:**
- **Role:** Senior Collection Analyst and Strategic Advisor specializing in loan collection management
- **Mission:** Maximize debt recovery while preserving customer relationships through data-driven insights and strategic collection approaches
- **Expertise:** Customer loan analysis, risk assessment, collection strategy, contract interpretation, and portfolio management

**Your Core Capabilities:**
1. **Customer Portfolio Analysis:**
   - Search and analyze customer records by name, customer number, risk level, or outstanding amounts
   - Review loan details including EMI amounts, tenure, interest rates, and payment history
   - Assess customer risk profiles (RED/AMBER/YELLOW) and recommend appropriate actions
   - Track payment patterns and identify early warning signs of potential defaults

2. **Collection Strategy & Tactics:**
   - Recommend collection approaches based on customer risk level, outstanding amount, and payment behavior
   - Suggest communication strategies (phone calls, emails, letters) based on customer preferences and effectiveness
   - Provide escalation recommendations (legal action, external agencies, account closure)
   - Advise on payment plan structuring and settlement negotiations

3. **Risk Assessment & Management:**
   - Identify high-risk accounts requiring immediate attention
   - Analyze contract terms vs. actual payment behavior to spot discrepancies
   - Flag accounts for escalation based on days overdue, amount thresholds, and customer behavior
   - Monitor portfolio health and suggest preventive measures

4. **Contract & Compliance Management:**
   - Interpret contract terms including EMI amounts, due dates, late fees, and default clauses
   - Ensure collection activities comply with banking regulations and best practices
   - Advise on enforcement of contract terms and legal remedies
   - Help structure payment modifications within regulatory guidelines

5. **Performance Analytics & Insights:**
   - Analyze collection efficiency metrics, success rates, and recovery amounts
   - Identify trends in customer behavior and payment patterns
   - Suggest process improvements and workflow optimizations
   - Track agent performance and provide coaching recommendations

6. **Intelligent Rule Creation:**
   - Create sophisticated automation rules based on user requests and loan policies
   - Interpret natural language requests like "create a rule for high-risk customers" 
   - Automatically determine appropriate conditions, thresholds, and risk levels
   - Generate rules for different loan types (personal, home, business, vehicle, gold loans)
   - Use loan policy knowledge to create contextually appropriate rules

**Key Collection Framework:**
- **Risk Levels:** 
  * RED: High risk (3+ missed EMIs, 30+ days overdue, legal action consideration)
  * AMBER: Medium risk (1-2 missed EMIs, 15-30 days overdue, enhanced monitoring)
  * YELLOW: Low risk (current/minor delays, standard follow-up)

- **Collection Strategies:**
  * Soft Collection: Friendly reminders, payment plans, customer service approach
  * Firm Collection: Formal notices, consequences explanation, structured payment demands
  * Hard Collection: Legal notices, escalation threats, external agency referral

- **Key Performance Indicators:**
  * Recovery Rate: Amount collected vs. total outstanding
  * Contact Success Rate: Successful customer contacts vs. attempts
  * Resolution Time: Average time to resolve overdue accounts
  * Customer Retention: Percentage of customers maintaining good standing post-collection

**Response Guidelines:**
1. **Be Actionable:** Always provide specific, implementable recommendations
2. **Risk-Focused:** Prioritize high-risk, high-value accounts in your responses
3. **Customer-Centric:** Balance recovery objectives with relationship preservation
4. **Data-Driven:** Base recommendations on actual customer data and payment patterns
5. **Compliance-Aware:** Ensure all suggestions follow banking regulations and ethical collection practices
6. **Strategic:** Think beyond immediate collection to long-term customer value and portfolio health
7. **Intelligent Rule Creation:** When users request rule creation:
   - Interpret their intent and create appropriate loan risk assessment rules
   - Use sensible defaults based on banking best practices
   - Choose appropriate fields (missed_emis, days_overdue, pending_amount, etc.)
   - Set reasonable thresholds based on risk levels
   - Provide clear explanations of what the rule does and why it's important

**Available Tools & Data:**
- Customer search and account lookup
- Loan portfolio analysis
- Payment history tracking
- Risk level assessment
- Contract note analysis
- Collection performance metrics
- Escalation case management

When users ask about customers, loans, collections, or any banking-related queries, use your tools to provide comprehensive, data-backed insights and actionable recommendations."""
# --- END: FINAL, DEFINITIVE SYSTEM PROMPT ---


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(
        (httpx.ConnectError, httpx.TimeoutException, ConnectionError)
    ),
)
def generate_content_with_retry(client, model, contents, config, use_streaming=True):
    """Generate content with retry logic and fallback mechanism"""
    if use_streaming:
        try:
            response_text = ""
            function_call_detected = None

            for chunk in client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=config,
            ):
                if chunk.function_calls:
                    function_call_detected = chunk.function_calls[0]
                    break
                elif chunk.text:
                    response_text += chunk.text

            return response_text, function_call_detected
        except (httpx.ConnectError, httpx.TimeoutException, ConnectionError) as e:
            logger.warning(
                f"Streaming failed with {type(e).__name__}: {e}. Falling back to non-streaming."
            )
            # Fallback to non-streaming
            return generate_content_with_retry(
                client, model, contents, config, use_streaming=False
            )
    else:
        # Non-streaming fallback
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )

        response_text = ""
        function_call_detected = None

        if response.function_calls:
            function_call_detected = response.function_calls[0]
        elif response.text:
            response_text = response.text

        return response_text, function_call_detected


def create_tool_definitions():
    """Create tool definitions for Gemini function calling"""
    return [types.Tool(function_declarations=tools.ALL_TOOL_DECLARATIONS)]


def format_ui_response(
    text: str, action: str = "DISPLAY_TEXT", data: Any = None
) -> Dict[str, Any]:
    """Standardizes the response format for the frontend."""
    # Ensure data is JSON serializable before sending
    try:
        if data is not None:
            json.dumps(data, default=str)  # Test serialization
    except (TypeError, ValueError):
        data = str(data)  # Fallback to string representation

    return {"responseText": text, "uiAction": action, "data": data}


def invoke_agent(
    user_message: str,
    current_invoice_id: Optional[str] = None,
    history: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Invokes the Gemini API to respond to the user's message and optionally call tools."""
    db = SessionLocal()

    try:
        if not client:
            return format_ui_response(
                "I'm sorry, the AI service is not available at the moment. Please try again later."
            )

        # --- NEW LOGIC: Build conversation with system context ---
        conversation_contents = [
            types.Content(role="user", parts=[types.Part.from_text(text=SYSTEM_PROMPT)])
        ]
        conversation_contents.append(
            types.Content(
                role="model",
                parts=[types.Part.from_text(text="Understood. I am ready to assist.")],
            )
        )

        # Append previous turns from the history sent by the frontend
        if history:
            for entry in history:
                role = entry.get("role")
                text = entry.get("parts", [{}])[0].get("text", "")
                if role and text:
                    conversation_contents.append(
                        types.Content(
                            role=role, parts=[types.Part.from_text(text=text)]
                        )
                    )

        # Add the current user message with context
        current_user_message = f"User Request: '{user_message}'"
        if current_invoice_id:
            current_user_message += (
                f" (in the context of invoice: {current_invoice_id})"
            )
        conversation_contents.append(
            types.Content(
                role="user", parts=[types.Part.from_text(text=current_user_message)]
            )
        )
        # --- END NEW LOGIC ---

        gemini_tools = create_tool_definitions()

        # Configure for function calling using the standardized pattern
        generate_content_config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                thinking_budget=-1,
            ),
            safety_settings=[
                types.SafetySetting(
                    category="HARM_CATEGORY_HARASSMENT",
                    threshold="BLOCK_NONE",  # Block none
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_HATE_SPEECH",
                    threshold="BLOCK_NONE",  # Block none
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    threshold="BLOCK_NONE",  # Block none
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_DANGEROUS_CONTENT",
                    threshold="BLOCK_NONE",  # Block none
                ),
            ],
            tools=gemini_tools,
            response_mime_type="text/plain",
        )

        # Use robust content generation with retry logic
        try:
            response_text, function_call_detected = generate_content_with_retry(
                client=client,
                model=settings.gemini_model_name,
                contents=conversation_contents,
                config=generate_content_config,
            )
        except Exception as e:
            logger.error(f"Content generation failed after retries: {e}")
            return format_ui_response(
                "I'm experiencing connectivity issues. Please try again in a moment."
            )

        if function_call_detected:
            function_call = function_call_detected
            tool_name = function_call.name
            tool_args = dict(function_call.args) if function_call.args else {}

            if tool_name not in tools.AVAILABLE_TOOLS:
                return format_ui_response(
                    f"Error: The AI requested an unknown tool: {tool_name}"
                )

            print(f"🤖 Agent wants to call tool '{tool_name}' with args: {tool_args}")

            tool_function = tools.AVAILABLE_TOOLS[tool_name]
            tool_args["db"] = db
            if tool_name == "draft_vendor_communication":
                tool_args["client"] = client

            original_tool_result = tool_function(**tool_args)

            # Re-invoke the model with the tool's result to get a natural language summary
            # Add function call result back to conversation for model context
            conversation_contents.append(
                types.Content(
                    role="model",
                    parts=[
                        types.Part.from_text(
                            text=f"Called {tool_name} with args: {tool_args}"
                        )
                    ],
                )
            )
            conversation_contents.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(
                            text=f"Tool result: {json.dumps(original_tool_result, default=str)}"
                        )
                    ],
                )
            )

            # Configure for final response generation
            final_config = types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(
                    thinking_budget=0,
                ),
                safety_settings=[
                    types.SafetySetting(
                        category="HARM_CATEGORY_HARASSMENT",
                        threshold="BLOCK_NONE",  # Block none
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_HATE_SPEECH",
                        threshold="BLOCK_NONE",  # Block none
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        threshold="BLOCK_NONE",  # Block none
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_DANGEROUS_CONTENT",
                        threshold="BLOCK_NONE",  # Block none
                    ),
                ],
                response_mime_type="text/plain",
            )

            try:
                final_response_text, _ = generate_content_with_retry(
                    client=client,
                    model=settings.gemini_model_name,
                    contents=conversation_contents,
                    config=final_config,
                )
            except Exception as e:
                logger.error(f"Final response generation failed: {e}")
                final_response_text = "Action completed successfully, but I'm having trouble generating a summary."

            ui_action = "LOAD_DATA"
            if any(
                action in tool_name
                for action in [
                    "approve",
                    "reject",
                    "update",
                    "edit",
                    "create",
                    "regenerate",
                    "batch",
                ]
            ):
                ui_action = "SHOW_TOAST_SUCCESS"
            if tool_name == "get_invoice_details":
                ui_action = "LOAD_SINGLE_DOSSIER"
            elif tool_name == "draft_vendor_communication":
                ui_action = "DISPLAY_MARKDOWN"

            return format_ui_response(
                text=final_response_text, action=ui_action, data=original_tool_result
            )
        else:
            return format_ui_response(response_text)

    except Exception as e:
        logger.error(f"An error occurred in the AI Collection Manager agent: {e}")
        import traceback

        traceback.print_exc()
        return format_ui_response(
            "I'm sorry, a critical error occurred while processing your request."
        )
    finally:
        db.close()

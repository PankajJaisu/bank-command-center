# src/app/utils/email_service.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from app.utils.logging import get_logger
import os

logger = get_logger(__name__)

# Email templates for different policy actions
EMAIL_TEMPLATES = {
    "Send Legal Notice": {
        "subject": "Legal Notice - Immediate Action Required",
        "template": """
        <html>
        <body>
            <h2 style="color: #dc2626;">LEGAL NOTICE</h2>
            <p>Dear {customer_name},</p>
            
            <p>This is a formal legal notice regarding your overdue loan account <strong>{customer_no}</strong>.</p>
            
            <p><strong>Outstanding Details:</strong></p>
            <ul>
                <li>Pending Amount: ₹{pending_amount}</li>
                <li>EMIs Pending: {emi_pending}</li>
                <li>Days Overdue: {days_overdue}</li>
            </ul>
            
            <p style="color: #dc2626; font-weight: bold;">
                Immediate payment is required to avoid legal proceedings. Please contact us within 7 days.
            </p>
            
            <p>Contact: pankajjaiswal@supervity.ai | Phone: +91-XXXXXXXXXX</p>
            
            <p>Regards,<br>
            Supervity Collections Team</p>
        </body>
        </html>
        """
    },
    "Send Reminder": {
        "subject": "Payment Reminder - {customer_no}",
        "template": """
        <html>
        <body>
            <h2 style="color: #f59e0b;">Payment Reminder</h2>
            <p>Dear {customer_name},</p>
            
            <p>This is a friendly reminder about your pending loan payment for account <strong>{customer_no}</strong>.</p>
            
            <p><strong>Payment Details:</strong></p>
            <ul>
                <li>Pending Amount: ₹{pending_amount}</li>
                <li>EMIs Pending: {emi_pending}</li>
                <li>Next Due Date: {next_due_date}</li>
            </ul>
            
            <p>Please make the payment at your earliest convenience to avoid any late fees.</p>
            
            <p>Contact: pankajjaiswal@supervity.ai | Phone: +91-XXXXXXXXXX</p>
            
            <p>Thank you,<br>
            Supervity Collections Team</p>
        </body>
        </html>
        """
    },
    "Send Email": {
        "subject": "Account Update - {customer_no}",
        "template": """
        <html>
        <body>
            <h2 style="color: #3b82f6;">Account Update</h2>
            <p>Dear {customer_name},</p>
            
            <p>We wanted to update you on your loan account <strong>{customer_no}</strong>.</p>
            
            <p><strong>Account Status:</strong></p>
            <ul>
                <li>Current Balance: ₹{pending_amount}</li>
                <li>EMIs Pending: {emi_pending}</li>
                <li>Account Status: Under Review</li>
            </ul>
            
            <p>If you have any questions, please don't hesitate to contact us.</p>
            
            <p>Contact: pankajjaiswal@supervity.ai | Phone: +91-XXXXXXXXXX</p>
            
            <p>Best regards,<br>
            Supervity Collections Team</p>
        </body>
        </html>
        """
    },
    "Make Phone Call": {
        "subject": "Follow-up Required - {customer_no}",
        "template": """
        <html>
        <body>
            <h2 style="color: #8b5cf6;">Follow-up Notification</h2>
            <p>Dear {customer_name},</p>
            
            <p>Our team will be contacting you shortly regarding your loan account <strong>{customer_no}</strong>.</p>
            
            <p><strong>Contact Reason:</strong></p>
            <ul>
                <li>Pending Amount: ₹{pending_amount}</li>
                <li>EMIs Pending: {emi_pending}</li>
                <li>Scheduled Call: Within 24 hours</li>
            </ul>
            
            <p>Please ensure you're available to discuss your account status.</p>
            
            <p>Contact: pankajjaiswal@supervity.ai | Phone: +91-XXXXXXXXXX</p>
            
            <p>Regards,<br>
            Supervity Collections Team</p>
        </body>
        </html>
        """
    }
}

# Email configuration for policy agent
POLICY_EMAIL_CONFIG = {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "username": "pankajfs19if009@gmail.com",
    "password": "dfxz ytxt qatu lbtz",
    "from_email": "pankajfs19if009@gmail.com"
}


def generate_policy_email(action: str, customer_data: dict) -> tuple[str, str]:
    """
    Generate email subject and body based on action type and customer data.
    """
    template_data = EMAIL_TEMPLATES.get(action)
    if not template_data:
        # Default template for unknown actions
        template_data = EMAIL_TEMPLATES["Send Email"]
    
    # Prepare customer data with defaults
    email_data = {
        "customer_name": customer_data.get("name", "Valued Customer"),
        "customer_no": customer_data.get("customer_no", "N/A"),
        "pending_amount": f"{customer_data.get('pending_amount', 0):,.2f}",
        "emi_pending": customer_data.get("emi_pending", 0),
        "days_overdue": customer_data.get("days_overdue", 0),
        "next_due_date": customer_data.get("next_due_date", "TBD")
    }
    
    # Format subject and body
    subject = template_data["subject"].format(**email_data)
    body = template_data["template"].format(**email_data)
    
    return subject, body


async def send_policy_email(to_email: str, subject: str, body: str, customer_name: str = "Customer") -> dict:
    """
    Sends a policy-related email notification using the configured SMTP settings.
    """
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = POLICY_EMAIL_CONFIG["from_email"]
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add body to email
        msg.attach(MIMEText(body, 'html'))
        
        # Create SMTP session
        server = smtplib.SMTP(POLICY_EMAIL_CONFIG["smtp_server"], POLICY_EMAIL_CONFIG["smtp_port"])
        server.starttls()  # Enable security
        server.login(POLICY_EMAIL_CONFIG["username"], POLICY_EMAIL_CONFIG["password"])
        
        # Send email
        text = msg.as_string()
        server.sendmail(POLICY_EMAIL_CONFIG["from_email"], to_email, text)
        server.quit()
        
        logger.info(f"✅ Policy email sent successfully to {to_email}")
        logger.info(f"📧 Subject: {subject}")
        logger.info(f"👤 Customer: {customer_name}")
        
        return {"success": True, "message": "Email sent successfully"}
        
    except Exception as e:
        logger.error(f"❌ Failed to send policy email to {to_email}: {str(e)}")
        return {"success": False, "error": str(e)}


async def send_email_notification(subject: str, recipients: List[str], body: str):
    """
    Legacy email notification function (kept for compatibility)
    """
    logger.info("--- EMAIL NOTIFICATION ---")
    logger.info(f"To: {recipients}")
    logger.info(f"Subject: {subject}")
    logger.debug(f"Body: {body}")
    logger.info("-------------------------")
    return {"message": "Email notification logged"}

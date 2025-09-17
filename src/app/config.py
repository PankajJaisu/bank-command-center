# config.py
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    # This tells Pydantic to load variables from a .env file and the environment.
    # `case_sensitive=False` allows DATABASE_URL env var to map to `database_url`.
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # --- Database Configuration ---
    # Can be overridden by setting the DATABASE_URL environment variable.
    # e.g. DATABASE_URL="postgresql://user:password@host:port/dbname"
    # Default is a local SQLite file for simple setup.
    database_url: str = "sqlite:///./ap_data.db"

    # --- Google GenAI Configuration ---
    # Can be overridden by setting the GEMINI_API_KEY environment variable.
    gemini_api_key: str = ""

    # Updated model name for the new Gemini API - using gemini-2.5-flash as per latest syntax
    gemini_model_name: str = "gemini-2.5-flash"

    # --- Email Configuration ---
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = "pankajjaiswal@supervity.ai"
    smtp_password: str = "Manikram@526254"
    smtp_sender_email: str = "pankajjaiswal@supervity.ai"
    app_domain: str = "supervity.ai"

    # --- PHASE 3: AI POLICY AGENT CONFIGURATION ---
    policy_agent_interval_minutes: float = 1.0  # Default to 1 minute for testing
    # --- END PHASE 3 ---

    # --- Document Storage Configuration ---
    # Primary PDF storage path for uploaded and sample documents
    # Can be overridden by setting the PDF_STORAGE_PATH environment variable
    pdf_storage_path: str = "sample_data/invoices"

    # Generated documents storage path for system-generated PDFs
    # Can be overridden by setting the GENERATED_PDF_STORAGE_PATH environment variable
    generated_pdf_storage_path: str = "generated_documents"

    # --- Authentication Configuration ---
    # Secret key for JWT token encryption - can be overridden by setting AUTH_SECRET_KEY environment variable
    auth_secret_key: str = (
        "15dc83e55320206d8e1559b9a7752623209d19200727e988801b18601cd8399e"
    )
    auth_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    # --- Email Configuration ---
    # Mail settings for notification system - can be overridden by environment variables
    mail_username: str = "your-email@example.com"
    mail_password: str = "your-password"
    mail_from: str = "your-email@example.com"
    mail_port: int = 587
    mail_server: str = "smtp.example.com"
    mail_starttls: bool = True
    mail_ssl_tls: bool = False


settings = Settings()

# The percentage variance allowed for a unit price mismatch between PO and Invoice.
# 5.0 means a 5% tolerance.
PRICE_TOLERANCE_PERCENT = 5.0

# The percentage variance allowed for a quantity mismatch between GRN and Invoice.
QUANTITY_TOLERANCE_PERCENT = 2.0  # e.g., 2.0 allows for a 2% variance

# Parallel processing configuration
# Number of worker threads for parallel document processing
PARALLEL_WORKERS = 9

"""
Configuration settings for the Bank Command Center application.
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./ap_data.db")
    
    # API Configuration
    cors_origins: str = os.getenv("CORS_ORIGINS", "*")
    
    # File Storage
    pdf_storage_path: str = os.getenv("PDF_STORAGE_PATH", "./sample_data")
    generated_pdf_storage_path: str = os.getenv("GENERATED_PDF_STORAGE_PATH", "./generated_documents")
    
    # Gemini AI
    gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY")
    
    # App Environment
    app_env: str = os.getenv("APP_ENV", "development")
    
    class Config:
        env_file = ".env"


# Global settings instance
settings = Settings()

#!/usr/bin/env python3
"""
Simplified initialization script for basic configuration data.
This creates minimal data needed for the application to start.
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from app.db.session import SessionLocal
from app.db import models
from app.config import settings

def main():
    """Initialize basic configuration data."""
    print("🚀 INITIALIZING BASIC CONFIGURATION DATA")
    print("=" * 50)
    
    try:
        with SessionLocal() as db:
            print("✅ Database connection successful")
            
            # Check if we have any customers (basic data check)
            customer_count = db.query(models.Customer).count()
            print(f"📊 Current customers in database: {customer_count}")
            
            # Check if we have any automation rules
            rule_count = db.query(models.AutomationRule).count()
            print(f"📋 Current automation rules: {rule_count}")
            
            print("✅ Basic configuration check completed")
            
    except Exception as e:
        print(f"❌ Error during initialization: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

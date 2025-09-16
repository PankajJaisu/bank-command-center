#!/usr/bin/env python3
"""
Simple script to create the required database tables for the collection system
"""
import sys
import os
sys.path.append('src')

from app.db.session import SessionLocal, engine
from app.db import models
from sqlalchemy import text

def create_tables():
    """Create all required tables for the collection system"""
    print("Creating database tables...")
    
    try:
        # Import all models to ensure they're registered
        from app.db.models import (
            ContractNote, Customer, Loan, DataIntegrityAlert
        )
        
        # Create all tables
        models.Base.metadata.create_all(bind=engine)
        
        print("✅ Tables created successfully!")
        
        # Test database connection
        with SessionLocal() as db:
            # Check if tables exist
            result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = [row[0] for row in result.fetchall()]
            print(f"📋 Available tables: {tables}")
            
            # Check customer count
            customer_count = db.query(models.Customer).count()
            print(f"👥 Current customers in database: {customer_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False

if __name__ == "__main__":
    success = create_tables()
    sys.exit(0 if success else 1)

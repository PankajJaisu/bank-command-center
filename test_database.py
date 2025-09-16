#!/usr/bin/env python3
"""
Test script to check database connectivity and customer data
"""
import sys
import os
sys.path.append('src')

from app.db.session import SessionLocal
from app.db import models
from sqlalchemy import text

def test_database():
    """Test database connectivity and check for customer data"""
    print("Testing database connectivity...")
    
    try:
        with SessionLocal() as db:
            # Check if tables exist (PostgreSQL version)
            result = db.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            tables = [row[0] for row in result.fetchall()]
            print(f"📋 Available tables: {tables}")
            
            # Check customer count
            customer_count = db.query(models.Customer).count()
            print(f"👥 Current customers in database: {customer_count}")
            
            if customer_count > 0:
                # Show sample customers
                customers = db.query(models.Customer).limit(5).all()
                print("\n📊 Sample customers:")
                for customer in customers:
                    print(f"  {customer.customer_no}: {customer.name} (Risk: {customer.cbs_risk_level})")
            
            # Check loan count
            loan_count = db.query(models.Loan).count()
            print(f"💰 Current loans in database: {loan_count}")
            
            # Check contract notes count
            contract_count = db.query(models.ContractNote).count()
            print(f"📄 Current contract notes in database: {contract_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database test error: {e}")
        return False

if __name__ == "__main__":
    success = test_database()
    sys.exit(0 if success else 1)

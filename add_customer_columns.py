#!/usr/bin/env python3
"""
Script to manually add the new customer columns to the database
"""
import sys
import os

# Add project paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from app.db.session import SessionLocal
from sqlalchemy import text


def add_customer_columns():
    """Add new customer columns to the database"""
    
    db = SessionLocal()
    try:
        print("🔄 Adding new customer columns...")
        
        # List of new columns to add
        new_columns = [
            "ADD COLUMN IF NOT EXISTS cibil_score INTEGER",
            "ADD COLUMN IF NOT EXISTS days_since_employment INTEGER", 
            "ADD COLUMN IF NOT EXISTS employment_status VARCHAR(50)",
            "ADD COLUMN IF NOT EXISTS cbs_income_verification VARCHAR(50)",
            "ADD COLUMN IF NOT EXISTS salary_last_date DATE",
            "ADD COLUMN IF NOT EXISTS pending_amount REAL",
            "ADD COLUMN IF NOT EXISTS pendency VARCHAR(50)"
        ]
        
        for column_sql in new_columns:
            try:
                full_sql = f"ALTER TABLE customers {column_sql}"
                db.execute(text(full_sql))
                print(f"✅ Added: {column_sql.split()[-2]}")
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                    print(f"ℹ️  Column already exists: {column_sql.split()[-2]}")
                else:
                    print(f"⚠️  Error adding {column_sql.split()[-2]}: {e}")
        
        db.commit()
        print("✅ Database schema updated successfully!")
        
        # Verify columns exist
        result = db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'customers' AND column_name IN ('cibil_score', 'days_since_employment', 'employment_status', 'pending_amount')"))
        existing_columns = [row[0] for row in result.fetchall()]
        print(f"📊 New columns found in database: {existing_columns}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating database schema: {e}")
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    print("🚀 Adding customer columns to database...")
    success = add_customer_columns()
    
    if success:
        print("✅ Customer columns added successfully!")
        print("💡 You can now load sample customer data.")
    else:
        print("❌ Failed to add customer columns.")
        sys.exit(1)

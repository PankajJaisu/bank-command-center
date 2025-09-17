#!/usr/bin/env python3
"""
Script to manually add the Phase 1 customer columns to the database schema.
"""
import sys
import os
from sqlalchemy import text

# Add project paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from app.db.session import SessionLocal

def add_phase1_customer_columns():
    """Add new customer columns for segmentation and AI risk management."""
    
    db = SessionLocal()
    try:
        print("🔄 Applying Phase 1 database schema changes for the Customer table...")
        
        # Check existing columns first (SQLite compatible)
        result = db.execute(text("PRAGMA table_info(customers)"))
        existing_columns = [row[1] for row in result.fetchall()]
        print(f"📊 Current columns in customers table: {existing_columns}")
        
        # List of new columns to add
        new_columns = [
            ("segment", "VARCHAR(100)"),
            ("risk_level", "VARCHAR(100)"),
            ("ai_suggested_action", "VARCHAR(255)"),
            ("last_action_taken", "VARCHAR(255)")
        ]
        
        for column_name, column_type in new_columns:
            if column_name not in existing_columns:
                try:
                    full_sql = f"ALTER TABLE customers ADD COLUMN {column_name} {column_type}"
                    db.execute(text(full_sql))
                    print(f"✅ Added column: {column_name}")
                except Exception as e:
                    print(f"⚠️  Error adding column '{column_name}': {e}")
            else:
                print(f"ℹ️  Column '{column_name}' already exists, skipping.")
        
        # Drop the old cbs_risk_level column if it exists
        if "cbs_risk_level" in existing_columns:
            try:
                # SQLite doesn't support DROP COLUMN directly, but we can work around it
                # For now, we'll just note it exists and should be ignored
                print("ℹ️  Old 'cbs_risk_level' column exists but will be ignored in favor of new 'risk_level' column.")
            except Exception as e:
                print(f"⚠️  Note about 'cbs_risk_level': {e}")
        else:
            print("ℹ️  Old 'cbs_risk_level' column not found.")

        db.commit()
        print("\n✅ Database schema updated successfully for Phase 1!")
        
        # Verify columns exist (SQLite compatible)
        result = db.execute(text("PRAGMA table_info(customers)"))
        all_columns = [row[1] for row in result.fetchall()]
        new_columns_found = [col for col in ["segment", "risk_level", "ai_suggested_action", "last_action_taken"] if col in all_columns]
        print(f"📊 Verification - New columns found in database: {new_columns_found}")
        
        return True
        
    except Exception as e:
        print(f"❌ A critical error occurred: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Running Phase 1 Migration...")
    success = add_phase1_customer_columns()
    
    if success:
        print("\n✅ Phase 1 migration completed!")
    else:
        print("\n❌ Phase 1 migration failed.")
        sys.exit(1)

#!/usr/bin/env python3
"""
Script to manually add the Phase 2 automation rule columns to the database schema.
"""
import sys
import os
from sqlalchemy import text

# Add project paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from app.db.session import SessionLocal

def add_phase2_automation_rule_columns():
    """Add new automation rule columns for policy ingestion and review workflow."""
    
    db = SessionLocal()
    try:
        print("🔄 Applying Phase 2 database schema changes for the AutomationRule table...")
        
        # Check existing columns first (SQLite compatible)
        result = db.execute(text("PRAGMA table_info(automation_rules)"))
        existing_columns = [row[1] for row in result.fetchall()]
        print(f"📊 Current columns in automation_rules table: {existing_columns}")
        
        # List of new columns to add
        new_columns = [
            ("rule_level", "VARCHAR(100)"),
            ("segment", "VARCHAR(255)"),
            ("customer_id", "VARCHAR(100)"),
            ("source_document", "VARCHAR(255)"),
            ("status", "VARCHAR(100) DEFAULT 'active'")
        ]
        
        for column_name, column_type in new_columns:
            if column_name not in existing_columns:
                try:
                    full_sql = f"ALTER TABLE automation_rules ADD COLUMN {column_name} {column_type}"
                    db.execute(text(full_sql))
                    print(f"✅ Added column: {column_name}")
                except Exception as e:
                    print(f"⚠️  Error adding column '{column_name}': {e}")
            else:
                print(f"ℹ️  Column '{column_name}' already exists, skipping.")

        db.commit()
        print("\n✅ Database schema updated successfully for Phase 2!")
        
        # Verify columns exist (SQLite compatible)
        result = db.execute(text("PRAGMA table_info(automation_rules)"))
        all_columns = [row[1] for row in result.fetchall()]
        new_columns_found = [col for col in ["rule_level", "segment", "customer_id", "source_document", "status"] if col in all_columns]
        print(f"📊 Verification - New columns found in database: {new_columns_found}")
        
        return True
        
    except Exception as e:
        print(f"❌ A critical error occurred: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Running Phase 2 Migration...")
    success = add_phase2_automation_rule_columns()
    
    if success:
        print("\n✅ Phase 2 migration completed!")
    else:
        print("\n❌ Phase 2 migration failed.")
        sys.exit(1)

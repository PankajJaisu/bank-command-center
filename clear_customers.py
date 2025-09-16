#!/usr/bin/env python3
"""
Script to clear all customer data from the database.
This includes customers, loans, contract notes, and data integrity alerts.
"""

import os
import sys
from sqlalchemy import text

# Add both the project root and src directory to the Python path
project_root = os.path.abspath(os.path.dirname(__file__))
src_dir = os.path.join(project_root, "src")
sys.path.insert(0, project_root)
sys.path.insert(0, src_dir)

from app.db.session import SessionLocal
from app.db import models


def clear_customer_data():
    """Remove all customer-related data from the database."""
    print("🧹 Clearing all customer data...")

    db = SessionLocal()
    try:
        # Delete customer-related data in correct order (respecting foreign keys)
        print("Deleting customer-related data...")

        # Order is important: delete from most dependent tables first
        customer_tables = [
            "data_integrity_alerts",  # References customers
            "loans",                  # References customers
            "contract_notes",         # Referenced by customers
            "customers"               # Main customer table
        ]

        deleted_counts = {}
        
        for table in customer_tables:
            try:
                # Get count before deletion
                count_result = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                
                # Delete all records
                result = db.execute(text(f"DELETE FROM {table}"))
                deleted_counts[table] = count_result
                print(f"✅ Deleted {count_result} records from {table}")
            except Exception as e:
                print(f"⚠️ Could not clear table {table}: {e}")

        db.commit()
        print("✅ Customer data cleared successfully!")

        # Show final counts
        try:
            customer_count = db.query(models.Customer).count()
            loan_count = db.query(models.Loan).count()
            contract_note_count = db.query(models.ContractNote).count()
            alert_count = db.query(models.DataIntegrityAlert).count()

            print(f"📊 Current counts after cleanup:")
            print(f"   • Customers: {customer_count}")
            print(f"   • Loans: {loan_count}")
            print(f"   • Contract Notes: {contract_note_count}")
            print(f"   • Data Integrity Alerts: {alert_count}")

            total_deleted = sum(deleted_counts.values())
            print(f"🗑️ Total records deleted: {total_deleted}")

        except Exception as e:
            print(f"⚠️ Could not get final counts: {e}")

    except Exception as e:
        print(f"❌ Error clearing customer data: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def reset_auto_increment():
    """Reset auto-increment counters for customer tables."""
    print("🔄 Resetting auto-increment counters...")
    
    db = SessionLocal()
    try:
        # Reset auto-increment for customer tables
        reset_commands = [
            "ALTER TABLE customers AUTO_INCREMENT = 1",
            "ALTER TABLE loans AUTO_INCREMENT = 1", 
            "ALTER TABLE contract_notes AUTO_INCREMENT = 1",
            "ALTER TABLE data_integrity_alerts AUTO_INCREMENT = 1"
        ]
        
        for command in reset_commands:
            try:
                db.execute(text(command))
                print(f"✅ Reset auto-increment for {command.split()[2]}")
            except Exception as e:
                print(f"⚠️ Could not reset auto-increment: {e}")
        
        db.commit()
        print("✅ Auto-increment counters reset!")
        
    except Exception as e:
        print(f"❌ Error resetting auto-increment: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("🚀 Starting customer data cleanup...")
    clear_customer_data()
    
    # Ask if user wants to reset auto-increment counters
    response = input("\n🔄 Do you want to reset auto-increment counters? (y/N): ").strip().lower()
    if response in ['y', 'yes']:
        reset_auto_increment()
    
    print("\n✅ Customer data cleanup completed!")
    print("🔄 The dashboard and collection cell will now show empty/default data.")
    print("💡 Use 'Sync Sample Data' in the Data Center to import new customer data.")

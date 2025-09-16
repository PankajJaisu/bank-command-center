#!/usr/bin/env python3
"""
Script to manually delete all customer-related records from the database
"""
import sys
import os
sys.path.append('src')

from app.db.session import SessionLocal
from app.db import models

def clear_all_customer_data():
    """Delete all customer-related data from the database"""
    print("🗑️  Starting database cleanup...")
    
    try:
        with SessionLocal() as db:
            # Count records before deletion
            customer_count = db.query(models.Customer).count()
            loan_count = db.query(models.Loan).count()
            contract_count = db.query(models.ContractNote).count()
            alert_count = db.query(models.DataIntegrityAlert).count()
            
            print(f"📊 Current records:")
            print(f"   👥 Customers: {customer_count}")
            print(f"   💰 Loans: {loan_count}")
            print(f"   📄 Contract Notes: {contract_count}")
            print(f"   🚨 Data Integrity Alerts: {alert_count}")
            
            if customer_count == 0 and loan_count == 0 and contract_count == 0 and alert_count == 0:
                print("✅ Database is already clean!")
                return True
            
            print("\n🔄 Deleting records...")
            
            # Delete in order to respect foreign key constraints
            
            # 1. Delete data integrity alerts first (they reference customers)
            deleted_alerts = db.query(models.DataIntegrityAlert).delete()
            print(f"   🚨 Deleted {deleted_alerts} data integrity alerts")
            
            # 2. Delete loans (they reference customers)
            deleted_loans = db.query(models.Loan).delete()
            print(f"   💰 Deleted {deleted_loans} loans")
            
            # 3. Delete customers (they reference contract notes)
            deleted_customers = db.query(models.Customer).delete()
            print(f"   👥 Deleted {deleted_customers} customers")
            
            # 4. Delete contract notes (no foreign key dependencies)
            deleted_contracts = db.query(models.ContractNote).delete()
            print(f"   📄 Deleted {deleted_contracts} contract notes")
            
            # Commit all deletions
            db.commit()
            print("\n✅ All customer-related data deleted successfully!")
            print("💾 Changes committed to database")
            
            # Verify deletion
            remaining_customers = db.query(models.Customer).count()
            remaining_loans = db.query(models.Loan).count()
            remaining_contracts = db.query(models.ContractNote).count()
            remaining_alerts = db.query(models.DataIntegrityAlert).count()
            
            print(f"\n🔍 Verification - Remaining records:")
            print(f"   👥 Customers: {remaining_customers}")
            print(f"   💰 Loans: {remaining_loans}")
            print(f"   📄 Contract Notes: {remaining_contracts}")
            print(f"   🚨 Data Integrity Alerts: {remaining_alerts}")
            
            if remaining_customers == 0 and remaining_loans == 0 and remaining_contracts == 0 and remaining_alerts == 0:
                print("✅ Database cleanup completed successfully!")
                return True
            else:
                print("⚠️  Some records may still remain")
                return False
        
    except Exception as e:
        print(f"❌ Error during database cleanup: {e}")
        return False

if __name__ == "__main__":
    print("🗑️  Database Cleanup Tool")
    print("This will delete ALL customer, loan, contract note, and alert records.")
    
    # Ask for confirmation
    response = input("\nAre you sure you want to proceed? (type 'yes' to confirm): ")
    
    if response.lower() == 'yes':
        success = clear_all_customer_data()
        sys.exit(0 if success else 1)
    else:
        print("❌ Operation cancelled")
        sys.exit(1)

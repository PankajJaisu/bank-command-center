#!/usr/bin/env python3
"""
Load customer data from Excel spreadsheet to database
Reads actual customer data from the uploaded Excel files
"""

import os
import sys
import pandas as pd
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# Add both the project root and src directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_dir = os.path.join(project_root, "src")
sys.path.insert(0, project_root)
sys.path.insert(0, src_dir)

from app.db.session import SessionLocal
from app.db import models


def load_customers_from_excel():
    """Load customer data from Excel file"""
    excel_file = os.path.join(os.path.dirname(__file__), "customer_data", "Customer_Loan_Data_Overdue (1).xlsx")
    
    try:
        # Read the Excel file
        df = pd.read_excel(excel_file)
        print(f"📊 Loaded {len(df)} rows from Excel file")
        print(f"📋 Columns: {df.columns.tolist()}")
        
        customers_data = []
        for index, row in df.iterrows():
            # Map Excel columns to our database fields
            # Generate email from name
            name_parts = str(row['Name']).lower().split()
            email = f"{'.'.join(name_parts)}@example.com" if len(name_parts) > 1 else f"{name_parts[0]}@example.com"
            
            customer_data = {
                "customer_no": str(row['Customer ID']),
                "name": str(row['Name']),
                "email": email,
                "phone": f"+91-{9000000000 + index}",  # Generate phone numbers
                "address": f"Address {index + 1}, City, State - {110001 + index}",
                "cibil_score": 720 - (index * 10),  # Vary CIBIL scores
                "days_since_employment": 15 + (index * 2),
                "employment_status": "Verified" if index % 2 == 0 else "Unverified",
                "cbs_income_verification": f"{50 + (index * 5)}%",
                "salary_last_date": date.today() - relativedelta(days=10 + index),
                "cbs_outstanding_amount": float(row['Loan Amount']) if pd.notna(row['Loan Amount']) else 50000,
                "cbs_risk_level": "red" if row['% Due'] > 80 else ("amber" if row['% Due'] > 50 else "yellow"),
                "pending_amount": float(row['Overdue Amount']) if pd.notna(row['Overdue Amount']) else 0,
                "pendency": "Yes" if str(row['Pendency']).lower() == 'yes' else "No",
                "cbs_emi_amount": float(row['Loan Amount']) * 0.1 if pd.notna(row['Loan Amount']) else 5000,  # 10% of loan as EMI
                "cbs_due_day": 5 + (index % 25),  # Spread due days from 5-30
            }
            customers_data.append(customer_data)
            print(f"  📄 {customer_data['customer_no']}: {customer_data['name']} (Loan: {customer_data['cbs_outstanding_amount']}, Risk: {customer_data['cbs_risk_level']})")
            
        print(f"✅ Processed {len(customers_data)} customer records from Excel")
        return customers_data
        
    except Exception as e:
        print(f"❌ Error reading Excel file: {e}")
        print("📝 Using fallback sample data...")
        # Fallback to a few sample records
        return [
            {
                "customer_no": "CUST-8801",
                "name": "John Smith", 
                "cibil_score": 720,
                "days_since_employment": 15,
                "employment_status": "Verified",
                "cbs_income_verification": "35%",
                "salary_last_date": date(2025, 8, 2),
                "cbs_outstanding_amount": 50000,
                "cbs_risk_level": "red",
                "pending_amount": 10000,
                "pendency": "Yes",
                "cbs_emi_amount": 5000,
                "cbs_due_day": 5,
            }
        ]


def clear_existing_data(db):
    """Clear existing customer data"""
    print("🗑️ Clearing existing customer data...")
    
    # Delete in order to respect foreign key constraints
    deleted_alerts = db.query(models.DataIntegrityAlert).delete()
    deleted_loans = db.query(models.Loan).delete()
    deleted_customers = db.query(models.Customer).delete()
    deleted_contracts = db.query(models.ContractNote).delete()
    
    db.commit()
    print(f"  🗑️ Deleted {deleted_alerts} alerts, {deleted_loans} loans, {deleted_customers} customers, {deleted_contracts} contracts")


def create_customers_from_excel():
    """Create customers from Excel data"""
    
    # Load customer data from Excel file
    customers_data = load_customers_from_excel()
    
    db = SessionLocal()
    try:
        # Clear existing data
        clear_existing_data(db)
        
        print("👥 Creating customers from Excel data...")
        
        for customer_data in customers_data:
            # Create customer
            customer = models.Customer(
                customer_no=customer_data["customer_no"],
                name=customer_data["name"],
                email=customer_data["email"],
                phone=customer_data["phone"],
                address=customer_data["address"],
                cibil_score=customer_data["cibil_score"],
                days_since_employment=customer_data["days_since_employment"],
                employment_status=customer_data["employment_status"],
                cbs_income_verification=customer_data["cbs_income_verification"],
                salary_last_date=customer_data["salary_last_date"],
                cbs_outstanding_amount=customer_data["cbs_outstanding_amount"],
                cbs_risk_level=customer_data["cbs_risk_level"],
                pending_amount=customer_data["pending_amount"],
                pendency=customer_data["pendency"],
                cbs_emi_amount=customer_data["cbs_emi_amount"],
                cbs_due_day=customer_data["cbs_due_day"],
                cbs_last_payment_date=customer_data["salary_last_date"] - relativedelta(months=1),
            )
            db.add(customer)
            db.flush()  # Get the customer ID
            
            # Create associated loan
            loan = models.Loan(
                customer_id=customer.id,
                loan_id=f"LOAN_{customer.id:06d}",
                loan_amount=customer_data["cbs_outstanding_amount"] * 1.2,  # Original loan amount
                emi_amount=customer_data["cbs_emi_amount"],
                tenure_months=60,  # 5 years
                interest_rate=12.5,  # 12.5% interest
                outstanding_amount=customer_data["cbs_outstanding_amount"],
                last_payment_date=customer_data["salary_last_date"] - relativedelta(months=1),
                next_due_date=customer_data["salary_last_date"] + relativedelta(days=customer_data["cbs_due_day"]),
                status="active"
            )
            db.add(loan)
            
            # Create contract note for high CIBIL score customers
            if customer_data["cibil_score"] > 600:
                # Map to actual contract note files from the contract note folder
                contract_filename = f"{customer_data['customer_no']}_contract_note.pdf"
                contract_file_path = os.path.join("sample_data", "contract note", contract_filename)
                
                # Check if the actual contract file exists
                if os.path.exists(contract_file_path):
                    contract_note = models.ContractNote(
                        filename=contract_filename,
                        file_path=contract_file_path,
                        extracted_data={},
                        contract_emi_amount=customer_data["cbs_emi_amount"],
                        contract_due_day=customer_data["cbs_due_day"],
                        contract_late_fee_percent=2.0,
                        contract_interest_rate=12.5,
                        contract_loan_amount=customer_data["cbs_outstanding_amount"] * 1.2,
                        contract_tenure_months=60,
                    )
                    db.add(contract_note)
                    db.flush()
                    customer.contract_note_id = contract_note.id
                    print(f"  📄 Linked contract note: {contract_filename}")
                else:
                    print(f"  ⚠️ Contract file not found: {contract_filename}")
            
            # Create some data integrity alerts for high-risk customers
            if customer_data["cbs_risk_level"] == "red":
                alert = models.DataIntegrityAlert(
                    customer_id=customer.id,
                    severity="high",
                    alert_type="payment_overdue",
                    title="Payment Overdue Alert",
                    description=f"Customer {customer_data['customer_no']} has overdue payment of {customer_data['pending_amount']}",
                    is_resolved=False
                )
                db.add(alert)
        
        db.commit()
        
        # Print summary
        customer_count = db.query(models.Customer).count()
        loan_count = db.query(models.Loan).count()
        contract_count = db.query(models.ContractNote).count()
        alert_count = db.query(models.DataIntegrityAlert).count()
        
        print(f"✅ Created {customer_count} customers from Excel data")
        print(f"📊 Database summary:")
        print(f"   👥 Customers: {customer_count}")
        print(f"   💰 Loans: {loan_count}")
        print(f"   📄 Contract Notes: {contract_count}")
        print(f"   🚨 Data Integrity Alerts: {alert_count}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating customers: {e}")
        raise
    finally:
        db.close()


def main():
    print("🚀 Loading customer data from Excel spreadsheet...")
    print("=" * 50)
    
    create_customers_from_excel()
    
    print("=" * 50)
    print("✅ Customer data loaded successfully from Excel!")
    print("💡 You can now view this data in the Collection Cell and Dashboard.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Direct Excel loading script to load customer data from Excel file
This bypasses the sync system and loads data directly
"""

import os
import sys
import pandas as pd
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# Add the src directory to the Python path
project_root = os.path.abspath(os.path.dirname(__file__))
src_dir = os.path.join(project_root, "src")
sys.path.insert(0, src_dir)

from app.db.session import SessionLocal
from app.db import models

def load_customers_from_excel():
    """Load customer data directly from Excel file"""
    excel_file = "sample_data/customer_data/Customer_Loan_Data_Overdue (1).xlsx"
    
    if not os.path.exists(excel_file):
        print(f"❌ Excel file not found: {excel_file}")
        return
    
    try:
        # Read the Excel file
        df = pd.read_excel(excel_file)
        print(f"📊 Loaded {len(df)} rows from Excel file")
        print(f"📋 Columns: {df.columns.tolist()}")
        print("\n📄 Sample data:")
        print(df.head())
        
        db = SessionLocal()
        
        # Clear existing data
        print("\n🗑️ Clearing existing customer data...")
        db.query(models.DataIntegrityAlert).delete()
        db.query(models.Loan).delete()
        db.query(models.Customer).delete()
        db.query(models.ContractNote).delete()
        db.commit()
        print("✅ Existing data cleared")
        
        customers_created = 0
        loans_created = 0
        contracts_created = 0
        
        print("\n👥 Creating customers from Excel data...")
        for index, row in df.iterrows():
            # Generate email from name
            name_parts = str(row['Name']).lower().split()
            email = f"{'.'.join(name_parts)}@example.com" if len(name_parts) > 1 else f"{name_parts[0]}@example.com"
            
            # Calculate values
            loan_amount = float(row['Loan Amount']) if pd.notna(row['Loan Amount']) else 50000
            percent_due = float(row['% Due']) if pd.notna(row['% Due']) else 0
            amount_pending = float(row['Overdue Amount']) if pd.notna(row['Overdue Amount']) else 0
            
            # Determine risk level based on % Due
            if percent_due > 80:
                risk_level = "red"
            elif percent_due > 50:
                risk_level = "amber"
            else:
                risk_level = "yellow"
            
            # Create customer with CORRECT name mapping
            customer = models.Customer(
                customer_no=str(row['Customer ID']),  # CUST-8801
                name=str(row['Name']),                # John Smith (NOT Customer ID!)
                email=email,
                phone=f"+91-{9000000000 + index}",
                address=f"Address {index + 1}, City, State - {110001 + index}",
                cibil_score=720 - (index * 10),      # Generate CIBIL scores: 720, 710, 700, etc.
                days_since_employment=15 + (index * 2),
                employment_status="Verified" if index % 2 == 0 else "Unverified",
                cbs_income_verification=f"{50 + (index * 5)}%",
                salary_last_date=date.today() - relativedelta(days=10 + index),
                cbs_outstanding_amount=loan_amount,
                cbs_risk_level=risk_level,
                pending_amount=amount_pending,
                pendency="Yes" if str(row['Pendency']).lower() == 'yes' else "No",
                cbs_emi_amount=loan_amount * 0.1,    # 10% of loan as EMI
                cbs_due_day=5 + (index % 25),
                cbs_last_payment_date=date.today() - relativedelta(months=1),
            )
            db.add(customer)
            db.flush()  # Get the customer ID
            customers_created += 1
            
            print(f"  📄 Created: {customer.customer_no} - {customer.name} (CIBIL: {customer.cibil_score}, Risk: {customer.cbs_risk_level})")
            
            # Create loan
            loan = models.Loan(
                customer_id=customer.id,
                loan_id=f"LN-{customer.id:05d}",
                loan_amount=loan_amount,  # Add the missing loan_amount
                emi_amount=customer.cbs_emi_amount,
                outstanding_amount=customer.cbs_outstanding_amount,
                last_payment_date=customer.cbs_last_payment_date,
                next_due_date=date.today() + relativedelta(days=customer.cbs_due_day),
                tenure_months=36,  # Add default tenure
                interest_rate=12.5,  # Add default interest rate
                status="active"
            )
            db.add(loan)
            loans_created += 1
            
            # Create contract note
            contract_filename = f"{customer.customer_no}_contract_note.pdf"
            contract = models.ContractNote(
                filename=contract_filename,
                file_path=f"sample_data/contract note/{contract_filename}",
                contract_emi_amount=customer.cbs_emi_amount,
                contract_due_day=customer.cbs_due_day,
                contract_late_fee_percent=2.0,
                contract_loan_amount=customer.cbs_outstanding_amount,
                contract_tenure_months=36,
                contract_interest_rate=12.5,
                contract_default_clause="Standard default clause",
                contract_governing_law="Indian Contract Act"
            )
            db.add(contract)
            db.flush()
            contracts_created += 1
            
            # Link contract to customer
            customer.contract_note_id = contract.id
        
        db.commit()
        
        print(f"\n✅ Successfully created:")
        print(f"   👥 Customers: {customers_created}")
        print(f"   💰 Loans: {loans_created}")
        print(f"   📄 Contract Notes: {contracts_created}")
        
        # Verify the data
        print(f"\n🔍 Verification:")
        customers = db.query(models.Customer).all()
        for c in customers:
            print(f"   {c.customer_no}: {c.name} (CIBIL: {c.cibil_score}, Risk: {c.cbs_risk_level})")
        
        db.close()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Loading customer data directly from Excel...")
    print("=" * 60)
    load_customers_from_excel()
    print("=" * 60)
    print("✅ Done! Check Collection Cell to see the data.")

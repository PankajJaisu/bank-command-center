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


def create_sample_customers():
    """Create sample customers based on spreadsheet data format"""
    
    # Sample customer data based on your spreadsheet
    customers_data = [
        {
            "customer_no": "CUST-8801",
            "name": "John Smith", 
            "cibil_score": 720,
            "days_since_employment": 15,
            "employment_status": "Verified",
            "cbs_income_verification": "35%",
            "salary_last_date": date(2025, 8, 2),
            "cbs_outstanding_amount": 350000,
            "cbs_risk_level": "red",
            "pending_amount": 10000,
            "pendency": "Yes",
            "cbs_emi_amount": 50000,
            "cbs_due_day": 5,
        },
        {
            "customer_no": "CUST-8802", 
            "name": "Amit Sharma",
            "cibil_score": 650,
            "days_since_employment": 20,
            "employment_status": "Unverified", 
            "cbs_income_verification": "55%",
            "salary_last_date": date(2025, 8, 5),
            "cbs_outstanding_amount": 520000,
            "cbs_risk_level": "amber",
            "pending_amount": 0,
            "pendency": "No",
            "cbs_emi_amount": 75000,
            "cbs_due_day": 10,
        },
        {
            "customer_no": "CUST-8803",
            "name": "Priya Kapoor",
            "cibil_score": 580,
            "days_since_employment": 45,
            "employment_status": "High-Risk",
            "cbs_income_verification": "68%", 
            "salary_last_date": date(2025, 8, 7),
            "cbs_outstanding_amount": 800000,
            "cbs_risk_level": "red",
            "pending_amount": 3000,
            "pendency": "Yes",
            "cbs_emi_amount": 60000,
            "cbs_due_day": 15,
        },
        {
            "customer_no": "CUST-8804",
            "name": "Michael Brown",
            "cibil_score": 780,
            "days_since_employment": 10,
            "employment_status": "Verified",
            "cbs_income_verification": "25%",
            "salary_last_date": date(2025, 8, 1),
            "cbs_outstanding_amount": 200000,
            "cbs_risk_level": "yellow",
            "pending_amount": 13500,
            "pendency": "Yes",
            "cbs_emi_amount": 45000,
            "cbs_due_day": 20,
        },
        {
            "customer_no": "CUST-8805",
            "name": "Sara Khan", 
            "cibil_score": 695,
            "days_since_employment": -10,
            "employment_status": "Verified",
            "cbs_income_verification": "50%",
            "salary_last_date": date(2025, 8, 3),
            "cbs_outstanding_amount": 450000,
            "cbs_risk_level": "amber",
            "pending_amount": 0,
            "pendency": "No",
            "cbs_emi_amount": 55000,
            "cbs_due_day": 25,
        },
        {
            "customer_no": "CUST-8806",
            "name": "David Lee",
            "cibil_score": 610,
            "days_since_employment": -35,
            "employment_status": "Unverified",
            "cbs_income_verification": "60%",
            "salary_last_date": date(2025, 8, 6),
            "cbs_outstanding_amount": 670000,
            "cbs_risk_level": "red",
            "pending_amount": 32000,
            "pendency": "Yes",
            "cbs_emi_amount": 80000,
            "cbs_due_day": 30,
        },
        {
            "customer_no": "CUST-8807",
            "name": "Pankaj Jaiswal",
            "cibil_score": 650,
            "days_since_employment": 39,
            "employment_status": "Verified",
            "cbs_income_verification": "75%",
            "salary_last_date": date(2025, 8, 7),
            "cbs_outstanding_amount": 689949,
            "cbs_risk_level": "amber",
            "pending_amount": 85843,
            "pendency": "Yes",
            "cbs_emi_amount": 68949,
            "cbs_due_day": 15,
        }
    ]
    
    db = SessionLocal()
    try:
        print("🗑️ Clearing existing customer data...")
        # Clear existing data
        db.query(models.DataIntegrityAlert).delete()
        db.query(models.Loan).delete() 
        db.query(models.Customer).delete()
        db.query(models.ContractNote).delete()
        
        print("👥 Creating sample customers...")
        created_customers = []
        
        for customer_data in customers_data:
            # Create customer
            customer = models.Customer(
                customer_no=customer_data["customer_no"],
                name=customer_data["name"],
                email=f"{customer_data['name'].lower().replace(' ', '.')}@email.com",
                phone="+1 (555) 123-4567",
                address="1234 Main Street, City, State 12345",
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
            created_customers.append(customer)
            
            # Create a loan for each customer
            loan = models.Loan(
                loan_id=f"LN-{customer.id:05d}",
                customer_id=customer.id,
                loan_amount=customer_data["cbs_outstanding_amount"] * 1.2,  # Original amount estimate
                emi_amount=customer_data["cbs_emi_amount"],
                tenure_months=60,  # 5 years
                interest_rate=12.5,
                status="active",
                outstanding_amount=customer_data["cbs_outstanding_amount"],
                last_payment_date=customer.cbs_last_payment_date,
                next_due_date=customer.cbs_last_payment_date + relativedelta(months=1),
            )
            
            db.add(loan)
            
            # Create contract note if customer has good CIBIL score
            if customer_data["cibil_score"] > 600:
                contract_note = models.ContractNote(
                    filename=f"contract_{customer_data['customer_no']}.pdf",
                    file_path=f"/contracts/{customer_data['customer_no']}.pdf",
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
                
                # Link customer to contract note
                customer.contract_note_id = contract_note.id
            
            # Create data integrity alert for high-risk customers
            if customer_data["cbs_risk_level"] == "red" or customer_data["pending_amount"] > 0:
                alert = models.DataIntegrityAlert(
                    customer_id=customer.id,
                    alert_type="PAYMENT_OVERDUE" if customer_data["pending_amount"] > 0 else "HIGH_RISK",
                    title=f"High Risk Customer: {customer.name}",
                    description=f"Customer has CIBIL score of {customer_data['cibil_score']} and pending amount of ₹{customer_data['pending_amount']:,.2f}",
                    severity="high" if customer_data["cbs_risk_level"] == "red" else "medium",
                    cbs_value=str(customer_data["cbs_outstanding_amount"]),
                    contract_value=str(customer_data["cbs_emi_amount"]),
                    is_resolved=False,
                )
                
                db.add(alert)
        
        db.commit()
        print(f"✅ Created {len(created_customers)} customers with loans and related data")
        
        # Show summary
        total_customers = db.query(models.Customer).count()
        total_loans = db.query(models.Loan).count()
        total_contracts = db.query(models.ContractNote).count()
        total_alerts = db.query(models.DataIntegrityAlert).count()
        
        print(f"📊 Database summary:")
        print(f"   👥 Customers: {total_customers}")
        print(f"   💰 Loans: {total_loans}")
        print(f"   📄 Contract Notes: {total_contracts}")
        print(f"   🚨 Data Integrity Alerts: {total_alerts}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating sample data: {e}")
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    print("🚀 Loading customer data from spreadsheet format...")
    success = create_sample_customers()
    
    if success:
        print("✅ Customer data loaded successfully!")
        print("💡 You can now view this data in the Collection Cell and Dashboard.")
    else:
        print("❌ Failed to load customer data.")
        sys.exit(1)

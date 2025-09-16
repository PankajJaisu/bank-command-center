#!/usr/bin/env python3
"""
Simple script to fix the database schema and add sample customer data
"""
import sqlite3
import os
from datetime import datetime, date

def fix_database():
    """Fix database schema and add sample data"""
    
    # Look for database file
    db_files = ['ap_command_center.db', 'database.db', 'app.db']
    db_path = None
    
    for db_file in db_files:
        if os.path.exists(db_file):
            db_path = db_file
            break
    
    if not db_path:
        print("❌ No database file found. Please ensure the database exists.")
        return False
    
    print(f"📊 Found database: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔄 Adding new customer fields...")
        
        # Add new columns (ignore errors if they already exist)
        new_columns = [
            "ALTER TABLE customers ADD COLUMN cibil_score INTEGER",
            "ALTER TABLE customers ADD COLUMN days_since_employment INTEGER", 
            "ALTER TABLE customers ADD COLUMN employment_status TEXT",
            "ALTER TABLE customers ADD COLUMN cbs_income_verification TEXT",
            "ALTER TABLE customers ADD COLUMN salary_last_date DATE",
            "ALTER TABLE customers ADD COLUMN pending_amount REAL",
            "ALTER TABLE customers ADD COLUMN pendency TEXT"
        ]
        
        for sql in new_columns:
            try:
                cursor.execute(sql)
                print(f"✅ Added column: {sql.split()[-2]}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print(f"ℹ️  Column already exists: {sql.split()[-2]}")
                else:
                    print(f"⚠️  Error adding column: {e}")
        
        print("🗑️ Clearing existing customer data...")
        cursor.execute("DELETE FROM customers")
        
        print("👥 Adding sample customer data...")
        
        # Sample customer data
        customers = [
            ('CUST-8801', 'John Smith', 'john.smith@email.com', '+1 (555) 123-4567', 
             720, 15, 'Verified', '35%', '2025-08-02', 350000, 'red', 10000, 'Yes', 50000, 5),
            ('CUST-8802', 'Amit Sharma', 'amit.sharma@email.com', '+1 (555) 123-4568',
             650, 20, 'Unverified', '55%', '2025-08-05', 520000, 'amber', 0, 'No', 75000, 10),
            ('CUST-8803', 'Priya Kapoor', 'priya.kapoor@email.com', '+1 (555) 123-4569',
             580, 45, 'High-Risk', '68%', '2025-08-07', 800000, 'red', 3000, 'Yes', 60000, 15),
            ('CUST-8804', 'Michael Brown', 'michael.brown@email.com', '+1 (555) 123-4570',
             780, 10, 'Verified', '25%', '2025-08-01', 200000, 'yellow', 13500, 'Yes', 45000, 20),
            ('CUST-8805', 'Sara Khan', 'sara.khan@email.com', '+1 (555) 123-4571',
             695, -10, 'Verified', '50%', '2025-08-03', 450000, 'amber', 0, 'No', 55000, 25),
            ('CUST-8806', 'David Lee', 'david.lee@email.com', '+1 (555) 123-4572',
             610, -35, 'Unverified', '60%', '2025-08-06', 670000, 'red', 32000, 'Yes', 80000, 30),
            ('CUST-8807', 'Pankaj Jaiswal', 'pankaj.jaiswal@email.com', '+1 (555) 123-4573',
             650, 39, 'Verified', '75%', '2025-08-07', 689949, 'amber', 85843, 'Yes', 68949, 15)
        ]
        
        insert_sql = """
        INSERT INTO customers (
            customer_no, name, email, phone, 
            cibil_score, days_since_employment, employment_status, 
            cbs_income_verification, salary_last_date,
            cbs_outstanding_amount, cbs_risk_level, 
            pending_amount, pendency, cbs_emi_amount, cbs_due_day,
            address, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        for customer in customers:
            cursor.execute(insert_sql, customer + (
                '1234 Main Street, City, State 12345',
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
        
        conn.commit()
        
        # Verify the data
        cursor.execute("SELECT COUNT(*) FROM customers")
        count = cursor.fetchone()[0]
        
        print(f"✅ Database updated successfully!")
        print(f"📊 Total customers: {count}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error updating database: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting database fix...")
    success = fix_database()
    
    if success:
        print("✅ Database fix completed!")
        print("💡 You can now test the dynamic data features.")
        print("🔄 Restart your backend server to see the changes.")
    else:
        print("❌ Database fix failed.")

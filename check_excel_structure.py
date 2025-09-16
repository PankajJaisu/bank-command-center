#!/usr/bin/env python3
"""
Simple script to check Excel file structure
"""

import pandas as pd
import os

def check_excel_structure():
    excel_file = "sample_data/customer_data/Customer_Loan_Data_Overdue (1).xlsx"
    
    if not os.path.exists(excel_file):
        print(f"❌ Excel file not found: {excel_file}")
        return
    
    try:
        # Read the Excel file
        df = pd.read_excel(excel_file)
        
        print("📊 Excel File Analysis")
        print("=" * 50)
        print(f"📋 Columns found: {df.columns.tolist()}")
        print(f"📈 Total rows: {len(df)}")
        print("\n📄 First 3 rows:")
        print(df.head(3).to_string())
        
        # Check for overdue amount column
        overdue_cols = [col for col in df.columns if 'overdue' in col.lower() or 'amount' in col.lower()]
        print(f"\n💰 Potential overdue amount columns: {overdue_cols}")
        
        # Check for specific values from your image
        if 'Overdue Amount' in df.columns:
            print(f"\n🎯 Overdue Amount values: {df['Overdue Amount'].tolist()}")
        
    except Exception as e:
        print(f"❌ Error reading Excel file: {e}")

if __name__ == "__main__":
    check_excel_structure()

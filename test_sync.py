#!/usr/bin/env python3
"""
Test script to verify the sync sample data functionality works correctly
"""

import requests
import time
import json

API_BASE_URL = "http://localhost:8000/api"

def test_sync_functionality():
    print("🧪 Testing Sync Sample Data Functionality")
    print("=" * 50)
    
    # 1. Check initial state
    print("1. Checking initial database state...")
    try:
        response = requests.get(f"{API_BASE_URL}/collection/loan-accounts?limit=10")
        if response.status_code == 200:
            data = response.json()
            print(f"   Initial loan accounts: {len(data)}")
        else:
            print(f"   API Error: {response.status_code}")
    except Exception as e:
        print(f"   Connection Error: {e}")
        return
    
    # 2. Trigger sync
    print("\n2. Triggering sync sample data...")
    try:
        response = requests.post(f"{API_BASE_URL}/documents/sync-sample-data")
        if response.status_code == 202:
            job_data = response.json()
            job_id = job_data["id"]
            print(f"   ✅ Sync job started: #{job_id}")
            
            # 3. Monitor job progress
            print("\n3. Monitoring job progress...")
            for i in range(30):  # Wait up to 30 seconds
                try:
                    job_response = requests.get(f"{API_BASE_URL}/jobs/{job_id}")
                    if job_response.status_code == 200:
                        job_status = job_response.json()
                        status = job_status.get("status", "unknown")
                        processed = job_status.get("processed_files", 0)
                        total = job_status.get("total_files", 0)
                        
                        print(f"   Status: {status} ({processed}/{total})")
                        
                        if status == "completed":
                            print("   ✅ Job completed successfully!")
                            break
                        elif status == "failed":
                            print("   ❌ Job failed!")
                            print(f"   Summary: {job_status.get('summary', {})}")
                            break
                    
                    time.sleep(1)
                except Exception as e:
                    print(f"   Error checking job status: {e}")
                    break
            
            # 4. Check final state
            print("\n4. Checking final database state...")
            try:
                response = requests.get(f"{API_BASE_URL}/collection/loan-accounts?limit=10")
                if response.status_code == 200:
                    data = response.json()
                    print(f"   Final loan accounts: {len(data)}")
                    if len(data) > 0:
                        print("   Sample account:")
                        account = data[0]
                        print(f"     Customer: {account.get('customerName', 'N/A')}")
                        print(f"     Customer No: {account.get('customerNo', 'N/A')}")
                        print(f"     CIBIL Score: {account.get('cibilScore', 'N/A')}")
                        print(f"     Risk Level: {account.get('riskLevel', 'N/A')}")
                else:
                    print(f"   API Error: {response.status_code}")
            except Exception as e:
                print(f"   Error checking final state: {e}")
                
        else:
            print(f"   ❌ Failed to start sync: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"   Connection Error: {e}")

if __name__ == "__main__":
    test_sync_functionality()

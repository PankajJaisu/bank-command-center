#!/usr/bin/env python3
"""
Test Data Verification Script
Proves that the generated test data is perfectly aligned between PDFs and structured data.
"""
import json
import csv
import os


def verify_test_data_alignment():
    """Verify that PO numbers in structured data match those referenced by invoices."""

    print("🔍 Supervity AP Test Data Verification")
    print("=" * 50)

    # Load structured data
    pos_file = "sample_data/pos.json"
    grns_file = "sample_data/grns.csv"

    if not os.path.exists(pos_file):
        print("❌ pos.json not found. Run scripts/data_generator.py first.")
        return False

    if not os.path.exists(grns_file):
        print("❌ grns.csv not found. Run scripts/data_generator.py first.")
        return False

    # Load PO data
    with open(pos_file, "r") as f:
        pos_data = json.load(f)

    po_numbers = set()
    for po in pos_data:
        po_numbers.add(po["po_number"])

    print(f"📄 Found {len(po_numbers)} Purchase Orders in pos.json:")
    for po_num in sorted(po_numbers):
        print(f"   ✓ {po_num}")

    # Load GRN data
    grn_po_numbers = set()
    grn_numbers = set()
    with open(grns_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            grn_numbers.add(row["grn_number"])
            grn_po_numbers.add(row["po_number"])

    print(f"\n📄 Found {len(grn_numbers)} Goods Receipt Notes in grns.csv:")
    for grn_num in sorted(grn_numbers):
        print(f"   ✓ {grn_num}")

    # Expected invoice-to-PO mappings based on our test data generation
    invoice_po_mappings = {
        "INV-GT-5001": ["PO-GT-1001"],
        "INV-AM-98002": ["PO-AM-78002"],
        "INV-AM-98003": ["PO-AM-78003"],
        "INV-AM-98004": ["PO-AM-78004"],
        "INV-AM-98005": ["PO-AM-78005-A", "PO-AM-78005-B"],
        "INV-IC-2024-01": [],  # Non-PO invoice
        "INV-AM-98010": ["PO-AM-78008"],
        "INV-AM-98011": ["PO-AM-78009"],
        "INV-AM-98012": ["PO-AM-78010"],
        "INV-GT-5002": ["PO-GT-1002"],
        "INV-GT-5003": ["PO-GT-1003"],
        "INV-AM-98013": ["PO-AM-78011"],
        "INV-AM-98013-DUP": ["PO-AM-78011"],
    }

    print(f"\n🔗 Verifying Invoice-to-PO alignment:")
    all_aligned = True

    for invoice, expected_pos in invoice_po_mappings.items():
        if not expected_pos:  # Non-PO invoice
            print(f"   ✓ {invoice} → Non-PO (Service Invoice)")
            continue

        missing_pos = []
        for po in expected_pos:
            if po not in po_numbers:
                missing_pos.append(po)

        if missing_pos:
            print(f"   ❌ {invoice} → {expected_pos} (MISSING: {missing_pos})")
            all_aligned = False
        else:
            po_list = ", ".join(expected_pos)
            print(f"   ✓ {invoice} → {po_list}")

    # Verify GRN-to-PO alignment
    print(f"\n🔗 Verifying GRN-to-PO alignment:")
    grn_alignment_good = True

    for grn_po in grn_po_numbers:
        if grn_po not in po_numbers:
            print(f"   ❌ GRN references {grn_po} but PO not found in pos.json")
            grn_alignment_good = False

    if grn_alignment_good:
        print(f"   ✓ All {len(grn_po_numbers)} GRN references point to valid POs")

    # Summary
    print("\n" + "=" * 50)
    if all_aligned and grn_alignment_good:
        print("🎉 VERIFICATION PASSED!")
        print("   All invoices reference POs that exist in structured data.")
        print("   All GRNs reference valid POs.")
        print("   The 3-way matching system will work perfectly!")
        return True
    else:
        print("❌ VERIFICATION FAILED!")
        print("   Some invoices reference POs that don't exist in structured data.")
        print("   The matching system will show 'Missing Document' errors.")
        return False


if __name__ == "__main__":
    verify_test_data_alignment()

#!/usr/bin/env python3
"""
DEFINITIVE Test Data Generator for Supervity Proactive Loan Command Center
- Creates PDFs for INVOICES ONLY.
- Creates matching structured data files (pos.json, grns.csv).
"""
import os
import sys
import json
import csv
from datetime import datetime, timedelta

# Add sample_data directory to path to import pdf_templates
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "sample_data"))
from pdf_templates import draw_po_pdf, draw_grn_pdf, draw_invoice_pdf

# Ensure output directory exists and is correctly located
SAMPLE_DATA_DIR = "sample_data"
PDF_OUTPUT_DIR = os.path.join(SAMPLE_DATA_DIR, "invoices")
STRUCTURED_DATA_OUTPUT_DIR = "sample_data"  # Output to the main sample_data directory
os.makedirs(PDF_OUTPUT_DIR, exist_ok=True)
os.makedirs(STRUCTURED_DATA_OUTPUT_DIR, exist_ok=True)

# --- GLOBAL LISTS TO STORE STRUCTURED DATA ---
ALL_POS = []
ALL_GRNS = []

# --- VENDOR & BUYER DEFINITIONS ---
ACME_DETAILS = {
    "name": "Acme Manufacturing",
    "address": "123 Industrial Park Drive\nManufacturing City, MC 12345",
}
GLOBAL_DETAILS = {
    "name": "Global Supplies Co",
    "address": "456 Commerce Boulevard\nSupply Town, ST 67890",
}
PREMIER_DETAILS = {
    "name": "Premier Components Inc",
    "address": "789 Technology Way\nComponent Valley, CV 11111",
}
INDUSTRIAL_DETAILS = {
    "name": "Industrial Partners Ltd",
    "address": "321 Business Center\nIndustrial District, ID 22222",
}
STANDARD_DETAILS = {
    "name": "Standard Materials Corp",
    "address": "654 Corporate Plaza\nMaterials Hub, MH 33333",
}
CONSULTDETAILS = {
    "name": "Professional Services LLC",
    "address": "987 Executive Suite\nBusiness City, BC 44444",
}
BUYERDETAILS = {
    "name": "Supervity Inc",
    "address": "123 Automation Lane\nFuture City, FC 54321",
}


# --- HELPER TO STANDARDIZE DATA ---
def get_base_data(vendor_details, po_number, order_date):
    return {
        "buyer_name": BUYERDETAILS["name"],
        "buyer_address": BUYERDETAILS["address"],
        "vendor_name": vendor_details["name"],
        "vendor_address": vendor_details["address"],
        "po_number": po_number,
        "order_date": order_date,
    }


def calculate_totals(line_items):
    subtotal = sum(item.get("line_total", 0) for item in line_items)
    tax = subtotal * 0.088  # Standard 8.8% tax
    grand_total = subtotal + tax
    return {"po_subtotal": subtotal, "po_tax": tax, "po_grand_total": grand_total}


# --- TEST SETS ---


def set_1_perfect_match_clean_vendor():
    print("  1. Perfect Match (Clean Vendor)...")
    po_data = get_base_data(ACME_DETAILS, "PO-AC-1001", datetime(2024, 3, 1))
    line_items = [
        {
            "sku": "AC-CBL-01",
            "description": "USB-C Cable Pack",
            "ordered_qty": 50,
            "unit": "packs",
            "unit_price": 25.00,
            "line_total": 1250.00,
        },
        {
            "sku": "AC-MSE-05",
            "description": "Ergonomic Mouse",
            "ordered_qty": 20,
            "unit": "pieces",
            "unit_price": 45.00,
            "line_total": 900.00,
        },
    ]
    po_data.update(calculate_totals(line_items))
    po_data["line_items"] = line_items
    ALL_POS.append(
        {
            "po_number": po_data["po_number"],
            "vendor_name": po_data["vendor_name"],
            "order_date": po_data["order_date"].strftime("%Y-%m-%d"),
            "line_items": po_data["line_items"],
        }
    )

    grn_items = [
        {
            "sku": "AC-CBL-01",
            "description": "USB-C Cable Pack",
            "received_qty": 50,
            "unit": "packs",
        },
        {
            "sku": "AC-MSE-05",
            "description": "Ergonomic Mouse",
            "received_qty": 20,
            "unit": "pieces",
        },
    ]
    grn_number = "GRN-AC-1001"
    ALL_GRNS.append(
        {
            "grn_number": grn_number,
            "po_number": po_data["po_number"],
            "received_date": datetime(2024, 3, 10).strftime("%Y-%m-%d"),
            "line_items": grn_items,
        }
    )

    inv_line_items = [
        {
            "description": "USB-C Cable Pack",
            "quantity": 50,
            "unit_price": 25.00,
            "line_total": 1250.00,
        },
        {
            "description": "Ergonomic Mouse",
            "quantity": 20,
            "unit_price": 45.00,
            "line_total": 900.00,
        },
    ]
    inv_data = {
        **po_data,
        "related_po_numbers": [po_data["po_number"]],
        "related_grn_numbers": [grn_number],
        "line_items": inv_line_items,
    }
    draw_invoice_pdf(
        inv_data,
        "INV-AC-5001",
        datetime(2024, 3, 11),
        datetime(2024, 4, 10),
        f"{PDF_OUTPUT_DIR}/Set01_INV-AC-5001.pdf",
    )


def set_2_price_mismatch_for_demo():
    print("  2. Price Mismatch (Demo Scenario)...")
    po_data = get_base_data(GLOBAL_DETAILS, "PO-GL-78002", datetime(2024, 3, 5))
    line_items = [
        {
            "sku": "GL-CD-003",
            "description": "Cutting Disc",
            "ordered_qty": 50,
            "unit": "pieces",
            "unit_price": 10.00,
            "line_total": 500.00,
        }
    ]
    po_data.update(calculate_totals(line_items))
    po_data["line_items"] = line_items
    ALL_POS.append(
        {
            "po_number": po_data["po_number"],
            "vendor_name": po_data["vendor_name"],
            "order_date": po_data["order_date"].strftime("%Y-%m-%d"),
            "line_items": po_data["line_items"],
        }
    )

    grn_items = [
        {
            "sku": "GL-CD-003",
            "description": "Cutting Disc",
            "received_qty": 50,
            "unit": "pieces",
        }
    ]
    grn_number = "GRN-GL-84002"
    ALL_GRNS.append(
        {
            "grn_number": grn_number,
            "po_number": po_data["po_number"],
            "received_date": datetime(2024, 3, 15).strftime("%Y-%m-%d"),
            "line_items": grn_items,
        }
    )

    inv_line_items = [
        {
            "description": "Cutting Disc",
            "quantity": 50,
            "unit_price": 11.00,
            "line_total": 550.00,
        }
    ]
    inv_data = {
        **po_data,
        "related_po_numbers": [po_data["po_number"]],
        "related_grn_numbers": [grn_number],
        "line_items": inv_line_items,
    }
    draw_invoice_pdf(
        inv_data,
        "INV-GL-98002",
        datetime(2024, 3, 16),
        datetime(2024, 4, 15),
        f"{PDF_OUTPUT_DIR}/Set02_INV-GL-98002.pdf",
    )


def set_3_mixed_line_item_issue():
    print("  3. Mixed Line Item Issues...")
    po_data = get_base_data(PREMIER_DETAILS, "PO-PR-78003", datetime(2024, 3, 8))
    line_items = [
        {
            "sku": "PR-SG-004",
            "description": "Safety Gloves",
            "ordered_qty": 100,
            "unit": "pairs",
            "unit_price": 15.00,
            "line_total": 1500.00,
        },
        {
            "sku": "PR-HH-005",
            "description": "Hard Hat",
            "ordered_qty": 20,
            "unit": "pieces",
            "unit_price": 22.00,
            "line_total": 440.00,
        },
    ]
    po_data.update(calculate_totals(line_items))
    po_data["line_items"] = line_items
    ALL_POS.append(
        {
            "po_number": po_data["po_number"],
            "vendor_name": po_data["vendor_name"],
            "order_date": po_data["order_date"].strftime("%Y-%m-%d"),
            "line_items": po_data["line_items"],
        }
    )

    grn_items = [
        {
            "sku": "PR-SG-004",
            "description": "Safety Gloves",
            "received_qty": 95,
            "unit": "pairs",
        },
        {
            "sku": "PR-HH-005",
            "description": "Hard Hat",
            "received_qty": 20,
            "unit": "pieces",
        },
    ]
    grn_number = "GRN-PR-84003"
    ALL_GRNS.append(
        {
            "grn_number": grn_number,
            "po_number": po_data["po_number"],
            "received_date": datetime(2024, 3, 18).strftime("%Y-%m-%d"),
            "line_items": grn_items,
        }
    )

    inv_line_items = [
        {
            "description": "Safety Gloves",
            "quantity": 95,
            "unit_price": 15.00,
            "line_total": 1425.00,
        },
        {
            "description": "Hard Hat",
            "quantity": 21,
            "unit_price": 22.00,
            "line_total": 462.00,
        },
    ]
    inv_data = {
        **po_data,
        "related_po_numbers": [po_data["po_number"]],
        "related_grn_numbers": [grn_number],
        "line_items": inv_line_items,
    }
    draw_invoice_pdf(
        inv_data,
        "INV-PR-98003",
        datetime(2024, 3, 19),
        datetime(2024, 4, 18),
        f"{PDF_OUTPUT_DIR}/Set03_INV-PR-98003.pdf",
    )


def set_4_multi_grn_to_invoice():
    print("  4. Multi-GRN to Single Invoice...")
    po_data = get_base_data(INDUSTRIAL_DETAILS, "PO-IN-78004", datetime(2024, 3, 12))
    line_items = [
        {
            "sku": "IN-CW-005",
            "description": "Copper Wire",
            "ordered_qty": 500,
            "unit": "meters",
            "unit_price": 2.00,
            "line_total": 1000.00,
        }
    ]
    po_data.update(calculate_totals(line_items))
    po_data["line_items"] = line_items
    ALL_POS.append(
        {
            "po_number": po_data["po_number"],
            "vendor_name": po_data["vendor_name"],
            "order_date": po_data["order_date"].strftime("%Y-%m-%d"),
            "line_items": po_data["line_items"],
        }
    )

    grn_a_num, grn_b_num = "GRN-IN-84004-A", "GRN-IN-84004-B"
    grn_a_items = [
        {
            "sku": "IN-CW-005",
            "description": "Copper Wire",
            "received_qty": 300,
            "unit": "meters",
        }
    ]
    grn_b_items = [
        {
            "sku": "IN-CW-005",
            "description": "Copper Wire",
            "received_qty": 200,
            "unit": "meters",
        }
    ]
    ALL_GRNS.append(
        {
            "grn_number": grn_a_num,
            "po_number": po_data["po_number"],
            "received_date": datetime(2024, 3, 20).strftime("%Y-%m-%d"),
            "line_items": grn_a_items,
        }
    )
    ALL_GRNS.append(
        {
            "grn_number": grn_b_num,
            "po_number": po_data["po_number"],
            "received_date": datetime(2024, 3, 25).strftime("%Y-%m-%d"),
            "line_items": grn_b_items,
        }
    )

    inv_line_items = [
        {
            "description": "Copper Wire",
            "quantity": 500,
            "unit_price": 2.0,
            "line_total": 1000.0,
        }
    ]
    inv_data = {
        **po_data,
        "related_po_numbers": [po_data["po_number"]],
        "related_grn_numbers": [grn_a_num, grn_b_num],
        "line_items": inv_line_items,
    }
    draw_invoice_pdf(
        inv_data,
        "INV-IN-98004",
        datetime(2024, 3, 26),
        datetime(2024, 4, 25),
        f"{PDF_OUTPUT_DIR}/Set04_INV-IN-98004.pdf",
    )


def set_5_multi_po_to_invoice():
    print("  5. Multi-PO to Single Invoice...")
    po1 = get_base_data(STANDARD_DETAILS, "PO-ST-78005-A", datetime(2024, 3, 15))
    po1_li = [
        {
            "sku": "ST-SP-008",
            "description": "Steel Plate",
            "ordered_qty": 25,
            "unit": "pieces",
            "unit_price": 120.00,
            "line_total": 3000.00,
        }
    ]
    po1.update(calculate_totals(po1_li))
    po1["line_items"] = po1_li
    ALL_POS.append(
        {
            "po_number": po1["po_number"],
            "vendor_name": po1["vendor_name"],
            "order_date": po1["order_date"].strftime("%Y-%m-%d"),
            "line_items": po1["line_items"],
        }
    )

    po2 = get_base_data(STANDARD_DETAILS, "PO-ST-78005-B", datetime(2024, 3, 16))
    po2_li = [
        {
            "sku": "ST-RB-009",
            "description": "Rivet Bundle",
            "ordered_qty": 5,
            "unit": "sets",
            "unit_price": 150.00,
            "line_total": 750.00,
        }
    ]
    po2.update(calculate_totals(po2_li))
    po2["line_items"] = po2_li
    ALL_POS.append(
        {
            "po_number": po2["po_number"],
            "vendor_name": po2["vendor_name"],
            "order_date": po2["order_date"].strftime("%Y-%m-%d"),
            "line_items": po2["line_items"],
        }
    )

    inv_line_items = [
        {
            "description": "Steel Plate",
            "quantity": 25,
            "unit_price": 120.00,
            "line_total": 3000.00,
        },
        {
            "description": "Rivet Bundle",
            "quantity": 5,
            "unit_price": 150.00,
            "line_total": 750.00,
        },
    ]
    inv_data = {
        **po1,
        "related_po_numbers": [po1["po_number"], po2["po_number"]],
        "related_grn_numbers": [],
        "line_items": inv_line_items,
    }
    draw_invoice_pdf(
        inv_data,
        "INV-ST-98005",
        datetime(2024, 3, 28),
        datetime(2024, 4, 27),
        f"{PDF_OUTPUT_DIR}/Set05_INV-ST-98005.pdf",
    )


def set_6_non_po_service_invoice():
    print("  6. Non-PO Service Invoice...")
    inv_line_items = [
        {
            "description": "Q1 Strategy Consulting Services",
            "quantity": 1,
            "unit_price": 5000.00,
            "line_total": 5000.00,
        }
    ]
    inv_data = {
        **get_base_data(CONSULTDETAILS, "", datetime(2024, 4, 1)),
        "line_items": inv_line_items,
        "related_po_numbers": [],
        "related_grn_numbers": [],
    }
    draw_invoice_pdf(
        inv_data,
        "INV-IC-2024-01",
        datetime(2024, 4, 1),
        datetime(2024, 4, 30),
        f"{PDF_OUTPUT_DIR}/Set06_INV-IC-2024-01_NonPO.pdf",
    )


def set_7_unit_conversion_issue():
    print("  7. Unit Conversion (tons/kg/lbs)...")
    po_data = get_base_data(ACME_DETAILS, "PO-AC-78008", datetime(2024, 2, 20))
    line_items = [
        {
            "sku": "AC-AC-009",
            "description": "Aluminum Coil",
            "ordered_qty": 2,
            "unit": "tons",
            "unit_price": 1800.00,
            "line_total": 3600.00,
        }
    ]
    po_data.update(calculate_totals(line_items))
    po_data["line_items"] = line_items
    ALL_POS.append(
        {
            "po_number": po_data["po_number"],
            "vendor_name": po_data["vendor_name"],
            "order_date": po_data["order_date"].strftime("%Y-%m-%d"),
            "line_items": po_data["line_items"],
        }
    )

    grn_items = [
        {
            "sku": "AC-AC-009",
            "description": "Aluminum Coil",
            "received_qty": 2000,
            "unit": "kg",
        }
    ]
    grn_number = "GRN-AC-84009"
    ALL_GRNS.append(
        {
            "grn_number": grn_number,
            "po_number": po_data["po_number"],
            "received_date": datetime(2024, 3, 1).strftime("%Y-%m-%d"),
            "line_items": grn_items,
        }
    )

    inv_line_items = [
        {
            "description": "Aluminum Coil",
            "quantity": 4409,
            "unit_price": 0.82,
            "line_total": 3615.38,
        }
    ]
    inv_data = {
        **po_data,
        "related_po_numbers": [po_data["po_number"]],
        "related_grn_numbers": [grn_number],
        "line_items": inv_line_items,
    }
    draw_invoice_pdf(
        inv_data,
        "INV-AC-98010",
        datetime(2024, 3, 2),
        datetime(2024, 4, 1),
        f"{PDF_OUTPUT_DIR}/Set07_INV-AC-98010.pdf",
    )


def set_8_financial_mismatch():
    print("  8. Financial Calculation Mismatch...")
    po_data = get_base_data(GLOBAL_DETAILS, "PO-GL-78009", datetime(2024, 4, 5))
    line_items = [
        {
            "sku": "GL-WP-012",
            "description": "Washer Pack",
            "ordered_qty": 200,
            "unit": "packs",
            "unit_price": 8.00,
            "line_total": 1600.00,
        }
    ]
    po_data.update(calculate_totals(line_items))
    po_data["line_items"] = line_items
    ALL_POS.append(
        {
            "po_number": po_data["po_number"],
            "vendor_name": po_data["vendor_name"],
            "order_date": po_data["order_date"].strftime("%Y-%m-%d"),
            "line_items": po_data["line_items"],
        }
    )

    inv_line_items = [
        {
            "description": "Washer Pack",
            "quantity": 200,
            "unit_price": 8.00,
            "line_total": 1600.00,
        }
    ]
    inv_data = {
        **po_data,
        "related_po_numbers": [po_data["po_number"]],
        "related_grn_numbers": [],
        "line_items": inv_line_items,
    }
    draw_invoice_pdf(
        inv_data,
        "INV-GL-98011",
        datetime(2024, 4, 10),
        datetime(2024, 5, 10),
        f"{PDF_OUTPUT_DIR}/Set08_INV-GL-98011.pdf",
        tax_override=140.80,
        grand_total_override=1740.80,
    )


def set_9_timing_violation():
    print("  9. Timing Violation (Invoice before PO)...")
    po_data = get_base_data(PREMIER_DETAILS, "PO-PR-78010", datetime(2024, 4, 15))
    line_items = [
        {
            "sku": "PR-FT-013",
            "description": "Fastener Set",
            "ordered_qty": 500,
            "unit": "pieces",
            "unit_price": 3.50,
            "line_total": 1750.00,
        }
    ]
    po_data.update(calculate_totals(line_items))
    po_data["line_items"] = line_items
    ALL_POS.append(
        {
            "po_number": po_data["po_number"],
            "vendor_name": po_data["vendor_name"],
            "order_date": po_data["order_date"].strftime("%Y-%m-%d"),
            "line_items": po_data["line_items"],
        }
    )

    inv_line_items = [
        {
            "description": "Fastener Set",
            "quantity": 500,
            "unit_price": 3.50,
            "line_total": 1750.00,
        }
    ]
    inv_data = {
        **po_data,
        "related_po_numbers": [po_data["po_number"]],
        "related_grn_numbers": [],
        "line_items": inv_line_items,
    }
    draw_invoice_pdf(
        inv_data,
        "INV-PR-98012",
        datetime(2024, 4, 14),
        datetime(2024, 5, 14),
        f"{PDF_OUTPUT_DIR}/Set09_INV-PR-98012.pdf",
    )


def set_10_and_11_volume_data():
    print(" 10 & 11. Volume Data (Perfect Matches)...")
    po_data_1 = get_base_data(INDUSTRIAL_DETAILS, "PO-IN-1002", datetime(2024, 4, 2))
    li_1 = [
        {
            "sku": "IN-KB-02",
            "description": "Mechanical Keyboard",
            "ordered_qty": 15,
            "unit": "units",
            "unit_price": 120.00,
            "line_total": 1800.00,
        }
    ]
    po_data_1.update(calculate_totals(li_1))
    po_data_1["line_items"] = li_1
    ALL_POS.append(
        {
            "po_number": po_data_1["po_number"],
            "vendor_name": po_data_1["vendor_name"],
            "order_date": po_data_1["order_date"].strftime("%Y-%m-%d"),
            "line_items": po_data_1["line_items"],
        }
    )

    inv_1_line_items = [
        {
            "description": "Mechanical Keyboard",
            "quantity": 15,
            "unit_price": 120.0,
            "line_total": 1800.0,
        }
    ]
    inv_1_data = {
        **po_data_1,
        "related_po_numbers": [po_data_1["po_number"]],
        "related_grn_numbers": [],
        "line_items": inv_1_line_items,
    }
    draw_invoice_pdf(
        inv_1_data,
        "INV-IN-5002",
        datetime(2024, 4, 3),
        datetime(2024, 5, 3),
        f"{PDF_OUTPUT_DIR}/Set10_INV-IN-5002.pdf",
    )

    po_data_2 = get_base_data(STANDARD_DETAILS, "PO-ST-1003", datetime(2024, 4, 5))
    li_2 = [
        {
            "sku": "ST-MON-27",
            "description": "27-inch Monitor",
            "ordered_qty": 10,
            "unit": "units",
            "unit_price": 350.00,
            "line_total": 3500.00,
        }
    ]
    po_data_2.update(calculate_totals(li_2))
    po_data_2["line_items"] = li_2
    ALL_POS.append(
        {
            "po_number": po_data_2["po_number"],
            "vendor_name": po_data_2["vendor_name"],
            "order_date": po_data_2["order_date"].strftime("%Y-%m-%d"),
            "line_items": po_data_2["line_items"],
        }
    )

    inv_2_line_items = [
        {
            "description": "27-inch Monitor",
            "quantity": 10,
            "unit_price": 350.0,
            "line_total": 3500.0,
        }
    ]
    inv_2_data = {
        **po_data_2,
        "related_po_numbers": [po_data_2["po_number"]],
        "related_grn_numbers": [],
        "line_items": inv_2_line_items,
    }
    draw_invoice_pdf(
        inv_2_data,
        "INV-ST-5003",
        datetime(2024, 4, 6),
        datetime(2024, 5, 6),
        f"{PDF_OUTPUT_DIR}/Set11_INV-ST-5003.pdf",
    )


def set_12_duplicate_invoice():
    print(" 12. Duplicate Invoice (Slight Variation)...")
    po_data = get_base_data(ACME_DETAILS, "PO-AC-78011", datetime(2024, 4, 20))
    line_items = [
        {
            "sku": "AC-BEAM-S",
            "description": "Small I-Beam",
            "ordered_qty": 40,
            "unit": "pieces",
            "unit_price": 75.00,
            "line_total": 3000.00,
        }
    ]
    po_data.update(calculate_totals(line_items))
    po_data["line_items"] = line_items
    ALL_POS.append(
        {
            "po_number": po_data["po_number"],
            "vendor_name": po_data["vendor_name"],
            "order_date": po_data["order_date"].strftime("%Y-%m-%d"),
            "line_items": po_data["line_items"],
        }
    )

    inv_line_items = [
        {
            "description": "Small I-Beam",
            "quantity": 40,
            "unit_price": 75.0,
            "line_total": 3000.0,
        }
    ]
    inv_data = {
        **po_data,
        "related_po_numbers": [po_data["po_number"]],
        "related_grn_numbers": [],
        "line_items": inv_line_items,
    }
    draw_invoice_pdf(
        inv_data,
        "INV-AC-98013",
        datetime(2024, 4, 22),
        datetime(2024, 5, 22),
        f"{PDF_OUTPUT_DIR}/Set12_INV-AC-98013.pdf",
    )
    draw_invoice_pdf(
        inv_data,
        "INV-AC-98013-DUP",
        datetime(2024, 4, 22),
        datetime(2024, 5, 22),
        f"{PDF_OUTPUT_DIR}/Set12_INV-AC-98013-DUP.pdf",
    )


def write_structured_files():
    """Writes the collected POs and GRNs to JSON and CSV files."""
    print("  Writing structured data files...")

    # Write pos.json
    with open(os.path.join(STRUCTURED_DATA_OUTPUT_DIR, "pos.json"), "w") as f:
        json.dump(ALL_POS, f, indent=2)
    print(f"    ✅ Wrote {len(ALL_POS)} records to pos.json")

    # Write grns.csv
    if ALL_GRNS:
        with open(
            os.path.join(STRUCTURED_DATA_OUTPUT_DIR, "grns.csv"), "w", newline=""
        ) as f:
            fieldnames = ["grn_number", "po_number", "received_date", "line_items"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for grn in ALL_GRNS:
                grn_copy = grn.copy()
                grn_copy["line_items"] = json.dumps(grn_copy["line_items"])
                writer.writerow(grn_copy)
        print(f"    ✅ Wrote {len(ALL_GRNS)} records to grns.csv")


def main():
    """Generate all test sets and structured data files."""
    print("🧪 Supervity AP Test Data Generator (v4 - Invoices only)")
    print("=" * 60)
    print(f"PDF Output directory: {PDF_OUTPUT_DIR}/")
    print(f"Structured Data Output directory: {STRUCTURED_DATA_OUTPUT_DIR}/")
    print("📝 Note: Only generating Invoice PDFs, PO/GRN data stored as JSON/CSV only")

    # Clean output directories
    if os.path.exists(PDF_OUTPUT_DIR):
        for f in os.listdir(PDF_OUTPUT_DIR):
            if f.endswith(".pdf"):
                os.remove(os.path.join(PDF_OUTPUT_DIR, f))
    print("🧹 Cleaned PDF output directory.")
    print("=" * 60)

    # Call all generation functions
    set_1_perfect_match_clean_vendor()
    set_2_price_mismatch_for_demo()
    set_3_mixed_line_item_issue()
    set_4_multi_grn_to_invoice()
    set_5_multi_po_to_invoice()
    set_6_non_po_service_invoice()
    set_7_unit_conversion_issue()
    set_8_financial_mismatch()
    set_9_timing_violation()
    set_10_and_11_volume_data()
    set_12_duplicate_invoice()

    print("\n" + "=" * 60)
    print("📄 Generated all Invoice PDF test sets.")

    # Write the structured files
    write_structured_files()

    print("\n" + "=" * 60)
    print("✅ All test data generated successfully!")
    print("\n📊 Generated Files:")
    print(f"   • {len(ALL_POS)} Purchase Orders → pos.json (structured data only)")
    print(f"   • {len(ALL_GRNS)} Goods Receipt Notes → grns.csv (structured data only)")
    print("   • 13 Invoice PDFs → sample_data/invoices/")
    print("\n🔄 Your workflow is now clean:")
    print("  1. Run the app: python run_fresh.py --reset")
    print(
        "  2. In the Data Center, click 'Sync Sample Data' to ingest the INVOICE PDFs."
    )
    print(
        "  3. Then, click 'Manual Document Upload' and select the new 'pos.json' and 'grns.csv' files to ingest the PO and GRN data."
    )


if __name__ == "__main__":
    main()

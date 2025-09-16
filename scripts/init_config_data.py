#!/usr/bin/env python3
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_dir = os.path.join(project_root, "src")
sys.path.insert(0, project_root)
sys.path.insert(0, src_dir)

from app.db.session import SessionLocal
from app.db import models
from app.modules.auth.password_service import get_password_hash
from app.config import settings


def create_roles(db):
    print("👥 Checking for user roles...")
    roles_to_create = ["admin", "ap_processor"]
    existing_roles = {role.name for role in db.query(models.Role).all()}
    created_count = 0
    for role_name in roles_to_create:
        if role_name not in existing_roles:
            new_role = models.Role(name=role_name)
            db.add(new_role)
            created_count += 1
    if created_count > 0:
        db.commit()
        print(f"✅ Created {created_count} user roles.")
    else:
        print("  -> All default roles already exist.")


def create_default_admin(db):
    print("🔐 Checking for default admin user...")
    admin_email = "admin@supervity.ai"
    admin_role = db.query(models.Role).filter(models.Role.name == "admin").first()
    if not admin_role:
        print("  -> Admin role not found. Cannot create admin user.")
        return
    if not db.query(models.User).filter(models.User.email == admin_email).first():
        new_admin = models.User(
            email=admin_email,
            hashed_password=get_password_hash("SupervityAdmin123!"),
            full_name="Default Admin",
            is_active=True,
            is_approved=True,
            role_id=admin_role.id,
        )
        db.add(new_admin)
        db.commit()
        print(f"  -> ✅ Created default admin user: {admin_email}")
    else:
        print("  -> Default admin user already exists.")


def create_default_demo_user(db):
    print("👤 Checking for default demo user...")
    demo_email = "demo@supervity.ai"
    processor_role = (
        db.query(models.Role).filter(models.Role.name == "ap_processor").first()
    )
    if not processor_role:
        print("  -> AP Processor role not found. Cannot create demo user.")
        return
    if not db.query(models.User).filter(models.User.email == demo_email).first():
        new_demo_user = models.User(
            email=demo_email,
            hashed_password=get_password_hash("SupervityDemo123!"),
            full_name="Demo User",
            is_active=True,
            is_approved=True,
            role_id=processor_role.id,
        )
        db.add(new_demo_user)
        db.flush()
        policies = [
            models.PermissionPolicy(
                user_id=new_demo_user.id,
                name="Access High-Value Acme Invoices",
                conditions={
                    "logical_operator": "AND",
                    "conditions": [
                        {
                            "field": "vendor_name",
                            "operator": "equals",
                            "value": "Acme Manufacturing",
                        },
                        {"field": "grand_total", "operator": ">", "value": 1000},
                    ],
                },
                is_active=True,
            ),
            models.PermissionPolicy(
                user_id=new_demo_user.id,
                name="Access Global Supplies",
                conditions={
                    "logical_operator": "AND",
                    "conditions": [
                        {
                            "field": "vendor_name",
                            "operator": "equals",
                            "value": "Global Supplies Co",
                        }
                    ],
                },
                is_active=True,
            ),
            models.PermissionPolicy(
                user_id=new_demo_user.id,
                name="Access Premier Components",
                conditions={
                    "logical_operator": "AND",
                    "conditions": [
                        {
                            "field": "vendor_name",
                            "operator": "equals",
                            "value": "Premier Components Inc",
                        }
                    ],
                },
                is_active=True,
            ),
        ]
        db.add_all(policies)
        db.commit()
        print(f"  -> ✅ Created default demo user: {demo_email}")
    else:
        print("  -> Default demo user already exists.")


def create_sample_automation_rules():
    print("🤖 Creating sample automation rules...")
    db = SessionLocal()
    try:
        if db.query(models.AutomationRule).count() > 0:
            print("⚠️ Found existing automation rules. Skipping creation.")
            return
        sample_rules = [
            {
                "rule_name": "Auto-approve small value invoices",
                "vendor_name": None,
                "conditions": {
                    "logical_operator": "AND",
                    "conditions": [
                        {"field": "grand_total", "operator": "<", "value": 250}
                    ],
                },
                "action": "approve",
                "is_active": 1,
                "source": "system_default",
            },
            {
                "rule_name": "Flag large invoices for manual review",
                "vendor_name": None,
                "conditions": {
                    "logical_operator": "AND",
                    "conditions": [
                        {"field": "grand_total", "operator": ">=", "value": 10000}
                    ],
                },
                "action": "flag_for_audit",
                "is_active": 1,
                "source": "system_default",
            },
        ]
        for rule_data in sample_rules:
            db.add(models.AutomationRule(**rule_data))
        db.commit()
        print(f"✅ Created {len(sample_rules)} automation rules.")
    except Exception as e:
        print(f"❌ Error creating automation rules: {e}")
        db.rollback()
    finally:
        db.close()


def create_extraction_field_configurations():
    print("📝 Creating default extraction field configurations...")
    db = SessionLocal()
    try:
        if db.query(models.ExtractionFieldConfiguration).count() > 0:
            print("⚠️ Found existing field configurations. Skipping creation.")
            return
        all_fields = {
            models.DocumentTypeEnum.Invoice: [
                ("invoice_id", "Invoice Number", True, True),
                ("vendor_name", "Vendor Name", True, True),
                ("invoice_date", "Invoice Date", True, True),
                ("grand_total", "Grand Total", True, True),
                ("due_date", "Due Date", False, True),
                ("subtotal", "Subtotal", False, True),
                ("tax", "Tax", False, True),
                ("related_po_numbers", "PO Number(s)", False, True),
            ],
            models.DocumentTypeEnum.PurchaseOrder: [
                ("po_number", "PO Number", True, True),
                ("vendor_name", "Vendor Name", True, True),
                ("order_date", "Order Date", True, True),
                ("grand_total", "Grand Total", False, True, True),
                ("subtotal", "Subtotal", False, True, True),
                ("tax", "Tax", False, True, True),
            ],
            models.DocumentTypeEnum.GoodsReceiptNote: [
                ("grn_number", "GRN Number", True, True),
                ("po_number", "Related PO Number", True, True),
                ("received_date", "Received Date", False, True),
            ],
        }
        for doc_type, fields in all_fields.items():
            for field_info in fields:
                field_name, display_name, is_essential, is_enabled = field_info[:4]
                is_editable = field_info[4] if len(field_info) > 4 else False
                db.add(
                    models.ExtractionFieldConfiguration(
                        document_type=doc_type,
                        field_name=field_name,
                        display_name=display_name,
                        is_essential=is_essential,
                        is_enabled=is_enabled,
                        is_editable=is_editable,
                    )
                )
        db.commit()
        print("✅ Created default field configurations.")
    except Exception as e:
        print(f"❌ Error creating field configurations: {e}")
        db.rollback()
    finally:
        db.close()


def create_sample_slas():
    print("🕒 Creating sample SLA policies...")
    db = SessionLocal()
    try:
        if db.query(models.SLA).count() > 0:
            print("⚠️ Found existing SLA policies. Skipping creation.")
            return
        sample_slas = [
            {
                "name": "Standard Review Time",
                "description": "Invoices in 'Needs Review' should be actioned within 2 business days.",
                "conditions": {"status": "needs_review"},
                "threshold_hours": 48,
                "is_active": True,
            },
            {
                "name": "High-Value Invoice Priority",
                "description": "Invoices over $5,000 should be processed within 1 business day.",
                "conditions": {"grand_total": {"operator": ">", "value": 5000}},
                "threshold_hours": 24,
                "is_active": True,
            },
        ]
        for sla_data in sample_slas:
            db.add(models.SLA(**sla_data))
        db.commit()
        print(f"✅ Created {len(sample_slas)} sample SLA policies.")
    except Exception as e:
        print(f"❌ Error creating sample SLAs: {e}")
        db.rollback()
    finally:
        db.close()


# --- START: New Functions for Demo Data ---
def create_sample_learned_heuristics(db):
    """Creates sample learned heuristics for the demo."""
    print("🧠 Creating sample learned heuristics for demo...")
    if db.query(models.LearnedHeuristic).count() > 0:
        print("⚠️ Found existing heuristics. Skipping creation.")
        return

    heuristics = [
        models.LearnedHeuristic(
            vendor_name="Global Supplies Co",
            exception_type="PriceMismatchException",
            learned_condition={"max_variance_percent": 8},
            resolution_action="matched",
            trigger_count=15,
            confidence_score=0.94,
        ),
        models.LearnedHeuristic(
            vendor_name="Acme Manufacturing",
            exception_type="QuantityMismatchException",
            learned_condition={"max_quantity_diff": 2},
            resolution_action="matched",
            trigger_count=8,
            confidence_score=0.89,
        ),
        models.LearnedHeuristic(
            vendor_name="Premier Components Inc",
            exception_type="PriceMismatchException",
            learned_condition={"max_variance_percent": 3},
            resolution_action="matched",
            trigger_count=5,
            confidence_score=0.83,
        ),
    ]
    db.add_all(heuristics)
    db.commit()
    print(f"✅ Created {len(heuristics)} sample learned heuristics.")


def create_sample_action_patterns(db):
    """Creates sample user action patterns for the demo."""
    print("⚡ Creating sample process hotspots for demo...")
    if db.query(models.UserActionPattern).count() > 0:
        print("⚠️ Found existing action patterns. Skipping creation.")
        return

    patterns = [
        models.UserActionPattern(
            pattern_type="MANUAL_PO_CREATION",
            entity_name="Professional Services LLC",
            count=12,
            user_id=None,
        ),
        models.UserActionPattern(
            pattern_type="FREQUENT_PO_EDITS",
            entity_name="Standard Materials Corp",
            count=8,
            user_id=None,
        ),
    ]
    db.add_all(patterns)
    db.commit()
    print(f"✅ Created {len(patterns)} sample action patterns.")


# --- START MODIFICATION: Add function to create sample learned preferences ---
def create_sample_learned_preferences(db):
    """Creates sample learned preferences for the demo."""
    print("💡 Creating sample learned preferences for demo...")
    if db.query(models.LearnedPreference).count() > 0:
        print("⚠️ Found existing preferences. Skipping creation.")
        return

    admin_user = (
        db.query(models.User).filter(models.User.email == "admin@supervity.ai").first()
    )
    if not admin_user:
        print("⚠️ Admin user not found, cannot create sample preferences.")
        return

    preferences = [
        models.LearnedPreference(
            user_id=admin_user.id,
            preference_type="PREFERRED_VENDOR_CONTACT",
            context_key="Global Supplies Co",
            preference_value="billing.dept@globalsupplies.com",
        ),
        models.LearnedPreference(
            user_id=admin_user.id,
            preference_type="DEFAULT_GL_CODE",
            context_key="Professional Services LLC",
            preference_value="6310-Consulting",
        ),
    ]
    db.add_all(preferences)
    db.commit()
    print(f"✅ Created {len(preferences)} sample learned preferences.")


# --- END MODIFICATION ---
# --- END: New Functions for Demo Data ---


def main():
    print("🚀 INITIALIZING SAMPLE CONFIGURATION DATA")
    print("=" * 50)
    db = SessionLocal()
    try:
        create_roles(db)
        create_default_admin(db)
        create_default_demo_user(db)
        # --- START: Call new demo data functions ---
        create_sample_learned_heuristics(db)
        create_sample_action_patterns(db)
        # --- START MODIFICATION: Call the new function ---
        create_sample_learned_preferences(db)
        # --- END MODIFICATION ---
        # --- END: Call new demo data functions ---
    finally:
        db.close()

    create_sample_automation_rules()
    create_extraction_field_configurations()
    create_sample_slas()

    print("=" * 50)
    print("✅ CONFIGURATION DATA INITIALIZATION COMPLETE!")
    print("\n💡 You can now:")
    print("1. Start the backend: python run.py")
    print("2. Start the frontend and log in")
    print("3. Navigate to the AI Insights page to see pre-populated data.")


if __name__ == "__main__":
    main()

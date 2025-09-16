#!/usr/bin/env python3
"""
Database cleanup script to remove all data and start fresh.
"""

import os
import sys
from sqlalchemy import text

# Add both the project root and src directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_dir = os.path.join(project_root, "src")
sys.path.insert(0, project_root)
sys.path.insert(0, src_dir)

# CORRECTED IMPORTS
from app.db.session import (
    SessionLocal,
    engine,
    database_exists,
    ensure_database_exists,
    create_db_and_tables,
)
from app.db import models


def cleanup_database():
    """Remove all data from the database."""
    print("🧹 Cleaning up database...")

    # Check if database exists first
    if not database_exists():
        print("⚠️ Database doesn't exist or has no tables. Creating fresh database...")
        ensure_database_exists()
        create_db_and_tables()
        print("✅ Fresh database created successfully!")
        return

    db = SessionLocal()
    try:
        # Delete all data from tables in correct order (respecting foreign keys)
        print("Deleting data from tables...")

        # Check if tables exist before trying to delete from them
        # Order is important: delete from most dependent tables first
        tables_to_clean = [
            # Tables that depend on invoices/users/etc (most dependent)
            "comments",
            "audit_logs",
            "notifications",
            "learned_preferences",
            "user_action_patterns",
            "permission_policies",
            "failed_ingestions",
            # Association tables (many-to-many relationships)
            "invoice_po_association",
            "invoice_grn_association",
            # Main entity tables
            "invoices",
            "goods_receipt_notes",
            "purchase_orders",
            # Configuration and learning tables
            "learned_heuristics",
            "vendor_settings",
            "automation_rules",
            "slas",
            "extraction_field_configurations",
            # User management tables (delete in dependency order)
            "users",  # Delete users before roles (users have foreign key to roles)
            "roles",
            # Jobs table (least dependent)
            "jobs",
        ]

        for table in tables_to_clean:
            try:
                db.execute(text(f"DELETE FROM {table}"))
                print(f"✅ Cleaned table: {table}")
            except Exception as e:
                print(f"⚠️ Could not clean table {table}: {e}")

        db.commit()
        print("✅ Database cleaned successfully!")

        # Show counts for main entity tables
        try:
            invoice_count = db.query(models.Invoice).count()
            grn_count = db.query(models.GoodsReceiptNote).count()
            po_count = db.query(models.PurchaseOrder).count()
            job_count = db.query(models.Job).count()
            user_count = db.query(models.User).count()
            role_count = db.query(models.Role).count()
            automation_rule_count = db.query(models.AutomationRule).count()
            vendor_setting_count = db.query(models.VendorSetting).count()

            print(f"📊 Current counts after cleanup:")
            print(f"   • Jobs: {job_count}")
            print(f"   • Users: {user_count}, Roles: {role_count}")
            print(f"   • POs: {po_count}, GRNs: {grn_count}, Invoices: {invoice_count}")
            print(f"   • Automation Rules: {automation_rule_count}")
            print(f"   • Vendor Settings: {vendor_setting_count}")

        except Exception as e:
            print(f"⚠️ Could not get counts: {e}")

    except Exception as e:
        print(f"❌ Error cleaning database: {e}")
        db.rollback()
    finally:
        db.close()


def reset_database():
    """Drop and recreate all tables."""
    print("🔄 Resetting database schema...")

    try:
        # Ensure database exists first
        ensure_database_exists()

        # Check if tables exist before trying to drop them
        if database_exists():
            print("📝 Dropping existing tables...")
            models.Base.metadata.drop_all(bind=engine)
            print("✅ Dropped all tables.")
        else:
            print("📝 No existing tables found.")

        # Create all tables
        print("📝 Creating all tables...")
        models.Base.metadata.create_all(bind=engine)
        print("✅ Recreated all tables.")

        print("📊 Database schema includes the following tables:")
        table_names = sorted(
            [
                "roles",
                "users",
                "permission_policies",
                "jobs",
                "invoices",
                "purchase_orders",
                "goods_receipt_notes",
                "comments",
                "audit_logs",
                "notifications",
                "learned_heuristics",
                "automation_rules",
                "slas",
                "vendor_settings",
                "user_action_patterns",
                "learned_preferences",
                "failed_ingestions",
                "extraction_field_configurations",
                "invoice_po_association",
                "invoice_grn_association",
            ]
        )
        for table in table_names:
            print(f"   • {table}")

    except Exception as e:
        print(f"❌ Error resetting database: {e}")
        raise


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        print("Running full database reset (drop and recreate tables)...")
        reset_database()
    else:
        print("Running database cleanup (deleting all data)...")
        cleanup_database()

    print("🚀 Database is ready for processing!")

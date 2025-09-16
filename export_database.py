#!/usr/bin/env python3
"""
Database Export Script
Exports all tables from the database (SQLite or PostgreSQL) to CSV and JSON formats
"""

import pandas as pd
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

# Add the src directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))
src_dir = os.path.join(project_root, "src")
sys.path.insert(0, project_root)
sys.path.insert(0, src_dir)

# Import app modules
from app.db.session import SessionLocal, engine
from app.config import settings


def get_database_info():
    """Get database connection information"""
    db_url = str(engine.url)
    dialect = engine.dialect.name

    if dialect == "postgresql":
        db_type = "PostgreSQL"
        db_identifier = f"{engine.url.host}:{engine.url.port}/{engine.url.database}"
    elif dialect == "sqlite":
        db_type = "SQLite"
        db_identifier = engine.url.database or "in-memory"
    else:
        db_type = dialect.upper()
        db_identifier = str(engine.url)

    return {
        "type": db_type,
        "dialect": dialect,
        "identifier": db_identifier,
        "url_safe": db_url.replace(
            str(engine.url.password) if engine.url.password else "", "***"
        ),
    }


def get_table_names():
    """Get all table names from the database"""
    inspector = inspect(engine)
    return inspector.get_table_names()


def export_database_to_csv_and_json(output_dir="database_export"):
    """Export all tables from the database to CSV and JSON files"""

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Create subdirectories
    csv_dir = output_path / "csv"
    json_dir = output_path / "json"
    csv_dir.mkdir(exist_ok=True)
    json_dir.mkdir(exist_ok=True)

    try:
        # Get database info
        db_info = get_database_info()
        print(f"🗄️  Database Type: {db_info['type']}")
        print(f"🔗 Connection: {db_info['identifier']}")

        # Get all table names
        tables = get_table_names()

        if not tables:
            print("❌ No tables found in the database!")
            return

        print(f"📊 Found {len(tables)} tables in the database")
        print(f"📁 Exporting to: {output_path.absolute()}")
        print()

        # Export summary
        export_summary = {
            "export_timestamp": datetime.now().isoformat(),
            "database_info": db_info,
            "tables_exported": [],
            "total_records": 0,
        }

        # Create database session
        db = SessionLocal()

        try:
            # Export each table
            for table_name in tables:
                try:
                    print(f"📋 Exporting table: {table_name}")

                    # Read table into pandas DataFrame using SQLAlchemy
                    query = text(f"SELECT * FROM {table_name}")
                    df = pd.read_sql_query(query, engine)

                    if df.empty:
                        print(f"   ⚠️  Table {table_name} is empty")
                        # Still add to summary even if empty
                        table_info = {
                            "table_name": table_name,
                            "record_count": 0,
                            "columns": [],
                            "csv_file": None,
                            "json_file": None,
                        }
                        export_summary["tables_exported"].append(table_info)
                        continue

                    # Export to CSV
                    csv_file = csv_dir / f"{table_name}.csv"
                    df.to_csv(csv_file, index=False)

                    # Export to JSON
                    json_file = json_dir / f"{table_name}.json"
                    # Convert DataFrame to dict and handle datetime/date objects
                    records = df.to_dict("records")
                    with open(json_file, "w", encoding="utf-8") as f:
                        json.dump(records, f, indent=2, default=str, ensure_ascii=False)

                    record_count = len(df)
                    print(f"   ✅ Exported {record_count} records")

                    # Add to summary
                    table_info = {
                        "table_name": table_name,
                        "record_count": record_count,
                        "columns": list(df.columns),
                        "csv_file": str(csv_file.name),
                        "json_file": str(json_file.name),
                    }
                    export_summary["tables_exported"].append(table_info)
                    export_summary["total_records"] += record_count

                except Exception as e:
                    print(f"   ❌ Error exporting table {table_name}: {e}")
                    # Add error to summary
                    table_info = {
                        "table_name": table_name,
                        "record_count": 0,
                        "columns": [],
                        "csv_file": None,
                        "json_file": None,
                        "error": str(e),
                    }
                    export_summary["tables_exported"].append(table_info)

        finally:
            db.close()

        # Save export summary
        summary_file = output_path / "export_summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(export_summary, f, indent=2, default=str, ensure_ascii=False)

        print()
        print("🎉 Export completed successfully!")
        print(f"📊 Total records exported: {export_summary['total_records']}")
        print(f"📁 Files saved in: {output_path.absolute()}")
        print(f"📋 Export summary: {summary_file}")

        # Show directory structure
        print("\n📂 Export structure:")
        for root, dirs, files in os.walk(output_path):
            level = root.replace(str(output_path), "").count(os.sep)
            indent = " " * 2 * level
            print(f"{indent}{os.path.basename(root)}/")
            subindent = " " * 2 * (level + 1)
            for file in files:
                print(f"{subindent}{file}")

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        raise


def create_master_file(output_dir="database_export"):
    """Create a single master file combining all database tables"""

    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    try:
        print("🔄 Creating master database export file...")

        # Get database info
        db_info = get_database_info()
        print(f"🗄️  Database Type: {db_info['type']}")
        print(f"🔗 Connection: {db_info['identifier']}")

        # Get all table names
        tables = get_table_names()

        if not tables:
            print("❌ No tables found in the database!")
            return

        # Master data structure
        master_data = {
            "export_info": {
                "export_timestamp": datetime.now().isoformat(),
                "database_info": db_info,
                "total_tables": len(tables),
                "export_type": "complete_database_dump",
            },
            "database": {},
        }

        total_records = 0

        # Create database session
        db = SessionLocal()

        try:
            # Export each table to master structure
            for table_name in tables:
                try:
                    print(f"  📋 Processing table: {table_name}")

                    # Read table into pandas DataFrame using SQLAlchemy
                    query = text(f"SELECT * FROM {table_name}")
                    df = pd.read_sql_query(query, engine)

                    if df.empty:
                        print(f"     ⚠️  Table {table_name} is empty")
                        master_data["database"][table_name] = {
                            "record_count": 0,
                            "columns": [],
                            "data": [],
                        }
                        continue

                    # Convert to records
                    records = df.to_dict("records")
                    record_count = len(records)
                    total_records += record_count

                    # Add to master structure
                    master_data["database"][table_name] = {
                        "record_count": record_count,
                        "columns": list(df.columns),
                        "data": records,
                    }

                    print(f"     ✅ Added {record_count} records")

                except Exception as e:
                    print(f"     ❌ Error processing table {table_name}: {e}")
                    master_data["database"][table_name] = {
                        "error": str(e),
                        "record_count": 0,
                        "columns": [],
                        "data": [],
                    }

        finally:
            db.close()

        # Update total records
        master_data["export_info"]["total_records"] = total_records

        # Save master JSON file
        master_json_file = output_path / "ap_database_master.json"
        with open(master_json_file, "w", encoding="utf-8") as f:
            json.dump(master_data, f, indent=2, default=str, ensure_ascii=False)

        # Create master CSV with summary
        master_csv_data = []
        for table_name, table_info in master_data["database"].items():
            if table_info["record_count"] > 0:
                for record in table_info["data"]:
                    # Add table source to each record
                    record_with_source = {"table_source": table_name, **record}
                    master_csv_data.append(record_with_source)

        master_csv_file = None
        if master_csv_data:
            master_csv_file = output_path / "ap_database_master.csv"
            master_df = pd.DataFrame(master_csv_data)
            master_df.to_csv(master_csv_file, index=False)
            print(f"📄 Master CSV created: {master_csv_file}")

        # Create readable summary file
        summary_file = output_path / "database_summary.txt"
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write("AP DATABASE EXPORT SUMMARY\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Export Date: {master_data['export_info']['export_timestamp']}\n")
            f.write(f"Database Type: {db_info['type']}\n")
            f.write(f"Database: {db_info['identifier']}\n")
            f.write(f"Total Tables: {len(tables)}\n")
            f.write(f"Total Records: {total_records}\n\n")

            f.write("TABLE BREAKDOWN:\n")
            f.write("-" * 30 + "\n")
            for table_name, table_info in master_data["database"].items():
                f.write(f"{table_name:30} | {table_info['record_count']:5} records\n")

            f.write("\nKEY INSIGHTS:\n")
            f.write("-" * 30 + "\n")
            invoices = (
                master_data["database"].get("invoices", {}).get("record_count", 0)
            )
            pos = (
                master_data["database"]
                .get("purchase_orders", {})
                .get("record_count", 0)
            )
            grns = (
                master_data["database"]
                .get("goods_receipt_notes", {})
                .get("record_count", 0)
            )
            po_assoc = (
                master_data["database"]
                .get("invoice_po_association", {})
                .get("record_count", 0)
            )
            grn_assoc = (
                master_data["database"]
                .get("invoice_grn_association", {})
                .get("record_count", 0)
            )

            f.write(f"• {invoices} invoices in the system\n")
            f.write(f"• {pos} purchase orders available\n")
            f.write(f"• {grns} goods receipt notes available\n")
            f.write(f"• {po_assoc} invoice-PO associations (linking status)\n")
            f.write(f"• {grn_assoc} invoice-GRN associations (linking status)\n")

            if po_assoc == 0 and grn_assoc == 0:
                f.write(
                    "\n⚠️  WARNING: No associations found - documents are not linked!\n"
                )

        print(f"\n🎉 Master file created successfully!")
        print(f"📄 JSON Master File: {master_json_file}")
        print(
            f"📄 CSV Master File: {master_csv_file if master_csv_data else 'Not created (no data)'}"
        )
        print(f"📄 Summary File: {summary_file}")
        print(f"📊 Total records in master file: {total_records}")

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        raise


def show_database_info():
    """Show basic information about the database"""
    try:
        # Get database info
        db_info = get_database_info()

        # Get all table names
        tables = get_table_names()

        print(f"📊 Database Type: {db_info['type']}")
        print(f"🔗 Connection: {db_info['identifier']}")
        print(f"📋 Tables ({len(tables)}):")

        # Create database session
        db = SessionLocal()

        try:
            total_records = 0
            for table_name in tables:
                try:
                    # Get record count for each table
                    query = text(f"SELECT COUNT(*) FROM {table_name}")
                    result = db.execute(query)
                    count = result.scalar()
                    total_records += count
                    print(f"   • {table_name}: {count} records")
                except Exception as e:
                    print(f"   • {table_name}: Error counting records - {e}")

            print(f"📈 Total records: {total_records}")

        finally:
            db.close()

    except Exception as e:
        print(f"❌ Database error: {e}")


if __name__ == "__main__":
    print("🗄️  AP Database Export Tool")
    print("=" * 50)

    try:
        # Show database info first
        show_database_info()
        print()

        # Ask user for export preference
        print("Export Options:")
        print("1. Individual table files (CSV + JSON)")
        print("2. Single master file")
        print("3. Both")

        choice = input("Choose export type (1/2/3): ").strip()

        if choice == "1":
            export_database_to_csv_and_json()
        elif choice == "2":
            create_master_file()
        elif choice == "3":
            export_database_to_csv_and_json()
            print("\n" + "=" * 50)
            create_master_file()
        else:
            print("Invalid choice. Exporting master file by default...")
            create_master_file()

    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)

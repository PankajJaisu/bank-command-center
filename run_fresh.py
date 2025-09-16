#!/usr/bin/env python3
"""
Fresh start script for the Supervity Proactive Loan Command Center.
This script:
1. Checks if database exists and creates it if needed
2. Clears existing data (if any)
3. Initializes configuration data
4. Starts the application server

Usage:
    python run_fresh.py [--reset]
    
Options:
    --reset    Perform a full database reset (drop and recreate tables)
"""

import os
import sys
import subprocess
import time

# Add src directory to Python path for imports
project_root = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(project_root, "src")
sys.path.insert(0, src_dir)


def run_script(script_path, args=None):
    """Run a Python script and wait for it to complete."""
    cmd = [sys.executable, script_path]
    if args:
        cmd.extend(args)

    print(f"🔧 Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False)
    if result.returncode != 0:
        print(f"❌ Script failed with return code {result.returncode}")
        sys.exit(1)
    print(f"✅ Completed: {script_path}")


def check_database_status():
    """Check and report database status."""
    try:
        from app.db.session import (
            database_exists,
            is_sqlite_database,
            is_postgresql_database,
            SQLALCHEMY_DATABASE_URL,
        )

        if is_sqlite_database():
            db_type = "SQLite"
            db_path = SQLALCHEMY_DATABASE_URL.replace("sqlite:///", "")
        elif is_postgresql_database():
            db_type = "PostgreSQL"
            db_path = SQLALCHEMY_DATABASE_URL
        else:
            db_type = "Unknown"
            db_path = SQLALCHEMY_DATABASE_URL

        print(f"🗄️ Database Type: {db_type}")
        print(f"🗄️ Database URL: {db_path}")

        exists = database_exists()
        print(f"🗄️ Database Exists: {'Yes' if exists else 'No'}")

        return exists

    except Exception as e:
        print(f"⚠️ Could not check database status: {e}")
        return False


def main():
    """Main function to orchestrate the fresh start process."""
    print("🚀 SUPERVITY Proactive Loan Command Center - FRESH START")
    print("=" * 50)
    print("This will:")
    print("1. Check database status")
    print("2. Clean/reset the database")
    print("3. Initialize configuration data")
    print("4. Start the application server")
    print("=" * 50)

    # Check database status first
    print("\n📝 STEP 0: Database Status Check")
    print("-" * 30)
    db_exists = check_database_status()

    # Get the project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))

    # Define script paths
    cleanup_script = os.path.join(project_root, "scripts", "cleanup_db.py")
    init_config_script = os.path.join(project_root, "scripts", "init_config_data.py")
    run_script_path = os.path.join(project_root, "run.py")

    # Check if --reset flag is passed
    reset_args = []
    if "--reset" in sys.argv:
        reset_args = ["--reset"]
        print("⚠️ Full database reset mode enabled")

    try:
        # Step 1: Clean/Reset the database
        print("\n📝 STEP 1: Database Cleanup/Creation")
        print("-" * 30)
        if not db_exists and not reset_args:
            print("📝 Database doesn't exist - will be created during cleanup")
        elif reset_args:
            print("📝 Performing full database reset...")
        else:
            print("📝 Database exists - cleaning existing data...")

        run_script(cleanup_script, reset_args)

        # Step 2: Initialize configuration data
        print("\n📝 STEP 2: Initialize Configuration")
        print("-" * 30)
        run_script(init_config_script)

        # Step 3: Start the application
        print("\n📝 STEP 3: Starting Application")
        print("-" * 30)
        print("🎉 Database is clean and configured!")
        print("🚀 Starting the Supervity Proactive Loan Command Center server...")
        print("\n" + "=" * 50)

        # Run the main application server as a managed subprocess
        # This allows the run_fresh script to remain in control and catch interrupts
        server_process = subprocess.Popen([sys.executable, run_script_path])
        server_process.wait()  # Wait for the server process to terminate

    except KeyboardInterrupt:
        print("\n\n⚠️ Process interrupted by user. Shutting down server...")
        if "server_process" in locals() and server_process.poll() is None:
            server_process.terminate()
            server_process.wait()
        print("✅ Server shut down gracefully.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error during fresh start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

# src/app/main.py
import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.session import create_db_and_tables, SessionLocal
from app.db import models
from app.modules.auth.password_service import get_password_hash

# --- ADD AI AP MANAGER TO IMPORTS ---
from app.api.endpoints import (
    documents,
    dashboard,
    invoices,
    copilot,
    learning,
    notifications,
    configuration,
    workflow,
    payments,
    auth,
    users,
    collection,
    ai_suggestions,
)
from app.core.monitoring_service import run_monitoring_cycle, check_held_invoices
from app.modules.automation import executor as automation_executor

# --- ADDED: Import the new learning engine ---
from app.modules.learning import engine as learning_engine
from app.config import settings
from app.utils.logging import setup_logging, get_logger

# --- ADDED: Import the policy scheduler ---
from app.services.policy_scheduler_service import start_policy_scheduler, stop_policy_scheduler

# Initialize logging first
setup_logging(
    level=os.getenv("LOG_LEVEL", "INFO"),
    log_file=os.getenv("LOG_FILE", None),
    console_colors=True,
)
logger = get_logger(__name__)


# --- DIRECTORY INITIALIZATION FUNCTION ---
def ensure_application_directories():
    """Ensure all required application directories exist on startup."""
    directories = [
        settings.pdf_storage_path,
        settings.generated_pdf_storage_path,
        "generated_documents",  # Additional fallback
    ]

    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
            logger.info(f"Directory ensured: {directory}")
        except OSError as e:
            logger.error(f"Could not create directory {directory}: {e}")


# --- STARTUP CONFIGURATION FUNCTIONS ---
def create_roles(db):
    """Create default user roles if they don't exist."""
    logger.info("👥 Checking for user roles...")
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
        logger.info(f"✅ Created {created_count} user roles.")
    else:
        logger.info("  -> All default roles already exist.")


def create_default_admin(db):
    """Create default admin user if it doesn't exist."""
    logger.info("🔐 Checking for default admin user...")
    admin_email = "admin@supervity.ai"
    admin_role = db.query(models.Role).filter(models.Role.name == "admin").first()
    if not admin_role:
        logger.warning("  -> Admin role not found. Cannot create admin user.")
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
        logger.info(f"  -> ✅ Created default admin user: {admin_email}")
    else:
        logger.info("  -> Default admin user already exists.")


def create_default_demo_user(db):
    """Create default demo user if it doesn't exist."""
    logger.info("👤 Checking for default demo user...")
    demo_email = "demo@supervity.ai"
    processor_role = (
        db.query(models.Role).filter(models.Role.name == "ap_processor").first()
    )
    if not processor_role:
        logger.warning("  -> AP Processor role not found. Cannot create demo user.")
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

        # Create permission policies for demo user
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
        logger.info(f"  -> ✅ Created default demo user: {demo_email}")
    else:
        logger.info("  -> Default demo user already exists.")


def create_sample_automation_rules(db):
    """Create sample automation rules if they don't exist."""
    logger.info("🤖 Creating sample automation rules...")
    try:
        if db.query(models.AutomationRule).count() > 0:
            logger.info("⚠️ Found existing automation rules. Skipping creation.")
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
        logger.info(f"✅ Created {len(sample_rules)} automation rules.")
    except Exception as e:
        logger.error(f"❌ Error creating automation rules: {e}")
        db.rollback()


def create_extraction_field_configurations(db):
    """Create default extraction field configurations if they don't exist."""
    logger.info("📝 Creating default extraction field configurations...")
    try:
        if db.query(models.ExtractionFieldConfiguration).count() > 0:
            logger.info("⚠️ Found existing field configurations. Skipping creation.")
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
        logger.info("✅ Created default field configurations.")
    except Exception as e:
        logger.error(f"❌ Error creating field configurations: {e}")
        db.rollback()


def create_sample_slas(db):
    """Create sample SLA policies if they don't exist."""
    logger.info("🕒 Creating sample SLA policies...")
    try:
        if db.query(models.SLA).count() > 0:
            logger.info("⚠️ Found existing SLA policies. Skipping creation.")
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
        logger.info(f"✅ Created {len(sample_slas)} sample SLA policies.")
    except Exception as e:
        logger.error(f"❌ Error creating sample SLAs: {e}")
        db.rollback()


def create_sample_learned_heuristics(db):
    """Create sample learned heuristics for the demo."""
    logger.info("🧠 Creating sample learned heuristics for demo...")
    if db.query(models.LearnedHeuristic).count() > 0:
        logger.info("⚠️ Found existing heuristics. Skipping creation.")
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
    logger.info(f"✅ Created {len(heuristics)} sample learned heuristics.")


def create_sample_action_patterns(db):
    """Create sample user action patterns for the demo."""
    logger.info("⚡ Creating sample process hotspots for demo...")
    if db.query(models.UserActionPattern).count() > 0:
        logger.info("⚠️ Found existing action patterns. Skipping creation.")
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
    logger.info(f"✅ Created {len(patterns)} sample action patterns.")


def create_sample_learned_preferences(db):
    """Create sample learned preferences for the demo."""
    logger.info("💡 Creating sample learned preferences for demo...")
    if db.query(models.LearnedPreference).count() > 0:
        logger.info("⚠️ Found existing preferences. Skipping creation.")
        return

    admin_user = (
        db.query(models.User).filter(models.User.email == "admin@supervity.ai").first()
    )
    if not admin_user:
        logger.warning("⚠️ Admin user not found, cannot create sample preferences.")
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
    logger.info(f"✅ Created {len(preferences)} sample learned preferences.")


def initialize_startup_configuration():
    """Initialize all startup configuration data."""
    logger.info("🚀 INITIALIZING STARTUP CONFIGURATION DATA")
    logger.info("=" * 50)

    try:
        with SessionLocal() as db:
            # Create roles and users
            create_roles(db)
            create_default_admin(db)
            create_default_demo_user(db)

            # Create sample data for demo
            create_sample_learned_heuristics(db)
            create_sample_action_patterns(db)
            create_sample_learned_preferences(db)

            # Create configuration data
            create_sample_automation_rules(db)
            create_extraction_field_configurations(db)
            create_sample_slas(db)

        logger.info("=" * 50)
        logger.info("✅ STARTUP CONFIGURATION INITIALIZATION COMPLETE!")

    except Exception as e:
        logger.error(
            f"❌ Error during startup configuration initialization: {e}", exc_info=True
        )


# --- NEW LIFESPAN MANAGER ---
async def recurring_background_tasks():
    """Wrapper to run all recurring services on a schedule."""
    task_logger = get_logger("app.background_tasks")

    while True:
        try:
            task_logger.debug("Starting recurring background tasks cycle")
            # Use consistent session management for all services
            with SessionLocal() as db:
                # Check for expired holds
                check_held_invoices(db)

                # Proactive Monitoring (runs every hour)
                run_monitoring_cycle(db)

                # Automation Engine (runs every 5 minutes)
                automation_executor.run_automation_engine(db)

                # --- ADDED: Run the new insight engine ---
                # This will analyze past events to generate learnings.
                learning_engine.run_analysis_cycle(db)
                # --- END ADDED ---

        except Exception as e:
            task_logger.error(
                f"Error in recurring background tasks: {e}", exc_info=True
            )
        # Let's run this more frequently, e.g., every 5 minutes (300 seconds)
        await asyncio.sleep(300)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup
    logger.info("🚀 Application starting up...")

    # Ensure directories exist
    ensure_application_directories()

    # Initialize database
    logger.info("📝 Creating database tables...")
    create_db_and_tables()
    logger.info("✅ Database tables created successfully")

    # Initialize startup configuration data
    initialize_startup_configuration()

    # Start the background tasks
    logger.info("🔄 Starting background task scheduler...")
    task = asyncio.create_task(recurring_background_tasks())
    
    # Start the AI Policy Agent scheduler
    logger.info("🤖 Starting AI Policy Agent scheduler...")
    policy_scheduler = start_policy_scheduler(interval_minutes=0.5)  # Run every 30 seconds
    logger.info("✅ AI Policy Agent scheduler started - will run automatically every 30 seconds")

    yield

    # On shutdown
    logger.info("👋 Application shutting down...")
    
    # Stop the policy scheduler
    logger.info("🛑 Stopping AI Policy Agent scheduler...")
    stop_policy_scheduler()
    
    # Stop background tasks
    task.cancel()
    try:
        await task
        logger.info("Background tasks successfully cancelled")
    except asyncio.CancelledError:
        logger.info("Background tasks cancelled during shutdown")


# --- MODIFIED APP INITIALIZATION ---
app = FastAPI(
    title="Supervity Proactive Loan Command Center API",  # <-- RENAMED
    description="The backend API for the Supervity AI-powered Accounts Payable Command Center.",
    version="2.0.0",  # Version bump for new release
    lifespan=lifespan,  # Use the new lifespan manager
)

# Configure CORS - make origins configurable for Kubernetes deployment
# Fix potential issue with single URL (no comma splitting needed)
cors_origins_env = os.getenv("CORS_ORIGINS", "")
if cors_origins_env and "," in cors_origins_env:
    cors_origins = [
        origin.strip() for origin in cors_origins_env.split(",") if origin.strip()
    ]
elif cors_origins_env:
    cors_origins = [cors_origins_env.strip()]
else:
    # Default development origins - covers common frontend ports and Docker networking
    cors_origins = [
        "http://localhost:3000",
        "http://localhost:3001", 
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://0.0.0.0:3000",
        "http://0.0.0.0:3001",
        # Add Docker and containerized environment support
        "http://supervity_frontend:3000",
        "http://frontend:3000",
        # Also allow any localhost for development
        "http://localhost",
        "http://127.0.0.1"
    ]

logger.info(f"🌐 CORS origins configured: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["User Management"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents & Jobs"])
app.include_router(invoices.router, prefix="/api/invoices", tags=["Invoices"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(
    copilot.router, prefix="/api/copilot", tags=["AI AP Manager"]
)  # <-- RENAMED TAG
app.include_router(
    learning.router, prefix="/api/learning", tags=["Learning & Heuristics"]
)
app.include_router(
    notifications.router, prefix="/api/notifications", tags=["Notifications"]
)
app.include_router(
    configuration.router, prefix="/api/config", tags=["Configuration & Settings"]
)  # <-- RENAMED TAG
app.include_router(workflow.router, prefix="/api/workflow", tags=["Workflow & Audit"])
app.include_router(payments.router, prefix="/api/payments", tags=["Payments"])
app.include_router(collection.router, prefix="/api/collection", tags=["Collection Cell"])
app.include_router(ai_suggestions.router, prefix="/api/ai-suggestions", tags=["AI Suggestions"])


@app.get("/api/health", tags=["Health Check"])
def health_check():
    return {"status": "ok"}

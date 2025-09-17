# src/app/main.py
import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.session import create_db_and_tables, SessionLocal
from app.db import models
from app.modules.auth.password_service import get_password_hash

# --- COLLECTION MANAGER IMPORTS ---
from app.api.endpoints import (
    dashboard,
    copilot,
    learning,
    notifications,
    configuration,
    auth,
    users,
    collection,
)
# Remove AP-specific monitoring and automation

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
    roles_to_create = ["admin", "collection_agent"]
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
        db.query(models.Role).filter(models.Role.name == "collection_agent").first()
    )
    if not processor_role:
        logger.warning("  -> Collection Agent role not found. Cannot create demo user.")
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

        # Create permission policies for demo user (collection-focused)
        policies = [
            models.PermissionPolicy(
                user_id=new_demo_user.id,
                name="Access High-Risk Customers",
                conditions={
                    "logical_operator": "AND",
                    "conditions": [
                        {
                            "field": "cbs_risk_level",
                            "operator": "equals",
                            "value": "red",
                        },
                    ],
                },
                is_active=True,
            ),
            models.PermissionPolicy(
                user_id=new_demo_user.id,
                name="Access Medium-Risk Customers",
                conditions={
                    "logical_operator": "AND",
                    "conditions": [
                        {
                            "field": "cbs_risk_level",
                            "operator": "equals",
                            "value": "amber",
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


# Removed AP-specific automation rules


# Removed AP-specific extraction field configurations


# Removed AP-specific SLA policies


# Removed AP-specific learned heuristics


# Removed AP-specific action patterns


# Removed AP-specific learned preferences


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

        logger.info("=" * 50)
        logger.info("✅ STARTUP CONFIGURATION INITIALIZATION COMPLETE!")

    except Exception as e:
        logger.error(
            f"❌ Error during startup configuration initialization: {e}", exc_info=True
        )


# --- NEW LIFESPAN MANAGER ---
async def recurring_background_tasks():
    """Wrapper to run collection-related background services."""
    task_logger = get_logger("app.background_tasks")

    while True:
        try:
            task_logger.debug("Starting collection background tasks cycle")
            # Use consistent session management for all services
            with SessionLocal() as db:
                # Run collection-specific learning engine
                learning_engine.run_analysis_cycle(db)

        except Exception as e:
            task_logger.error(
                f"Error in recurring background tasks: {e}", exc_info=True
            )
        # Run every 5 minutes (300 seconds)
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
    policy_scheduler = start_policy_scheduler(interval_minutes=settings.policy_agent_interval_minutes)
    logger.info(f"✅ AI Policy Agent scheduler started - will run automatically every {settings.policy_agent_interval_minutes} minutes")

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
    title="Supervity Bank Collection Management API",
    description="The backend API for the Supervity AI-powered Bank Collection and Loan Management System.",
    version="2.0.0",
    lifespan=lifespan,
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

# Include API routers - Collection Management focused
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["User Management"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(
    copilot.router, prefix="/api/copilot", tags=["AI Collection Manager"]
)
app.include_router(
    learning.router, prefix="/api/learning", tags=["Learning & Heuristics"]
)
app.include_router(
    notifications.router, prefix="/api/notifications", tags=["Notifications"]
)
app.include_router(
    configuration.router, prefix="/api/config", tags=["Configuration & Settings"]
)
# Add documents router for backward compatibility
app.include_router(
    configuration.router, prefix="/api/documents", tags=["Document Management"]
)
app.include_router(collection.router, prefix="/api/collection", tags=["Collection Management"])


@app.get("/api/health", tags=["Health Check"])
def health_check():
    return {"status": "ok"}

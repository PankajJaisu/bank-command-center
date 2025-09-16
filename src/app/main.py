"""
Main FastAPI application for the Bank Command Center.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Bank Command Center API",
    description="API for bank loan collection and monitoring system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Bank Command Center API is starting up...")
    logger.info(f"Environment: {settings.app_env}")
    logger.info("✅ Startup complete!")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 Bank Command Center API is shutting down...")

# Configure CORS
origins = [origin.strip() for origin in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    print("📍 Root endpoint called")
    return {
        "message": "Bank Command Center API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint for monitoring."""
    print("📍 Health check endpoint called")
    return {
        "status": "healthy",
        "service": "bank-command-center",
        "environment": settings.app_env
    }


# Include API routers here when they are created
# from app.api.endpoints import auth, customers, loans
# app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
# app.include_router(customers.router, prefix="/api/customers", tags=["customers"])
# app.include_router(loans.router, prefix="/api/loans", tags=["loans"])

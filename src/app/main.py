"""
Main FastAPI application for the Bank Command Center.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

# Create FastAPI application
app = FastAPI(
    title="Bank Command Center API",
    description="API for bank loan collection and monitoring system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

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
    return {
        "message": "Bank Command Center API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint for monitoring."""
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

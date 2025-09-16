"""
SQLAlchemy database models for the Bank Command Center.
"""
from datetime import datetime, date
from typing import Optional
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, Boolean, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.db.session import Base


class ContractNote(Base):
    """Contract note model for storing contract document data."""
    __tablename__ = "contract_notes"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(500), nullable=False)
    file_path = Column(String(500), nullable=False)
    extracted_data = Column(JSON, nullable=True)
    
    # Contract terms
    contract_emi_amount = Column(Float, nullable=True)
    contract_due_day = Column(Integer, nullable=True)
    contract_late_fee_percent = Column(Float, nullable=True)
    contract_default_clause = Column(String(2000), nullable=True)
    contract_governing_law = Column(String(500), nullable=True)
    contract_interest_rate = Column(Float, nullable=True)
    contract_loan_amount = Column(Float, nullable=True)
    contract_tenure_months = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customers = relationship("Customer", back_populates="contract_note")


class Customer(Base):
    """Customer model for storing customer information."""
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    customer_no = Column(String(100), nullable=False, unique=True, index=True)
    name = Column(String(500), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(String(1000), nullable=True)
    
    # Contract note reference
    contract_note_id = Column(Integer, ForeignKey("contract_notes.id"), nullable=True)
    
    # CBS (Core Banking System) data
    cbs_emi_amount = Column(Float, nullable=True)
    cbs_due_day = Column(Integer, nullable=True)
    cbs_last_payment_date = Column(Date, nullable=True)
    cbs_outstanding_amount = Column(Float, nullable=True)
    cbs_risk_level = Column(String(20), nullable=True)
    cbs_income_verification = Column(String(50), nullable=True)
    
    # Additional customer fields (from migration 003)
    cibil_score = Column(Integer, nullable=True)
    days_since_employment = Column(Integer, nullable=True)
    employment_status = Column(String(50), nullable=True)
    salary_last_date = Column(Date, nullable=True)
    pending_amount = Column(Float, nullable=True)
    pendency = Column(String(50), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    contract_note = relationship("ContractNote", back_populates="customers")
    loans = relationship("Loan", back_populates="customer")
    data_integrity_alerts = relationship("DataIntegrityAlert", back_populates="customer")


class Loan(Base):
    """Loan model for storing loan information."""
    __tablename__ = "loans"

    id = Column(Integer, primary_key=True, index=True)
    loan_id = Column(String(100), nullable=False, unique=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    
    # Loan details
    loan_amount = Column(Float, nullable=True)
    emi_amount = Column(Float, nullable=True)
    tenure_months = Column(Integer, nullable=True)
    interest_rate = Column(Float, nullable=True)
    status = Column(String(50), nullable=True)
    outstanding_amount = Column(Float, nullable=True)
    
    # Payment dates
    last_payment_date = Column(Date, nullable=True)
    next_due_date = Column(Date, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customer = relationship("Customer", back_populates="loans")


class DataIntegrityAlert(Base):
    """Data integrity alert model for tracking data discrepancies."""
    __tablename__ = "data_integrity_alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_type = Column(String(100), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    severity = Column(String(20), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(String(2000), nullable=True)
    
    # Data comparison
    cbs_value = Column(String(500), nullable=True)
    contract_value = Column(String(500), nullable=True)
    
    # Resolution tracking
    is_resolved = Column(Boolean, default=False)
    resolved_by = Column(Integer, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customer = relationship("Customer", back_populates="data_integrity_alerts")


class AutomationRule(Base):
    """Automation rule model for policy and business rules."""
    __tablename__ = "automation_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)  # Added from migration aefd4c279334
    
    # Rule configuration (from migration 004)
    rule_level = Column(String, nullable=True)
    segment = Column(String, nullable=True)
    customer_id = Column(String, nullable=True)
    source_document = Column(String, nullable=True)
    status = Column(String, nullable=True, default='active')
    
    # Rule logic
    conditions = Column(JSON, nullable=True)
    actions = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

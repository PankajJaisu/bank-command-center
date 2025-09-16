# src/app/api/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session, joinedload
from jose import JWTError, jwt

from app.db.session import SessionLocal
from app.config import settings
from app.db import models, schemas

# This tells FastAPI where to look for the token (the /api/auth/login endpoint)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_db():
    """
    FastAPI dependency that provides a database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> models.User:
    """
    Decodes the JWT token to get the current user.
    This will be used as a dependency to protect endpoints.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.auth_secret_key, algorithms=[settings.auth_algorithm]
        )
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = schemas.TokenData(email=email)
    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.email == token_data.email).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    return user


def get_current_active_admin(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """
    A dependency that checks if the current user is an active admin.
    """
    if current_user.role.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user


def get_invoice_for_user(
    invoice_db_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> models.Invoice:
    """
    Dependency to get a specific invoice by database ID, ensuring the user has permission to access it.
    Prevents Insecure Direct Object Reference (IDOR) attacks.
    """
    invoice = (
        db.query(models.Invoice).filter(models.Invoice.id == invoice_db_id).first()
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if current_user.role.name == "ap_processor":
        # Get user's assigned vendors
        user_with_vendors = (
            db.query(models.User)
            .options(joinedload(models.User.assigned_vendors))
            .filter(models.User.id == current_user.id)
            .first()
        )

        if user_with_vendors and user_with_vendors.assigned_vendors:
            assigned_vendor_names = [
                v.vendor_name for v in user_with_vendors.assigned_vendors
            ]
            if invoice.vendor_name not in assigned_vendor_names:
                raise HTTPException(
                    status_code=403,
                    detail="You do not have permission to access this invoice.",
                )
        else:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to access this invoice.",
            )

    return invoice


def get_invoice_by_string_id_for_user(
    invoice_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> models.Invoice:
    """
    Dependency to get a specific invoice by string ID, ensuring the user has permission to access it.
    Prevents Insecure Direct Object Reference (IDOR) attacks.
    """
    invoice = (
        db.query(models.Invoice).filter(models.Invoice.invoice_id == invoice_id).first()
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if current_user.role.name == "ap_processor":
        # Get user's assigned vendors
        user_with_vendors = (
            db.query(models.User)
            .options(joinedload(models.User.assigned_vendors))
            .filter(models.User.id == current_user.id)
            .first()
        )

        if user_with_vendors and user_with_vendors.assigned_vendors:
            assigned_vendor_names = [
                v.vendor_name for v in user_with_vendors.assigned_vendors
            ]
            if invoice.vendor_name not in assigned_vendor_names:
                raise HTTPException(
                    status_code=403,
                    detail="You do not have permission to access this invoice.",
                )
        else:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to access this invoice.",
            )

    return invoice

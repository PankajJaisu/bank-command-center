# src/app/api/endpoints/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.db import models, schemas
from app.modules.auth import password_service, token_service

router = APIRouter()


@router.post(
    "/signup", response_model=schemas.User, status_code=status.HTTP_201_CREATED
)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # --- START MODIFICATION: Conditional Role & Approval ---
    is_supervity_user = user.email.endswith("@supervity.ai")

    if is_supervity_user:
        # For @supervity.ai users, assign 'admin' role and auto-approve.
        target_role_name = "admin"
        is_approved_status = True
    else:
        # For all other users, assign 'ap_processor' role and require admin approval.
        target_role_name = "ap_processor"
        is_approved_status = False

    # Fetch the target role from the database
    role = db.query(models.Role).filter(models.Role.name == target_role_name).first()
    if not role:
        raise HTTPException(
            status_code=500, detail=f"Default role '{target_role_name}' not found."
        )

    hashed_password = password_service.get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        role_id=role.id,
        is_approved=is_approved_status,
    )
    # --- END MODIFICATION ---

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.post("/login", response_model=schemas.Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active or not user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive or not yet approved by an administrator.",
        )
    if not password_service.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = token_service.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

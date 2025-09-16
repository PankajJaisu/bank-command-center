# src/app/api/endpoints/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List

from app.api.dependencies import get_db, get_current_active_admin, get_current_user
from app.db import models, schemas

router = APIRouter()


@router.get("/", response_model=List[schemas.UserWithVendors])
def read_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """
    Retrieve all users. Admin only.
    """
    users = (
        db.query(models.User)
        .options(
            joinedload(models.User.role), joinedload(models.User.permission_policies)
        )
        .offset(skip)
        .limit(limit)
        .all()
    )

    # Manually construct the response to include permission policies
    response_users = []
    for user in users:
        user_data = schemas.UserWithVendors(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_approved=user.is_approved,
            role=user.role,
            permission_policies=[
                schemas.PermissionPolicy(
                    id=p.id,
                    user_id=p.user_id,
                    name=p.name,
                    conditions=p.conditions,
                    is_active=p.is_active,
                )
                for p in user.permission_policies
            ],
        )
        response_users.append(user_data)

    return response_users


@router.post("/{user_id}/approve", response_model=schemas.User)
def approve_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """
    Approve a newly registered user. Admin only.
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_approved = True
    db.commit()
    db.refresh(user)
    return user


@router.put("/{user_id}/policies", response_model=schemas.UserWithVendors)
def update_user_policies(
    user_id: int,
    policies: List[schemas.PermissionPolicyCreate],
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """
    Replaces all permission policies for a given user. Admin only.
    """
    user = (
        db.query(models.User)
        .options(
            joinedload(models.User.permission_policies), joinedload(models.User.role)
        )
        .filter(models.User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Delete old policies
    db.query(models.PermissionPolicy).filter(
        models.PermissionPolicy.user_id == user_id
    ).delete()
    db.flush()  # Make sure the deletion is committed

    # Create and add new policies
    new_policies = [
        models.PermissionPolicy(user_id=user_id, **p.model_dump()) for p in policies
    ]
    db.add_all(new_policies)

    db.commit()
    db.refresh(user)

    # Manually construct the response object to match the Pydantic schema
    response_data = schemas.UserWithVendors(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_approved=user.is_approved,
        role=user.role,
        permission_policies=[
            schemas.PermissionPolicy(
                id=p.id,
                user_id=p.user_id,
                name=p.name,
                conditions=p.conditions,
                is_active=p.is_active,
            )
            for p in user.permission_policies
        ],
    )
    return response_data


@router.get("/me", response_model=schemas.UserWithVendors)
def read_users_me(
    current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Get current user's details.
    """
    user = (
        db.query(models.User)
        .options(
            joinedload(models.User.role), joinedload(models.User.permission_policies)
        )
        .filter(models.User.id == current_user.id)
        .first()
    )

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Manually construct the response object to match the Pydantic schema
    response_data = schemas.UserWithVendors(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_approved=user.is_approved,
        role=user.role,
        permission_policies=[
            schemas.PermissionPolicy(
                id=p.id,
                user_id=p.user_id,
                name=p.name,
                conditions=p.conditions,
                is_active=p.is_active,
            )
            for p in user.permission_policies
        ],
    )
    return response_data


@router.put("/{user_id}/role", response_model=schemas.UserWithVendors)
def update_user_role(
    user_id: int,
    role_update: schemas.UserRoleUpdate,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """
    Updates a user's role. Admin only.
    """
    if user_id == admin_user.id:
        raise HTTPException(
            status_code=400, detail="Admins cannot change their own role."
        )

    # Validate role name
    if role_update.role_name not in ["admin", "ap_processor"]:
        raise HTTPException(
            status_code=400, detail=f"Invalid role name: {role_update.role_name}"
        )

    user = (
        db.query(models.User)
        .options(
            joinedload(models.User.role), joinedload(models.User.permission_policies)
        )
        .filter(models.User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_role = (
        db.query(models.Role).filter(models.Role.name == role_update.role_name).first()
    )
    if not new_role:
        raise HTTPException(
            status_code=404, detail=f"Role '{role_update.role_name}' not found"
        )

    user.role_id = new_role.id
    db.commit()
    db.refresh(user)

    # Manually construct the response object to match the Pydantic schema
    response_data = schemas.UserWithVendors(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_approved=user.is_approved,
        role=user.role,
        permission_policies=[
            schemas.PermissionPolicy(
                id=p.id,
                user_id=p.user_id,
                name=p.name,
                conditions=p.conditions,
                is_active=p.is_active,
            )
            for p in user.permission_policies
        ],
    )
    return response_data

# src/app/services/permission_service.py
from sqlalchemy.orm import Session, Query, joinedload
from sqlalchemy import or_, and_
from typing import List

from app.db import models


def _build_filter_from_condition(condition: dict):
    """Translates a single JSON condition into a SQLAlchemy filter criterion."""
    field_name = condition.get("field")
    operator = condition.get("operator")
    value = condition.get("value")

    column = getattr(models.Invoice, field_name, None)
    if column is None:
        return None

    if operator == "equals":
        return column == value
    if operator == "not_equals":
        return column != value
    if operator == ">":
        return column > value
    if operator == "<":
        return column < value
    if operator == ">=":
        return column >= value
    if operator == "<=":
        return column <= value
    if operator == "contains":
        return column.ilike(f"%{value}%")
    if operator == "is_null":
        return column.is_(None)
    if operator == "is_not_null":
        return column.isnot(None)
    # Add other operators as needed
    return None


def apply_invoice_permissions(query: Query, user: models.User, db: Session) -> Query:
    """
    Applies all of a user's permission policies to an invoice query.
    """
    if user.role.name == "admin":
        return query  # Admins see everything

    # For AP Processors, build a filter from their policies
    user_with_policies = (
        db.query(models.User)
        .options(joinedload(models.User.permission_policies))
        .filter(models.User.id == user.id)
        .one()
    )

    policies = user_with_policies.permission_policies
    if not policies:
        return query.filter(models.Invoice.id == -1)  # No policies means see nothing

    # Combine all policies with an OR condition
    all_policy_filters = []
    for policy in policies:
        if not policy.is_active:
            continue

        conditions = policy.conditions.get("conditions", [])
        logical_op = policy.conditions.get("logical_operator", "AND").upper()

        # Build filters for the conditions within this single policy
        single_policy_filters = [
            _build_filter_from_condition(cond) for cond in conditions
        ]
        single_policy_filters = [f for f in single_policy_filters if f is not None]

        if not single_policy_filters:
            continue

        # Combine the conditions for this policy using AND or OR
        if logical_op == "AND":
            all_policy_filters.append(and_(*single_policy_filters))
        else:
            all_policy_filters.append(or_(*single_policy_filters))

    if not all_policy_filters:
        return query.filter(models.Invoice.id == -1)

    return query.filter(or_(*all_policy_filters))

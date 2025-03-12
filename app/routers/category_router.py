from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.repositories import category_crud
from app.schemas import category_schema, user_schema
from app.security.user_security import get_current_user

category_Router = APIRouter(prefix="/category")


@category_Router.get(
    "/list", response_model=list[category_schema.Category], tags=["categories"]
)
def get_user_categories(
    type: Optional[Literal["income", "expense"]] = Query(
        default=None, description="Filter by category type (income or expense)"
    ),
    ignore_group: Optional[bool] = Query(
        default=False, description="Exclude group categories if set to true"
    ),
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    categories = category_crud.get_categories_by_username(
        db=db, username=user.username, category_type=type, ignore_group=ignore_group
    )

    if not categories:
        return []

    return categories


@category_Router.post(
    "/create", response_model=category_schema.Category, tags=["categories"]
)
def create_category(
    category: category_schema.CategoryCreate,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        new_category = category_crud.create_category(
            db=db, user_id=user.user_id, category=category
        )
        return new_category
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the category.",
        )


@category_Router.get(
    "/group", response_model=list[category_schema.CategoryBase], tags=["categories"]
)
def get_group_categories_by_type(
    category_type: Optional[Literal["income", "expense"]] = Query(
        default=None, description="Filter by category type (income or expense)"
    ),
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    group_categories = category_crud.get_group_categories_by_type(
        db=db, user_id=user.user_id, category_type=category_type
    )
    return group_categories

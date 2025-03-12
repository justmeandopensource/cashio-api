from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.model import Category
from app.repositories.user_crud import get_user_by_username
from app.schemas.category_schema import CategoryCreate


def get_categories_by_username(
    db: Session,
    username: str,
    category_type: Optional[str] = None,
    ignore_group: Optional[bool] = False,
):
    user = get_user_by_username(db=db, username=username)
    if not user:
        return []

    query = db.query(Category).filter(Category.user_id == user.user_id)

    # Filter by category type if provided
    if category_type:
        query = query.filter(Category.type == category_type)

    # Exclude group categories if ignore_group is True
    if ignore_group:
        query = query.filter(Category.is_group == False)

    categories = query.all()
    return categories


def create_category(db: Session, user_id: int, category: CategoryCreate):
    existing_category = (
        db.query(Category)
        .filter(Category.user_id == user_id, Category.name == category.name)
        .first()
    )

    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Category already exists"
        )

    # Validate parent_category_id (if provided)
    if category.parent_category_id is not None:
        parent_category = (
            db.query(Category)
            .filter(
                Category.category_id == category.parent_category_id,
                Category.user_id == user_id,
                Category.is_group == True,
            )
            .first()
        )

        if not parent_category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid parent_category_id: The parent category must exist and be a group category in the same account",
            )

    db_category = Category(
        user_id=user_id,
        name=category.name,
        type=category.type,
        is_group=category.is_group,
        parent_category_id=category.parent_category_id,
    )

    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


def get_group_categories_by_type(
    db: Session, user_id: int, category_type: Optional[str] = None
):
    query = db.query(Category).filter(
        Category.user_id == user_id, Category.is_group == True
    )
    if category_type:
        query = query.filter(Category.type == category_type)
    return query.all()

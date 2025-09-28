from datetime import datetime
from sqlalchemy.orm import Session

from app.models.model import User
from app.schemas.user_schema import UserCreate
from app.security.user_security import hash_password


def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()


def create_user(db: Session, user: UserCreate):
    hashed_password = hash_password(user.password)
    db_user = User(
        full_name=user.full_name,
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.user_id == user_id).first()


def update_user(db: Session, user_id: int, full_name: str | None = None, email: str | None = None):
    db_user = db.query(User).filter(User.user_id == user_id).first()
    if db_user:
        if full_name is not None:
            db_user.full_name = full_name  # type: ignore[reportAttributeAccessIssue]
        if email is not None:
            db_user.email = email  # type: ignore[reportAttributeAccessIssue]
        db_user.updated_at = datetime.now()  # type: ignore[reportAttributeAccessIssue]
        db.commit()
        db.refresh(db_user)
    return db_user


def update_password(db: Session, user_id: int, new_password: str):
    db_user = db.query(User).filter(User.user_id == user_id).first()
    if db_user:
        db_user.hashed_password = hash_password(new_password)  # type: ignore
        # Update the updated_at timestamp to current local time
        db_user.updated_at = datetime.now()  # type: ignore[reportAttributeAccessIssue]
        db.commit()
        db.refresh(db_user)
    return db_user

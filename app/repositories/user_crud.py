from sqlalchemy.orm import Session
from models.model import User
from schemas.user_schema import UserCreate
from security.user_security import hash_password

def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def create_user(db: Session, user: UserCreate):
    hashed_password = hash_password(user.password)
    db_user = User(
        full_name = user.full_name,
        username = user.username,
        email = user.email,
        hashed_password = hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

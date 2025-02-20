from sqlalchemy.orm import Session
from models.model import Ledger
from repositories.user_crud import get_user_by_username

def get_ledgers_by_username(db: Session, username: str):
    user = get_user_by_username(db, username)
    if not user:
        return []
    return db.query(Ledger).filter(Ledger.user_id == user.user_id).all()

from sqlalchemy.orm import Session

from app.models.model import Tag


def search_tags(db: Session, query: str, user_id: int):
    return (
        db.query(Tag).filter(Tag.user_id == user_id, Tag.name.ilike(f"%{query}%")).all()
    )

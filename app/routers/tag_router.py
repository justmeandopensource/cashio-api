from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.repositories import tag_crud
from app.schemas import tag_schema, user_schema
from app.security.user_security import get_current_user

tag_Router = APIRouter(prefix="/tags")


@tag_Router.get("/search", response_model=List[tag_schema.Tag], tags=["tags"])
def search_tags(
    query: str = Query(..., min_length=1, description="Search query for tags"),
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return tag_crud.search_tags(db=db, query=query, user_id=user.user_id)

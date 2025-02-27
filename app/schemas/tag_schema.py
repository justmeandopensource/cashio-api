from pydantic import BaseModel

class TagCreate(BaseModel):
    name: str

class Tag(TagCreate):
    tag_id: int
    user_id: int

    class Config:
        from_attributes = True

from pydantic import BaseModel
from datetime import datetime

class UserBase(BaseModel):
    full_name: str
    username: str
    email: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    user_id: int
    username: str
    created_at: datetime
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str


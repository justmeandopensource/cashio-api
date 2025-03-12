from datetime import datetime

from pydantic import BaseModel


class UserBase(BaseModel, str_strip_whitespace=True):
    full_name: str
    username: str
    email: str


class UserCreate(UserBase):
    password: str


class User(UserBase, str_strip_whitespace=True):
    user_id: int
    username: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str

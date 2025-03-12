from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.repositories import user_crud
from app.schemas import general_schema, user_schema
from app.security.user_security import (
    authenticate_user,
    create_access_token,
    oauth2_scheme,
    verify_token,
)

user_Router = APIRouter(prefix="/user")


@user_Router.post(
    "/create", response_model=general_schema.RegisterResponse, tags=["users"]
)
def create_user(user: user_schema.UserCreate, db: Session = Depends(get_db)):
    db_user = user_crud.get_user_by_username(db=db, username=user.username)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )
    user_crud.create_user(db=db, user=user)
    return {"message": "user created successfully"}


@user_Router.post("/login", tags=["users"])
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"www-Authenticate": "Bearer"},
        )
    access_token = create_access_token(user=user)
    return {"access_token": access_token, "token_type": "bearer"}


@user_Router.post("/verify-token", tags=["users"])
async def verify_user_token(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    try:
        verify_token(token=token, db=db)
        return {"message": "token is valid"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while verifying the token.",
        )

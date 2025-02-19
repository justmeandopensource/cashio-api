import uvicorn
from fastapi import FastAPI
from routers import user_router
from database.connection import Base, engine
from contextlib import asynccontextmanager
from models.user_model import User
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    # stuff to do when app starts
    Base.metadata.create_all(bind=engine)
    yield
    # stuff to do when app stops

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins="http://localhost:5173",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_router.user_Router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

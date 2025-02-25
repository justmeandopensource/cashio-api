import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from routers import (
    user_router,
    ledger_router,
    account_router,
    transaction_router,
    category_router,
    system_router
)
from database.connection import Base, engine
from models import model
from repositories.settings import settings
from version import __version__

@asynccontextmanager
async def lifespan(app: FastAPI):
    # stuff to do when app starts
    Base.metadata.create_all(bind=engine)
    yield
    # stuff to do when app stops

app = FastAPI(title=settings.API_TITLE, version=__version__, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CASHIO_UI_URL,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_router.user_Router)
app.include_router(ledger_router.ledger_Router)
app.include_router(account_router.account_Router)
app.include_router(transaction_router.transaction_Router)
app.include_router(category_router.category_Router)
app.include_router(system_router.system_Router)

if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.API_HOST, port=settings.API_PORT, reload=True)

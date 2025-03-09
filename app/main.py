import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.version import __version__
from app.routers import (
    user_router,
    ledger_router,
    account_router,
    transaction_router,
    tag_router,
    category_router,
    system_router
)
from app.database.connection import Base, engine
from app.models import model
from app.repositories.settings import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # stuff to do when app starts
    Base.metadata.create_all(bind=engine)
    yield
    # stuff to do when app stops

app = FastAPI(version=__version__, lifespan=lifespan)

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
app.include_router(tag_router.tag_Router)
app.include_router(category_router.category_Router)
app.include_router(system_router.system_Router)

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        ssl_keyfile="/app/certs/key.pem",
        ssl_certfile="/app/certs/cert.pem"
    )

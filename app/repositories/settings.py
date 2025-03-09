from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    # database
    POSTGRES_USER: str = "test"
    POSTGRES_PASSWORD: str = "test"
    POSTGRES_DB: str = "test"
    POSTGRES_HOST: str = "host"
    POSTGRES_PORT: int = 5432

    SQLALCHEMY_DATABASE_URL: str = "postgresql://test:test@host:5432/db"

    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173"]

    # for jwt
    SECRET_KEY: str = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

settings = Settings()

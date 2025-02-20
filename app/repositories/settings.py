from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    API_TITLE: str = "Cashio API"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    SQLALCHEMY_DATABASE_URL: str = "sqlite:///./cashio.db"

    # frontend url to allow access to the api
    CASHIO_UI_URL: str ="http://localhost:5173"

    # for jwt
    SECRET_KEY: str = "098166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

settings = Settings()

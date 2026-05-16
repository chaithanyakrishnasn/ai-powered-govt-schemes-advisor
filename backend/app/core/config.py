from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/yojana"
    GEMINI_API_KEY: str = ""
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "dev"
    GEMINI_MODEL_FAST: str = "gemini-2.5-flash"
    GEMINI_MODEL_EMBED: str = "gemini-embedding-001"
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:3001"]
    APP_VERSION: str = "0.1.0"
    WORKERS: int = 2
    LOG_JSON: bool = False

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "prod"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

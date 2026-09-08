from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Defaults to a local SQLite file; set DATABASE_URL to a Postgres DSN in
    # production without touching any code, per decisions.md.
    database_url: str = "sqlite:///./salary_management.db"
    jwt_secret: str = "development-only-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 90
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    class Config:
        env_file = ".env"


settings = Settings()

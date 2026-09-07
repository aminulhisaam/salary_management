from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Defaults to a local SQLite file; set DATABASE_URL to a Postgres DSN in
    # production without touching any code, per decisions.md.
    database_url: str = "sqlite:///./salary_management.db"
    jwt_secret: str = "Amin-Ul-Hisaam"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 90

    class Config:
        env_file = ".env"


settings = Settings()

import os
from pathlib import Path

from sqlalchemy import create_engine, text

from alembic import command
from alembic.config import Config
from app.config import settings


def database_url_for_tests(tmp_path, filename: str) -> str:
    return os.environ.get("TEST_DATABASE_URL", f"sqlite:///{tmp_path / filename}")


def engine_options_for_tests(url: str) -> dict:
    return {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}


def migrate_test_database(url: str) -> None:
    settings.database_url = url
    if url.startswith("postgresql"):
        engine = create_engine(url)
        with engine.begin() as connection:
            connection.execute(text("DROP SCHEMA public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))
        engine.dispose()
    command.upgrade(Config(str(Path(__file__).parents[1] / "alembic.ini")), "head")

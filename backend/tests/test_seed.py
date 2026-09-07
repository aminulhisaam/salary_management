import importlib.util
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from app.config import settings
from app.models import Employee, Salary

seed_module_path = Path(__file__).parents[2] / "seed" / "seed.py"
seed_module_spec = importlib.util.spec_from_file_location("seed_script", seed_module_path)
assert seed_module_spec is not None and seed_module_spec.loader is not None
seed_module = importlib.util.module_from_spec(seed_module_spec)
seed_module_spec.loader.exec_module(seed_module)
seed_database = seed_module.seed_database


def test_seed_populates_employees_and_salary_history(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'seed.db'}"
    monkeypatch.setattr(settings, "database_url", database_url)

    alembic_config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    command.upgrade(alembic_config, "head")
    assert seed_database() == 10_000

    engine = create_engine(database_url)
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Employee)) == 10_000
        assert (
            session.scalar(
                select(func.count())
                .select_from(Employee)
                .where(Employee.current_salary_amount.is_(None))
            )
            == 0
        )
        assert (
            session.scalar(
                select(Salary.employee_id)
                .group_by(Salary.employee_id)
                .having(func.count(Salary.id) > 1)
                .limit(1)
            )
            is not None
        )
    engine.dispose()

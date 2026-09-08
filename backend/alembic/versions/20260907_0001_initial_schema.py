"""Create users, employees, and salaries tables.

Revision ID: 20260907_0001
Revises:
Create Date: 2026-09-07 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260907_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    is_sqlite = op.get_bind().dialect.name == "sqlite"
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("hashed_password", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), server_default=sa.text("'hr_admin'"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "employees",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("employee_code", sa.Text(), nullable=False),
        sa.Column("first_name", sa.Text(), nullable=False),
        sa.Column("last_name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("department", sa.Text(), nullable=False),
        sa.Column("country", sa.Text(), nullable=False),
        sa.Column("job_title", sa.Text(), nullable=False),
        sa.Column("band", sa.Text(), nullable=False),
        sa.Column("hire_date", sa.Date(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("current_salary_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("current_salary_currency", sa.Text(), nullable=True),
        sa.Column("current_salary_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_code"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_employees_band"), "employees", ["band"], unique=False)
    op.create_index(op.f("ix_employees_country"), "employees", ["country"], unique=False)
    op.create_index(op.f("ix_employees_department"), "employees", ["department"], unique=False)

    op.create_table(
        "salaries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_salaries_effective_date"), "salaries", ["effective_date"], unique=False
    )
    op.create_index(
        op.f("ix_salaries_employee_id"),
        "salaries",
        ["employee_id"],
        unique=False,
    )
    if is_sqlite:
        with op.batch_alter_table("employees") as batch_op:
            batch_op.create_foreign_key(
                "fk_employees_current_salary_id_salaries",
                "salaries",
                ["current_salary_id"],
                ["id"],
            )
    else:
        op.create_foreign_key(
            "fk_employees_current_salary_id_salaries",
            "employees",
            "salaries",
            ["current_salary_id"],
            ["id"],
        )
    op.create_index(
        "ix_salaries_employee_id_effective_date",
        "salaries",
        ["employee_id", sa.text("effective_date DESC")],
        unique=False,
    )


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("employees") as batch_op:
            batch_op.drop_constraint("fk_employees_current_salary_id_salaries", type_="foreignkey")
    else:
        op.drop_constraint("fk_employees_current_salary_id_salaries", "employees", type_="foreignkey")
    op.drop_index("ix_salaries_employee_id_effective_date", table_name="salaries")
    op.drop_index(op.f("ix_salaries_employee_id"), table_name="salaries")
    op.drop_index(op.f("ix_salaries_effective_date"), table_name="salaries")
    op.drop_table("salaries")
    op.drop_index(op.f("ix_employees_department"), table_name="employees")
    op.drop_index(op.f("ix_employees_country"), table_name="employees")
    op.drop_index(op.f("ix_employees_band"), table_name="employees")
    op.drop_table("employees")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

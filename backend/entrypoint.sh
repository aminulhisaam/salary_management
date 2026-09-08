#!/bin/sh
set -eu

: "${DATABASE_URL:=sqlite:///./salary_management.db}"
export DATABASE_URL

alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"

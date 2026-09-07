from datetime import datetime

from sqlalchemy import TIMESTAMP, Integer, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(Text, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text, default="hr_admin", server_default=text("'hr_admin'"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP)

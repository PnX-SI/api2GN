from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from geonature.utils.env import DB


class ParserModel(DB.Model):
    __tablename__ = "parser"
    __table_args__ = {"schema": "api2gn"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    last_import: Mapped[Optional[datetime]] = mapped_column(DateTime)
    nb_row_total: Mapped[Optional[int]] = mapped_column(Integer)
    nb_row_last_import: Mapped[Optional[int]] = mapped_column(Integer)
    schedule_frequency: Mapped[Optional[int]] = mapped_column(Integer)

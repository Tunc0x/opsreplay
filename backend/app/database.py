import os
from collections.abc import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session


class Base(DeclarativeBase):
    pass


DATABASE_URL = os.getenv("DATABASE_URL")

engine: Engine | None = None
if DATABASE_URL:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 3},
    )


def is_database_healthy() -> bool:
    if engine is None:
        return False

    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1")).scalar_one()
    except SQLAlchemyError:
        return False

    return result == 1


def get_db_session() -> Iterator[Session]:
    if engine is None:
        raise RuntimeError(
            "DATABASE_URL is required to create a database session."
        )

    with Session(engine) as session:
        yield session

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import Base, get_db_session
from app.main import app
from app.models.organization import Organization  # noqa: F401


DEFAULT_TEST_DATABASE_URL = (
    "postgresql+psycopg://opsreplay_test:opsreplay_test@"
    "127.0.0.1:5433/opsreplay_test"
)
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    DEFAULT_TEST_DATABASE_URL,
)

test_engine = create_engine(TEST_DATABASE_URL)


@pytest.fixture(scope="session", autouse=True)
def prepare_test_database() -> Iterator[None]:
    try:
        try:
            with test_engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError as error:
            pytest.fail(
                "Test database is not reachable. Start it with "
                "`docker compose --profile test up -d test_db`. "
                f"Database error: {error}",
                pytrace=False,
            )

        Base.metadata.drop_all(test_engine)
        Base.metadata.create_all(test_engine)
        yield
    finally:
        test_engine.dispose()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with test_engine.connect() as connection:
        outer_transaction = connection.begin()

        def override_get_db_session() -> Iterator[Session]:
            with Session(
                bind=connection,
                join_transaction_mode="create_savepoint",
            ) as session:
                yield session

        app.dependency_overrides[get_db_session] = override_get_db_session

        try:
            with TestClient(app) as test_client:
                yield test_client
        finally:
            app.dependency_overrides.clear()
            outer_transaction.rollback()

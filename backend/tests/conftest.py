import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import Base, get_db_session
from app.main import app
from app.models import Organization, Repository  # noqa: F401


DEFAULT_TEST_DATABASE_URL = (
    "postgresql+psycopg://opsreplay_test:opsreplay_test@"
    "127.0.0.1:5433/opsreplay_test"
)
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    DEFAULT_TEST_DATABASE_URL,
)

test_engine = create_engine(TEST_DATABASE_URL)

# pytest automatically uses this fixture, we prepare the testing environment once for the entire pytest run.
@pytest.fixture(scope="session", autouse=True) # scope="session" defines how long that fixture instance should stay alive, in this case after the whole test session is finished.
def prepare_test_database() -> Iterator[None]:
    try:
        try:
            # Check if communication is possible
            with test_engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError as error:
            pytest.fail(
                "Test database is not reachable. Start it with "
                "`docker compose --profile test up -d test_db`. "
                f"Database error: {error}",
                pytrace=False,
            )

        # start with fresh tables
        Base.metadata.drop_all(test_engine)
        # Recreate fresh empty tables based on my SQLAlchemy models.
        Base.metadata.create_all(test_engine)
        yield
    finally:
        test_engine.dispose()

# another fixture for every individual test.
@pytest.fixture
def client() -> Iterator[TestClient]:
    # ───────── SETUP ─────────
    # again open connection for the test
    with test_engine.connect() as connection:
        # wrap the entire test in one big transaction
        outer_transaction = connection.begin()

        def override_get_db_session() -> Iterator[Session]:
            with Session(
                bind=connection, # This SQLAlchemy Session must use the test connection I created above.
                join_transaction_mode="create_savepoint", # The application plays inside a sandbox that itself sits inside a bigger transaction controlled by pytest.
            ) as session:
                yield session
        # we override the dependency so we are not using the real database rather our test db, thats the power of dependency injection
        app.dependency_overrides[get_db_session] = override_get_db_session

        try:
            with TestClient(app) as test_client:
                yield test_client # TestClient lets pytest talk to FastAPI approximately as if a frontend/browser were making HTTP requests.
                # ── test runs while paused here ──
        finally:
            # ───────── TEARDOWN ─────────
            app.dependency_overrides.clear()
            outer_transaction.rollback()

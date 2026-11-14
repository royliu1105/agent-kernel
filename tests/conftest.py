import os
from collections.abc import Iterator

import pytest
from kernel_storage import create_session_factory
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from scripts.testing_database import isolated_database
from scripts.testing_database import test_database_url as configured_test_database_url


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    # Validate once for legacy opt-in PostgreSQL fixtures as well as shared fixtures.
    if os.environ.get("AGENT_KERNEL_TEST_POSTGRES_URL"):
        try:
            configured_test_database_url()
        except ValueError as error:
            raise pytest.UsageError(str(error)) from None
    # Import-time ASGI construction must never inherit a developer's live DB URL.
    # This non-listening endpoint is only for constructing engines, never a fixture.
    os.environ["DATABASE_URL"] = "postgresql+psycopg://unused@127.0.0.1:1/import_only_test"


@pytest.fixture
def postgres_engine(monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    with isolated_database() as engine:
        monkeypatch.setenv("DATABASE_URL", engine.url.render_as_string(hide_password=False))
        yield engine


@pytest.fixture
def postgres_session_factory(postgres_engine: Engine) -> sessionmaker[Session]:
    return create_session_factory(postgres_engine)


@pytest.fixture
def migration_engine() -> Iterator[Engine]:
    with isolated_database(migrated=False) as engine:
        yield engine

from uuid import UUID

import pytest
from kernel_core import MemoryType
from kernel_storage import MemoryRepository
from sqlalchemy.orm import Session, sessionmaker


def test_memory_repository_creates_loads_and_filters_memory_items(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    source_run_id = UUID("00000000-0000-0000-0000-000000000123")
    with sqlite_session_factory() as session:
        repository = MemoryRepository(session)
        preference = repository.create(
            type=MemoryType.USER_PREFERENCE,
            scope="user:roy",
            content={"language": "zh"},
            source_run_id=source_run_id,
            confidence=0.9,
            metadata={"source": "manual"},
        )
        repository.create(
            type=MemoryType.TASK_CONTEXT,
            scope="task:deploy",
            content={"summary": "Deploy needs approval."},
        )

        loaded = repository.get(preference.id)
        user_memories = repository.list(scope="user:roy")
        preference_memories = repository.list(type=MemoryType.USER_PREFERENCE)

    assert loaded is not None
    assert loaded.id == preference.id
    assert loaded.type is MemoryType.USER_PREFERENCE
    assert loaded.scope == "user:roy"
    assert loaded.content == {"language": "zh"}
    assert loaded.source_run_id == source_run_id
    assert loaded.confidence == 0.9
    assert loaded.metadata == {"source": "manual"}
    assert [item.id for item in user_memories] == [preference.id]
    assert [item.id for item in preference_memories] == [preference.id]


def test_memory_repository_deletes_memory_item(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        repository = MemoryRepository(session)
        memory = repository.create(
            type=MemoryType.LONG_TERM,
            scope="user:roy",
            content={"fact": "Prefers concise summaries."},
        )

        deleted = repository.delete(memory.id)
        loaded = repository.get(memory.id)
        missing_deleted = repository.delete(memory.id)

    assert deleted is True
    assert loaded is None
    assert missing_deleted is False


def test_memory_repository_rejects_invalid_limit(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session, pytest.raises(
        ValueError,
        match="limit must be at least 1",
    ):
        MemoryRepository(session).list(limit=0)

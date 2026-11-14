import json

import pytest
from kernel_core import MemoryType
from kernel_memory import MemoryRetrievalService
from kernel_storage import MemoryRepository
from sqlalchemy import event
from sqlalchemy.orm import Session, sessionmaker


def test_memory_retrieval_service_filters_by_scope_and_type(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory() as session:
        repository = MemoryRepository(session)
        preference = repository.create(
            type=MemoryType.USER_PREFERENCE,
            scope="user:roy",
            content={"language": "zh"},
            confidence=0.9,
        )
        repository.create(
            type=MemoryType.TASK_CONTEXT,
            scope="task:deploy",
            content={"summary": "Deploy needs approval."},
        )
        repository.create(
            type=MemoryType.USER_PREFERENCE,
            scope="user:someone-else",
            content={"language": "en"},
        )

        context = MemoryRetrievalService().retrieve(
            repository=repository,
            scopes=("user:roy", "task:deploy"),
            types=(MemoryType.USER_PREFERENCE,),
            limit=10,
        )

    assert [item.id for item in context.items] == [preference.id]
    assert context.to_output_payload() == {
        "used": True,
        "item_count": 1,
        "item_ids": [str(preference.id)],
    }
    item = json.loads(context.to_prompt_text())["items"][0]
    assert item["type"] == "user_preference"
    assert item["content"] == {"language": "zh"}


def test_memory_retrieval_service_returns_empty_context(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory() as session:
        context = MemoryRetrievalService().retrieve(
            repository=MemoryRepository(session),
            scopes=("user:missing",),
        )

    assert context.items == ()
    assert json.loads(context.to_prompt_text()) == {
        "version": 1,
        "trust": "untrusted",
        "items": [],
    }
    assert context.to_output_payload() == {
        "used": False,
        "item_count": 0,
        "item_ids": [],
    }


def test_memory_retrieval_service_rejects_empty_scopes(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with (
        postgres_session_factory() as session,
        pytest.raises(
            ValueError,
            match="At least one memory scope is required",
        ),
    ):
        MemoryRetrievalService().retrieve(
            repository=MemoryRepository(session),
            scopes=(),
        )


def test_memory_recall_queries_once_and_limits_globally_to_newest(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory() as session:
        repository = MemoryRepository(session)
        items = [
            repository.create(
                type=MemoryType.LONG_TERM if index % 2 else MemoryType.USER_PREFERENCE,
                scope=f"scope-{index % 2}",
                content={"index": index},
            )
            for index in range(24)
        ]
        statements: list[str] = []

        def record_query(*args: object) -> None:
            statements.append(str(args[2]))

        engine = session.get_bind()
        event.listen(engine, "before_cursor_execute", record_query)
        try:
            context = MemoryRetrievalService().retrieve(
                repository=repository,
                scopes=("scope-0", "scope-1", "scope-0"),
                types=(MemoryType.LONG_TERM, MemoryType.USER_PREFERENCE),
                limit=20,
            )
        finally:
            event.remove(engine, "before_cursor_execute", record_query)
        assert len(statements) == 1
        assert [item.id for item in context.items] == [item.id for item in reversed(items[-20:])]
        assert (
            MemoryRetrievalService()
            .retrieve(
                repository=repository,
                scopes=("scope-0",),
                types=(),
            )
            .items
            == ()
        )

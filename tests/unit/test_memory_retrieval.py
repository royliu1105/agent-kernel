import pytest
from kernel_core import MemoryType
from kernel_memory import MemoryRetrievalService
from kernel_storage import MemoryRepository
from sqlalchemy.orm import Session, sessionmaker


def test_memory_retrieval_service_filters_by_scope_and_type(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
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
    assert "type=user_preference" in context.to_prompt_text()
    assert '"language": "zh"' in context.to_prompt_text()


def test_memory_retrieval_service_returns_empty_context(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        context = MemoryRetrievalService().retrieve(
            repository=MemoryRepository(session),
            scopes=("user:missing",),
        )

    assert context.items == ()
    assert context.to_prompt_text() == "Relevant memory: none."
    assert context.to_output_payload() == {
        "used": False,
        "item_count": 0,
        "item_ids": [],
    }


def test_memory_retrieval_service_rejects_empty_scopes(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session, pytest.raises(
        ValueError,
        match="At least one memory scope is required",
    ):
        MemoryRetrievalService().retrieve(
            repository=MemoryRepository(session),
            scopes=(),
        )

import asyncio
import json
from pathlib import Path
from threading import Event

import pytest
from agent_kernel_api.readiness import (
    DependencyCheck,
    ReadinessChecker,
    create_readiness_checker,
)
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker


@pytest.mark.asyncio
@pytest.mark.parametrize("valid", [True, False])
async def test_pilot_provider_readiness_is_local_and_keeps_credentials_private(
    postgres_session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch, valid: bool
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("Readiness must not contact a provider")

    monkeypatch.setattr("httpx.Client.send", forbidden)
    monkeypatch.setattr("httpx.AsyncClient.send", forbidden)
    checker = create_readiness_checker(
        postgres_session_factory,
        env={
            "AGENT_KERNEL_EMBEDDING_PROVIDER": "dashscope",
            "DASHSCOPE_API_KEY": "fixture-embedding" if valid else "",
            "DEEPSEEK_API_KEY": "fixture-generation",
            "AGENT_KERNEL_READINESS_DEEPSEEK": "required",
            "DEEPSEEK_BASE_URL": "https://api.deepseek.com"
            if valid
            else "https://SECRET@wrong.test",
        },
    )
    try:
        result = await checker.check()
        assert result.status_code == (200 if valid else 503)
        dependencies = {item.name: item for item in result.dependencies}
        for name in ("deepseek", "dashscope"):
            assert dependencies[name].required
            assert dependencies[name].status == ("ok" if valid else "failed")
        assert "SECRET" not in json.dumps(result.to_dict())
        assert "fixture" not in json.dumps(result.to_dict())
    finally:
        checker.close()


@pytest.mark.parametrize("mode", ["optional", "disabled"])
def test_selected_dashscope_cannot_disable_required_readiness(mode: str) -> None:
    with pytest.raises(ValueError, match="must be required"):
        create_readiness_checker(
            sessionmaker(),
            env={
                "AGENT_KERNEL_EMBEDDING_PROVIDER": "dashscope",
                "AGENT_KERNEL_READINESS_DASHSCOPE": mode,
            },
        )


@pytest.mark.asyncio
async def test_readiness_checks_real_database_and_disabled_dependencies(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    checker = create_readiness_checker(postgres_session_factory, env={})
    try:
        result = await checker.check()
        assert result.status_code == 200
        assert result.to_dict() == {
            "status": "ready",
            "dependencies": {
                "database": {"required": True, "status": "ok"},
                "redis": {"required": False, "status": "disabled"},
                "s3": {"required": False, "status": "disabled"},
                "pgvector": {"required": True, "status": "ok"},
                "local_storage": {"required": True, "status": "ok"},
                "openai": {"required": False, "status": "disabled"},
            },
        }
    finally:
        checker.close()


@pytest.mark.asyncio
async def test_connectivity_without_schema_is_not_ready(migration_engine: Engine) -> None:
    engine = migration_engine
    checker = create_readiness_checker(sessionmaker(engine), env={})
    try:
        result = await checker.check()
        assert result.status_code == 503
        assert result.to_dict()["status"] == "not_ready"
        assert "SELECT" not in json.dumps(result.to_dict())
    finally:
        checker.close()
        engine.dispose()


@pytest.mark.asyncio
async def test_required_optional_and_missing_configuration_are_distinct(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    def failure() -> None:
        raise RuntimeError("postgres://user:password@host/private?token=SECRET")

    optional = create_readiness_checker(
        postgres_session_factory, env={"REDIS_URL": "redis://configured"}, redis_probe=failure
    )
    required = create_readiness_checker(
        postgres_session_factory, env={"AGENT_KERNEL_READINESS_REDIS": "required"}
    )
    s3 = create_readiness_checker(
        postgres_session_factory, env={"AGENT_KERNEL_OBJECT_STORE_BACKEND": "s3"}
    )
    try:
        result = await optional.check()
        assert result.ready and result.to_dict()["status"] == "degraded"
        assert "SECRET" not in json.dumps(result.to_dict())
        assert "postgres" not in json.dumps(result.to_dict())
        assert (await required.check()).status_code == 503
        assert (await s3.check()).status_code == 503
    finally:
        optional.close()
        required.close()
        s3.close()


@pytest.mark.asyncio
async def test_auxiliary_s3_can_be_optional_but_selected_backend_cannot(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    for backend, mode, code in (("s3", "required", 503), ("local", "optional", 200)):
        checker = create_readiness_checker(
            postgres_session_factory,
            env={"AGENT_KERNEL_OBJECT_STORE_BACKEND": backend, "AGENT_KERNEL_READINESS_S3": mode},
            s3_probe=lambda: False,
        )
        try:
            assert (await checker.check()).status_code == code
        finally:
            checker.close()
    for mode in ("optional", "disabled"):
        with pytest.raises(ValueError, match="S3 readiness"):
            create_readiness_checker(
                postgres_session_factory,
                env={
                    "AGENT_KERNEL_OBJECT_STORE_BACKEND": "s3",
                    "AGENT_KERNEL_READINESS_S3": mode,
                },
            )
        with pytest.raises(ValueError, match="Redis readiness"):
            create_readiness_checker(
                postgres_session_factory,
                env={
                    "AGENT_KERNEL_RATE_LIMIT_REQUESTS": "100",
                    "AGENT_KERNEL_READINESS_REDIS": mode,
                },
            )


@pytest.mark.asyncio
async def test_rate_limiter_makes_redis_a_required_dependency(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    checker = create_readiness_checker(
        postgres_session_factory, env={"AGENT_KERNEL_RATE_LIMIT_REQUESTS": "100"}
    )
    try:
        result = await checker.check()
        assert result.status_code == 503
        assert result.dependencies[1].required
        assert result.dependencies[1].error == "not_configured"
    finally:
        checker.close()


@pytest.mark.asyncio
async def test_deadlines_share_one_inflight_probe_and_do_not_queue_more_work() -> None:
    released = Event()
    calls = 0

    def hung() -> None:
        nonlocal calls
        calls += 1
        released.wait(timeout=2)

    checker = ReadinessChecker(
        (DependencyCheck("database", "required", hung),), timeout_seconds=0.03, cache_seconds=0
    )
    try:
        results = await asyncio.gather(*(checker.check() for _ in range(20)))
        assert all(result.status_code == 503 for result in results)
        assert all(result.dependencies[0].error == "timeout" for result in results)
        assert calls == 1
        await checker.check()
        assert calls == 1
    finally:
        released.set()
        checker.close()
    assert (await checker.check()).dependencies[0].error == "closed"


@pytest.mark.asyncio
async def test_readiness_recovers_without_recreating_checker() -> None:
    healthy = False
    checker = ReadinessChecker(
        (DependencyCheck("database", "required", lambda: healthy),), cache_seconds=0
    )
    try:
        assert not (await checker.check()).ready
        healthy = True
        assert (await checker.check()).ready
    finally:
        checker.close()


def test_invalid_dependency_modes_fail_at_startup(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with pytest.raises(ValueError, match="READINESS_REDIS"):
        create_readiness_checker(
            postgres_session_factory, env={"AGENT_KERNEL_READINESS_REDIS": "maybe"}
        )
    with pytest.raises(ValueError, match="database"):
        ReadinessChecker((DependencyCheck("database", "optional", lambda: True),))


@pytest.mark.asyncio
async def test_selected_pgvector_fails_without_vector_column(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory() as session:
        session.execute(text("ALTER TABLE chunk_embeddings DROP COLUMN vector_pg CASCADE"))
        session.commit()
    checker = create_readiness_checker(
        postgres_session_factory, env={"AGENT_KERNEL_VECTOR_STORE": "pgvector"}
    )
    try:
        result = await checker.check()
        assert result.status_code == 503
        assert result.to_dict()["dependencies"]["pgvector"] == {  # type: ignore[index]
            "required": True,
            "status": "failed",
            "error": "unavailable",
        }
    finally:
        checker.close()


@pytest.mark.asyncio
async def test_local_store_read_write_probe_and_invalid_root(
    postgres_session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    for root, expected in ((tmp_path / "objects", 200), (Path("/dev/null"), 503)):
        checker = create_readiness_checker(
            postgres_session_factory, env={"AGENT_KERNEL_OBJECT_STORE_ROOT": str(root)}
        )
        try:
            result = await checker.check()
            assert result.status_code == expected
            assert str(root) not in json.dumps(result.to_dict())
        finally:
            checker.close()
    assert list((tmp_path / "objects").iterdir()) == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "configuration",
    [
        {},
        {"OPENAI_API_KEY": "sk-PRIVATE_SENTINEL", "OPENAI_EMBEDDING_DIMENSIONS": "invalid"},
        {"OPENAI_API_KEY": "bad\nkey"},
    ],
)
async def test_required_provider_checks_configuration_without_billing(
    postgres_session_factory: sessionmaker[Session], configuration: dict[str, str]
) -> None:
    checker = create_readiness_checker(
        postgres_session_factory,
        env={"AGENT_KERNEL_READINESS_OPENAI": "required", **configuration},
    )
    try:
        result = await checker.check()
        assert result.status_code == 503
        assert "PRIVATE_SENTINEL" not in json.dumps(result.to_dict())
    finally:
        checker.close()


@pytest.mark.asyncio
async def test_valid_required_provider_does_not_call_network(
    postgres_session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("Readiness must not invoke a paid model")

    monkeypatch.setattr("httpx.Client.send", forbidden)
    checker = create_readiness_checker(
        postgres_session_factory,
        env={
            "AGENT_KERNEL_READINESS_OPENAI": "required",
            "OPENAI_API_KEY": "sk-test-only",
            "OPENAI_EMBEDDING_DIMENSIONS": "1536",
        },
    )
    try:
        assert (await checker.check()).status_code == 200
    finally:
        checker.close()


@pytest.mark.asyncio
async def test_selected_openai_embeddings_require_provider_readiness(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    checker = create_readiness_checker(
        postgres_session_factory,
        env={
            "AGENT_KERNEL_EMBEDDING_PROVIDER": "openai",
        },
    )
    try:
        result = await checker.check()
        assert result.status_code == 503
        provider = next(check for check in result.dependencies if check.name == "openai")
        assert provider.required and provider.status == "failed"
    finally:
        checker.close()
    for mode in ("optional", "disabled"):
        with pytest.raises(ValueError, match="must be required"):
            create_readiness_checker(
                postgres_session_factory,
                env={
                    "AGENT_KERNEL_EMBEDDING_PROVIDER": "openai",
                    "AGENT_KERNEL_READINESS_OPENAI": mode,
                },
            )
    with pytest.raises(ValueError, match="embedding provider"):
        create_readiness_checker(
            postgres_session_factory,
            env={
                "AGENT_KERNEL_EMBEDDING_PROVIDER": "unknown",
            },
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "setting",
    ["AGENT_KERNEL_RATE_LIMIT_PRINCIPAL_REQUESTS", "AGENT_KERNEL_RATE_LIMIT_API_KEY_REQUESTS"],
)
async def test_principal_and_key_limiters_make_redis_required(
    postgres_session_factory: sessionmaker[Session],
    setting: str,
) -> None:
    checker = create_readiness_checker(postgres_session_factory, env={setting: "10"})
    try:
        result = await checker.check()
        assert result.status_code == 503
        redis = next(check for check in result.dependencies if check.name == "redis")
        assert redis.required and redis.error == "not_configured"
    finally:
        checker.close()

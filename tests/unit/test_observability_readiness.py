import asyncio
import json
from threading import Event

import pytest
from agent_kernel_api.readiness import (
    DependencyCheck,
    ReadinessChecker,
    create_readiness_checker,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


@pytest.mark.asyncio
async def test_readiness_checks_real_database_and_disabled_dependencies(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    checker = create_readiness_checker(sqlite_session_factory, env={})
    try:
        result = await checker.check()
        assert result.status_code == 200
        assert result.to_dict() == {
            "status": "ready",
            "dependencies": {
                "database": {"required": True, "status": "ok"},
                "redis": {"required": False, "status": "disabled"},
                "s3": {"required": False, "status": "disabled"},
            },
        }
    finally:
        checker.close()


@pytest.mark.asyncio
async def test_connectivity_without_schema_is_not_ready() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
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
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    def failure() -> None:
        raise RuntimeError("postgres://user:password@host/private?token=SECRET")

    optional = create_readiness_checker(
        sqlite_session_factory, env={"REDIS_URL": "redis://configured"}, redis_probe=failure
    )
    required = create_readiness_checker(
        sqlite_session_factory, env={"AGENT_KERNEL_READINESS_REDIS": "required"}
    )
    s3 = create_readiness_checker(
        sqlite_session_factory, env={"AGENT_KERNEL_OBJECT_STORE_BACKEND": "s3"}
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
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    for backend, mode, code in (("s3", "required", 503), ("local", "optional", 200)):
        checker = create_readiness_checker(
            sqlite_session_factory,
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
                sqlite_session_factory,
                env={
                    "AGENT_KERNEL_OBJECT_STORE_BACKEND": "s3",
                    "AGENT_KERNEL_READINESS_S3": mode,
                },
            )
        with pytest.raises(ValueError, match="Redis readiness"):
            create_readiness_checker(
                sqlite_session_factory,
                env={
                    "AGENT_KERNEL_RATE_LIMIT_REQUESTS": "100",
                    "AGENT_KERNEL_READINESS_REDIS": mode,
                },
            )


@pytest.mark.asyncio
async def test_rate_limiter_makes_redis_a_required_dependency(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    checker = create_readiness_checker(
        sqlite_session_factory, env={"AGENT_KERNEL_RATE_LIMIT_REQUESTS": "100"}
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
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with pytest.raises(ValueError, match="READINESS_REDIS"):
        create_readiness_checker(
            sqlite_session_factory, env={"AGENT_KERNEL_READINESS_REDIS": "maybe"}
        )
    with pytest.raises(ValueError, match="database"):
        ReadinessChecker((DependencyCheck("database", "optional", lambda: True),))

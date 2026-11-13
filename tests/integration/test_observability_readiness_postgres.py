"""Readiness must verify the selected native backend, not only SELECT 1."""

import pytest
from agent_kernel_api.readiness import create_readiness_checker
from kernel_storage import create_session_factory
from sqlalchemy import Engine, text
from test_real_pgvector_backend_contract import pg_backend as pg_backend


@pytest.mark.asyncio
async def test_pgvector_readiness_detects_missing_native_column_in_isolated_schema(
    pg_backend: Engine,
) -> None:
    checker = create_readiness_checker(
        create_session_factory(pg_backend),
        env={"AGENT_KERNEL_VECTOR_STORE": "auto"},
        cache_seconds=0,
    )
    try:
        assert (await checker.check()).status_code == 200
        with pg_backend.begin() as connection:
            connection.execute(text("ALTER TABLE chunk_embeddings DROP COLUMN vector_pg CASCADE"))
        result = await checker.check()
        assert result.status_code == 503
        checks = {check.name: check for check in result.dependencies}
        assert checks["database"].status == "ok"
        assert checks["pgvector"].required and checks["pgvector"].status == "failed"
        assert checks["pgvector"].error == "unavailable"
    finally:
        checker.close()

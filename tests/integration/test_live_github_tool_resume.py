"""Opt-in live GitHub pin + approval resume (no paid model).

Set AGENT_KERNEL_TEST_LIVE_GITHUB=1 to hit api.github.com once. Uses a scripted
provider so DeepSeek/OpenAI spend remains zero.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import httpx
import pytest
from kernel_core import RunStatus, ToolCallStatus
from kernel_providers import LLMToolCall
from kernel_runtime import RunExecutionService
from kernel_storage import ApprovalRepository, RunRepository, ToolCallRepository
from kernel_tools import ToolRegistry
from kernel_tools.external.config import read_external_tools_config
from kernel_tools.external.openapi import load_openapi_tools
from sqlalchemy.orm import Session, sessionmaker
from test_bounded_native_execution import ScriptedProvider, queued, reply

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / "deploy/local-paid-tools"
ARGS = {"path": {"run_id": 43634747295}, "query": {"exclude_pull_requests": True}}
PIN = "a1b246537bc9e07143ad3daaf7dc1a9da6d03d1663b28829257f05766b11d232"


@pytest.mark.asyncio
async def test_live_github_pin_matches_and_resume_succeeds(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    if os.environ.get("AGENT_KERNEL_TEST_LIVE_GITHUB") != "1":
        pytest.skip("Set AGENT_KERNEL_TEST_LIVE_GITHUB=1 for one live GitHub GET.")

    config = read_external_tools_config(DIRECTORY / "tools.json").openapi[0]
    assert config.bindings[0].response_sha256 == PIN
    config = config.model_copy(update={"document": DIRECTORY / "github-ci.openapi.json"})

    async with httpx.AsyncClient(trust_env=False, timeout=20.0) as probe:
        probed = await probe.get(
            "https://api.github.com/repos/royliu1105/agent-kernel/actions/runs/43634747295",
            params={"exclude_pull_requests": "true"},
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
    assert probed.status_code == 200
    assert hashlib.sha256(probed.content).hexdigest() == PIN

    initial = ScriptedProvider(
        [reply(LLMToolCall(id="lookup", name="github_ci_run_status", arguments=ARGS))]
    )
    continuation = ScriptedProvider([reply(text="reviewed CI status received")])
    async with httpx.AsyncClient(trust_env=False, timeout=20.0) as client:
        registry = ToolRegistry()
        registry.register(load_openapi_tools(client, config)[0])
        with postgres_session_factory() as session:
            run_id = queued(session)
            waiting = await RunExecutionService(
                provider=initial, tool_registry=registry
            ).execute(run_id=run_id, repository=RunRepository(session))
            assert waiting.status is RunStatus.WAITING_APPROVAL
            approval = ApprovalRepository(session).list_for_run(run_id)[0]
            ApprovalRepository(session).approve(approval_id=approval.id)
        with postgres_session_factory() as session:
            result = await RunExecutionService(
                provider=continuation, tool_registry=registry
            ).resume(
                run_id=run_id,
                repository=RunRepository(session),
                approval_repository=ApprovalRepository(session),
                tool_call_repository=ToolCallRepository(session),
                approval_id=approval.id,
            )
            calls = ToolCallRepository(session).list_for_run(run_id)

    assert result.status is RunStatus.SUCCEEDED
    assert calls[0].status is ToolCallStatus.SUCCEEDED
    assert calls[0].result is not None
    assert calls[0].result["data"]["id"] == 43634747295
    assert len(continuation.requests) == 1

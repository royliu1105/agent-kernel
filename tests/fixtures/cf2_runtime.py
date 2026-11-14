"""Offline provider/MCP instrumentation, mounted only in disposable CF2 containers."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any
from unittest.mock import patch

EVIDENCE = Path("/evidence")


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def save(name: str, value: Any) -> None:
    path = EVIDENCE / name
    path.write_bytes(canonical(value))
    path.chmod(0o600)


def append(name: str, value: Any) -> None:
    with (EVIDENCE / name).open("a", encoding="utf-8") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        stream.write(canonical(value).decode() + "\n")
        stream.flush()
    (EVIDENCE / name).chmod(0o600)


def guard() -> None:
    from sqlalchemy.engine import make_url

    project = os.environ.get("CF2_PROJECT", "")
    url = make_url(os.environ.get("DATABASE_URL", ""))
    if (
        not re.fullmatch(r"agent-kernel-cf2-[0-9a-f]{16}", project)
        or not Path("/.dockerenv").exists()
        or json.loads((EVIDENCE / "guard.json").read_text()) != {"project": project}
        or url.get_backend_name() != "postgresql"
        or url.host != "postgres"
        or url.database != "cf2"
        or url.username != "cf2"
    ):
        raise RuntimeError("CF2 requires its owned disposable container/database.")


def bootstrap() -> None:
    from kernel_identity import PrincipalType, WorkspaceRole
    from kernel_storage import (
        ApiKeyRepository,
        PrincipalRepository,
        WorkspaceMembershipRepository,
        WorkspaceRepository,
        create_engine_for_url,
        create_session_factory,
    )

    guard()
    subprocess.run(["alembic", "upgrade", "head"], check=True)
    engine = create_engine_for_url()
    identities = {}
    try:
        with create_session_factory(engine)() as session:
            workspaces = {
                label: WorkspaceRepository(session).create(name=f"CF2 {label}", slug=f"cf2-{label}")
                for label in ("a", "b")
            }
            for label, workspace, role in (
                ("operator", workspaces["a"], WorkspaceRole.OPERATOR),
                ("viewer", workspaces["a"], WorkspaceRole.VIEWER),
                ("other", workspaces["b"], WorkspaceRole.OPERATOR),
            ):
                principal = PrincipalRepository(session).create(
                    type=PrincipalType.USER, display_name=f"CF2 {label}"
                )
                WorkspaceMembershipRepository(session).assign(
                    principal_id=principal.id, workspace_id=workspace.id, role=role
                )
                credential = ApiKeyRepository(session).issue(
                    workspace_id=workspace.id,
                    principal_id=principal.id,
                    name=f"CF2 {label}",
                    plaintext_key=secrets.token_urlsafe(40),
                )
                assert credential is not None
                identities[label] = {
                    "key": credential.plaintext_key,
                    "workspace_id": str(workspace.id),
                    "principal_id": str(principal.id),
                    "role": role.value,
                }
        save("credentials.json", identities)
        save(
            "identities.json",
            {
                label: {key: value for key, value in identity.items() if key != "key"}
                for label, identity in identities.items()
            },
        )
        save(
            "tools.json",
            {
                "mcp": [
                    {
                        "name": "cf2_inventory",
                        "stdio": {
                            "command": "/app/.venv/bin/python",
                            "args": ["/fixture/cf2_runtime.py", "mcp"],
                        },
                        "access": {"workspace_ids": [identities["operator"]["workspace_id"]]},
                        "bindings": [
                            {
                                "remote_name": "inventory_lookup",
                                "contract": {
                                    "name": "inventory_lookup",
                                    "description": "Synthetic CF2 inventory lookup.",
                                    "read_only": True,
                                    "idempotent": True,
                                    "policy_decision": "require_approval",
                                },
                            }
                        ],
                    }
                ]
            },
        )
    finally:
        engine.dispose()


def fixture_response(payload: dict[str, Any]) -> dict[str, Any]:
    """Respond from actual tool outputs, never from an expected document/citation ID."""
    assert payload["model"] == "cf2-offline"
    task = next(
        json.loads(item["content"][0]["text"])
        for item in payload["input"]
        if item.get("role") == "user" and item["content"][0]["text"].startswith('{"case":')
    )
    results = [
        json.loads(item["output"])
        for item in payload["input"]
        if item.get("type") == "function_call_output"
    ]
    output: list[dict[str, Any]]
    if len(results) < 2:
        name = "kb_search" if not results else "inventory_lookup"
        arguments = (
            {"knowledge_base_id": task["kb_id"], "query": "CF2 hatch blue", "top_k": 1}
            if not results
            else {"item_id": task["case"]}
        )
        output = [
            {
                "type": "function_call",
                "id": f"fc_{task['case']}_{len(results)}",
                "call_id": f"call_{task['case']}_{len(results)}",
                "name": name,
                "arguments": json.dumps(arguments, sort_keys=True),
                "status": "completed",
            }
        ]
    else:
        assert len(results) == 2
        assert [result["tool_name"] for result in results] == ["kb_search", "inventory_lookup"]
        citation = results[0]["result"]["results"][0]
        text = json.dumps(
            {
                "fixture_answer": citation["content"],
                "citation": citation["citation"],
                "inventory": results[1]["result"],
            },
            sort_keys=True,
        )
        output = [
            {
                "type": "message",
                "id": "msg_cf2",
                "role": "assistant",
                "status": "completed",
                "content": [{"type": "output_text", "text": text}],
            }
        ]
    return {
        "model": payload["model"],
        "status": "completed",
        "output": output,
        "usage": {"input_tokens": 3, "output_tokens": 1},
    }


def instrument_provider() -> None:
    import httpx
    import kernel_runtime.router as router
    from kernel_providers import LLMRequest, LLMResponse, OpenAIProvider
    from kernel_rag.embeddings import create_embedding_provider
    from kernel_runtime import ExecutionLimits, RetryPolicy
    from kernel_runtime.retry import RetryDelayPolicy

    embedding = create_embedding_provider()
    save(
        f"effective-{os.environ['CF2_ROLE']}.json",
        {
            "limits": ExecutionLimits.from_env().model_dump(mode="json"),
            "retry": asdict(RetryPolicy()),
            "retry_delay": asdict(RetryDelayPolicy()),
            "embedding": {"model": embedding.model, "dimensions": embedding.dimensions},
            "provider_route": "openai:cf2-offline",
            "fallbacks": [],
            "transport": "httpx.MockTransport in the real OpenAI adapter",
            "auth": True,
            "queue": "redis",
            "objects": "local",
        },
    )

    class CapturedProvider(OpenAIProvider):
        async def complete(self, request: LLMRequest) -> LLMResponse:
            def transport(wire: httpx.Request) -> httpx.Response:
                assert str(wire.url) == "https://cf2.invalid/v1/responses"
                payload = json.loads(wire.content)
                response = fixture_response(payload)
                append(
                    "provider.jsonl",
                    {
                        "service": os.environ["CF2_ROLE"],
                        "run_id": request.metadata["run_id"],
                        "normalized_request": request.model_dump(mode="json"),
                        "wire_request": payload,
                        "wire_sha256": digest(payload),
                        "tool_schema_sha256": digest(payload["tools"]),
                        "response": response,
                    },
                )
                return httpx.Response(200, json=response)

            # Only the provider transport is substituted. Production serialization/parsing runs.
            provider = OpenAIProvider(
                api_key="synthetic-cf2-not-a-credential",
                base_url="https://cf2.invalid/v1",
                transport=httpx.MockTransport(transport),
            )
            return await provider.complete(request)

    patch.object(router, "OpenAIProvider", CapturedProvider).start()


def mcp() -> None:
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("cf2-counted-inventory")

    @server.tool()
    def inventory_lookup(item_id: str) -> dict[str, str]:
        """Return synthetic inventory; count actual invocations across process restarts."""
        append("effects.jsonl", {"item_id": item_id})
        return {"item_id": item_id, "availability": "synthetic-only"}

    server.run(transport="stdio")


def main() -> None:
    os.umask(0o077)
    mode = sys.argv.pop(1)
    if mode == "mcp":
        # The MCP client supplies a deliberately reduced environment, not DB credentials.
        mcp()
        return
    guard()
    if mode == "bootstrap":
        bootstrap()
        return
    instrument_provider()
    if mode == "api":
        from agent_kernel_api.main import main as entrypoint
    elif mode == "worker":
        from agent_kernel_worker.main import main as entrypoint
    else:
        raise ValueError("Unknown fixture entrypoint")
    entrypoint()


if __name__ == "__main__":
    main()

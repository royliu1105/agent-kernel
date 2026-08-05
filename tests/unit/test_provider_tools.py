from typing import Any

from kernel_core import RiskLevel
from kernel_providers import LLMResponse, LLMToolCall
from kernel_runtime import (
    persist_provider_tool_calls,
    tool_metadata_to_llm_tool_definition,
    tool_registry_to_llm_tool_definitions,
)
from kernel_storage import AgentRepository, RunRepository, ToolCallRepository
from kernel_tools import ToolMetadata, ToolRegistry
from sqlalchemy.orm import Session, sessionmaker


def test_tool_metadata_to_llm_tool_definition_copies_provider_visible_schema() -> None:
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
        "additionalProperties": False,
    }
    metadata = ToolMetadata(
        name="kb_search",
        description="Search the knowledge base.",
        input_schema=input_schema,
        output_schema={"type": "object"},
        risk_level=RiskLevel.READ_ONLY,
    )

    definition = tool_metadata_to_llm_tool_definition(metadata)
    input_schema["properties"]["query"]["description"] = "mutated later"

    assert definition.name == "kb_search"
    assert definition.description == "Search the knowledge base."
    assert definition.input_schema == {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
        "additionalProperties": False,
    }


def test_tool_registry_to_llm_tool_definitions_filters_disabled_tools() -> None:
    registry = ToolRegistry()
    registry.register(_StaticTool(name="enabled_tool", enabled=True))
    registry.register(_StaticTool(name="disabled_tool", enabled=False))

    definitions = tool_registry_to_llm_tool_definitions(registry)

    assert [definition.name for definition in definitions] == ["enabled_tool"]


def test_persist_provider_tool_calls_records_known_tool_metadata(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    registry = ToolRegistry()
    registry.register(_StaticTool(name="kb_search", enabled=True, risk_level=RiskLevel.READ_ONLY))
    raw_provider_payload = {
        "type": "function_call",
        "call_id": "call_001",
        "name": "kb_search",
        "arguments": '{"query":"alpha"}',
    }
    response = LLMResponse(
        provider="openai",
        model="gpt-4.1-mini",
        text="",
        tool_calls=(
            LLMToolCall(
                id="call_001",
                name="kb_search",
                arguments={"query": "alpha"},
                raw=raw_provider_payload,
            ),
        ),
    )
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="native-tool-agent")
        run = RunRepository(session).create(agent_id=agent.id, input_payload={"task": "search"})

        persisted = persist_provider_tool_calls(
            running=run,
            response=response,
            tool_call_repository=ToolCallRepository(session),
            tool_registry=registry,
        )
        events = RunRepository(session).list_events(run.id)

    assert len(persisted) == 1
    assert persisted[0].tool_name == "kb_search"
    assert persisted[0].arguments == {"query": "alpha"}
    assert persisted[0].risk_level is RiskLevel.READ_ONLY
    assert persisted[0].provider_name == "openai"
    assert persisted[0].provider_tool_call_id == "call_001"
    assert persisted[0].raw_provider_payload == raw_provider_payload
    assert events[-1].payload["provider_name"] == "openai"


def test_persist_provider_tool_calls_marks_unknown_tool_dangerous(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    response = LLMResponse(
        provider="openai",
        model="gpt-4.1-mini",
        text="",
        tool_calls=(
            LLMToolCall(
                id="call_unknown",
                name="unknown_tool",
                arguments={},
                raw={"type": "function_call"},
            ),
        ),
    )
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="native-tool-agent")
        run = RunRepository(session).create(agent_id=agent.id, input_payload={"task": "search"})

        persisted = persist_provider_tool_calls(
            running=run,
            response=response,
            tool_call_repository=ToolCallRepository(session),
            tool_registry=ToolRegistry(),
        )

    assert persisted[0].risk_level is RiskLevel.DANGEROUS


class _StaticTool:
    def __init__(
        self,
        *,
        name: str,
        enabled: bool,
        risk_level: RiskLevel = RiskLevel.READ_ONLY,
    ) -> None:
        self._metadata = ToolMetadata(
            name=name,
            description=f"{name} description.",
            input_schema={"type": "object"},
            enabled=enabled,
            risk_level=risk_level,
        )

    @property
    def metadata(self) -> ToolMetadata:
        return self._metadata

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return arguments

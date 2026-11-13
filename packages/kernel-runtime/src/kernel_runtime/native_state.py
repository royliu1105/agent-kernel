"""Trusted execution bounds and private, versioned model continuation state."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from time import monotonic
from typing import Any, Literal
from uuid import UUID

from kernel_core import Run
from kernel_providers import LLMRequest, LLMResponse
from pydantic import BaseModel, ConfigDict, Field


class ExecutionLimitError(RuntimeError):
    def __init__(self, dimension: str) -> None:
        self.error_type = f"execution_{dimension}_limit"
        super().__init__(f"Execution {dimension.replace('_', ' ')} limit reached.")


class ExecutionLimits(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

    max_model_calls: int = Field(default=8, ge=1, le=256, strict=True)
    max_tool_calls: int = Field(default=16, ge=0, le=1024, strict=True)
    max_active_seconds: float = Field(default=300.0, gt=0, le=86400)
    max_history_bytes: int = Field(default=1048576, ge=64, le=16777216, strict=True)
    max_total_tokens: int = Field(default=64000, ge=1, le=64000000, strict=True)
    max_output_tokens: int = Field(default=4096, ge=1, le=1000000, strict=True)
    max_estimated_cost: float | None = Field(default=None, gt=0)

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> ExecutionLimits:
        values = os.environ if env is None else env
        fields: dict[str, Any] = {}
        for name in cls.model_fields:
            raw = values.get(f"AGENT_KERNEL_{name.upper()}")
            if raw is not None and raw.strip():
                fields[name] = (
                    float(raw) if name in {"max_active_seconds", "max_estimated_cost"} else int(raw)
                )
        return cls(**fields)

    def tightened(self, current: ExecutionLimits) -> ExecutionLimits:
        result = self.model_dump()
        for key, value in current.model_dump().items():
            if value is not None:
                result[key] = value if result[key] is None else min(value, result[key])
        return ExecutionLimits.model_validate(result)


class NativeState(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    version: Literal[1] = 1
    run_id: UUID
    limits: ExecutionLimits
    request: LLMRequest
    model_ref: str
    provider_name: str = ""
    memory_output: dict[str, Any] | None = None
    tool_contracts: dict[str, str] = Field(default_factory=dict)
    model_calls: int = Field(default=0, ge=0)
    tool_calls: int = Field(default=0, ge=0)
    elapsed_seconds: float = Field(default=0, ge=0)
    model_latency_ms: int = Field(default=0, ge=0)
    fallback_used: bool = False
    response: LLMResponse | None = None
    pending_tool_ids: list[UUID] = Field(default_factory=list)
    next_tool_index: int = Field(default=0, ge=0)
    seen_call_ids: list[str] = Field(default_factory=list)
    last_tool_summary: dict[str, Any] | None = None

    def serialized(self) -> dict[str, Any]:
        payload = self.model_dump(mode="json")
        if len(json.dumps(payload, allow_nan=False).encode()) > self.limits.max_history_bytes:
            raise ExecutionLimitError("history_bytes")
        return payload


class ExecutionBudget:
    """Active time excludes approval waiting and survives checkpoint restoration."""

    def __init__(self, state: NativeState) -> None:
        self.state = state
        self._tick = monotonic()

    def tick(self) -> None:
        now = monotonic()
        self.state.elapsed_seconds += max(0, now - self._tick)
        self._tick = now

    def remaining_seconds(self) -> float:
        self.tick()
        remaining = self.state.limits.max_active_seconds - self.state.elapsed_seconds
        if remaining <= 0:
            raise ExecutionLimitError("active_time")
        return remaining

    def check(self, run: Run, *, continuation: bool = True) -> None:
        self.remaining_seconds()
        tokens = run.input_tokens_total + run.output_tokens_total
        if tokens > self.state.limits.max_total_tokens or (
            continuation and tokens == self.state.limits.max_total_tokens
        ):
            raise ExecutionLimitError("tokens")
        limit = self.state.limits.max_estimated_cost
        if limit is not None and (
            run.estimated_cost_total > limit or (continuation and run.estimated_cost_total == limit)
        ):
            raise ExecutionLimitError("estimated_cost")
        self.state.serialized()

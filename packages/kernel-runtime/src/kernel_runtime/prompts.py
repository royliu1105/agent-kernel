"""Prompt version registry baseline."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from kernel_core import utc_now
from pydantic import BaseModel, ConfigDict, Field


class PromptVersion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID = Field(default_factory=uuid4)
    name: str
    version: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class PromptRegistry:
    """In-memory immutable prompt version registry."""

    def __init__(self) -> None:
        self._versions: dict[tuple[str, str], PromptVersion] = {}
        self._latest_by_name: dict[str, PromptVersion] = {}

    def register(self, prompt: PromptVersion) -> PromptVersion:
        key = (prompt.name, prompt.version)
        if key in self._versions:
            raise ValueError(f"Prompt {prompt.name!r} version {prompt.version!r} already exists.")
        self._versions[key] = prompt
        self._latest_by_name[prompt.name] = prompt
        return prompt

    def get(self, *, name: str, version: str) -> PromptVersion | None:
        return self._versions.get((name, version))

    def latest(self, *, name: str) -> PromptVersion | None:
        return self._latest_by_name.get(name)

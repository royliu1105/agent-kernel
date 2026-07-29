"""Scoped memory retrieval and context rendering."""

from __future__ import annotations

import json
from dataclasses import dataclass
from uuid import UUID

from kernel_core import MemoryItem, MemoryType
from kernel_storage import MemoryRepository


@dataclass(frozen=True)
class MemoryContext:
    items: tuple[MemoryItem, ...]

    @property
    def item_ids(self) -> tuple[UUID, ...]:
        return tuple(item.id for item in self.items)

    def to_prompt_text(self) -> str:
        if not self.items:
            return "Relevant memory: none."

        lines = ["Relevant memory:"]
        for index, item in enumerate(self.items, start=1):
            content = json.dumps(item.content, sort_keys=True)
            lines.append(
                " ".join(
                    [
                        f"{index}.",
                        f"type={item.type.value}",
                        f"scope={item.scope}",
                        f"confidence={item.confidence:.2f}",
                        f"content={content}",
                    ]
                )
            )
        return "\n".join(lines)

    def to_event_payload(self) -> dict[str, object]:
        return {
            "item_count": len(self.items),
            "item_ids": [str(item.id) for item in self.items],
            "scopes": sorted({item.scope for item in self.items}),
            "types": sorted({item.type.value for item in self.items}),
        }

    def to_output_payload(self) -> dict[str, object]:
        return {
            "used": bool(self.items),
            "item_count": len(self.items),
            "item_ids": [str(item.id) for item in self.items],
        }


class MemoryRetrievalService:
    """Retrieve explicit scoped memory for runtime context injection."""

    def retrieve(
        self,
        *,
        repository: MemoryRepository,
        scopes: tuple[str, ...],
        types: tuple[MemoryType, ...] | None = None,
        limit: int = 10,
    ) -> MemoryContext:
        if not scopes:
            raise ValueError("At least one memory scope is required.")
        if limit < 1:
            raise ValueError("Memory retrieval limit must be at least 1.")

        items_by_id: dict[UUID, MemoryItem] = {}
        for scope in scopes:
            if types is None:
                for item in repository.list(scope=scope, limit=limit):
                    items_by_id[item.id] = item
                continue
            for memory_type in types:
                for item in repository.list(scope=scope, type=memory_type, limit=limit):
                    items_by_id[item.id] = item

        items = sorted(items_by_id.values(), key=lambda item: item.created_at, reverse=True)
        return MemoryContext(items=tuple(items[:limit]))

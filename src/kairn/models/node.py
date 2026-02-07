"""Node model for the knowledge graph."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class Node(BaseModel):
    """A node in the knowledge graph."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    namespace: str = "knowledge"
    type: str
    name: str
    description: str | None = None
    properties: dict | None = None
    tags: list[str] | None = None
    created_by: str | None = None
    visibility: str = "workspace"
    source_type: str | None = None
    source_ref: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str | None = None
    deleted_at: str | None = None

    def to_storage(self) -> dict:
        return self.model_dump()

    def to_response(self, *, detail: str = "summary") -> dict[str, Any]:
        data: dict[str, Any] = {"_v": "1.0", "id": self.id, "name": self.name, "type": self.type}
        if detail != "summary":
            data.update(
                {
                    "namespace": self.namespace,
                    "description": self.description,
                    "properties": self.properties,
                    "tags": self.tags,
                    "visibility": self.visibility,
                    "source_type": self.source_type,
                    "created_at": self.created_at,
                    "updated_at": self.updated_at,
                }
            )
        return data

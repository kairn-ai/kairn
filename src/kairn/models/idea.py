"""Idea model with lifecycle management."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field

VALID_STATUSES = {"draft", "evaluating", "approved", "implementing", "done", "archived"}


class Idea(BaseModel):
    """An idea with status lifecycle and graph integration."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str
    status: str = "draft"
    category: str | None = None
    score: float | None = None
    properties: dict | None = None
    created_by: str | None = None
    visibility: str = "private"
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str | None = None

    def to_storage(self) -> dict:
        return self.model_dump()

    def to_response(self, *, detail: str = "summary") -> dict:
        data = {
            "_v": "1.0",
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "score": self.score,
        }
        if detail != "summary":
            data.update(
                {
                    "category": self.category,
                    "properties": self.properties,
                    "visibility": self.visibility,
                    "created_at": self.created_at,
                    "updated_at": self.updated_at,
                }
            )
        return data

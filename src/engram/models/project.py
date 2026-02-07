"""Project and progress models."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field

VALID_PHASES = {"planning", "active", "paused", "done"}


class Project(BaseModel):
    """A tracked project with lifecycle phases."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    phase: str = "planning"
    goals: list[str] | None = None
    active: bool = False
    created_by: str | None = None
    stakeholders: list[str] | None = None
    success_metrics: list[str] | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str | None = None

    def to_storage(self) -> dict:
        return self.model_dump()

    def to_response(self, *, detail: str = "summary") -> dict:
        data = {
            "_v": "1.0",
            "id": self.id,
            "name": self.name,
            "phase": self.phase,
            "active": self.active,
        }
        if detail != "summary":
            data.update(
                {
                    "goals": self.goals,
                    "stakeholders": self.stakeholders,
                    "success_metrics": self.success_metrics,
                    "created_at": self.created_at,
                    "updated_at": self.updated_at,
                }
            )
        return data


class ProgressEntry(BaseModel):
    """A progress or failure log entry."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    project_id: str
    type: str  # "progress" or "failure"
    action: str
    result: str | None = None
    next_step: str | None = None
    created_by: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_storage(self) -> dict:
        return self.model_dump()

    def to_response(self) -> dict:
        return {
            "_v": "1.0",
            "id": self.id,
            "type": self.type,
            "action": self.action,
            "result": self.result,
            "next_step": self.next_step,
            "created_at": self.created_at,
        }

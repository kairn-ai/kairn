"""Project Memory engine for lifecycle and progress tracking."""

import logging
from typing import ClassVar

from kairn.events.bus import EventBus
from kairn.events.types import EventType
from kairn.models.project import VALID_PHASES, ProgressEntry, Project
from kairn.storage.base import StorageBackend

logger = logging.getLogger(__name__)


class ProjectMemory:
    """Manages project lifecycle and progress logging."""

    # Phase transition rules: from_phase → allowed_to_phases
    _PHASE_TRANSITIONS: ClassVar[dict[str, set[str]]] = {
        "planning": {"active"},
        "active": {"paused", "done"},
        "paused": {"active", "done"},
        "done": set(),  # Final state
    }

    def __init__(self, store: StorageBackend, event_bus: EventBus) -> None:
        """Initialize ProjectMemory.

        Args:
            store: Storage backend for persistence
            event_bus: Event bus for emitting events
        """
        self._store = store
        self._event_bus = event_bus

    async def create_project(
        self,
        *,
        name: str,
        goals: list[str] | None = None,
        stakeholders: list[str] | None = None,
        success_metrics: list[str] | None = None,
    ) -> Project:
        """Create a new project.

        Args:
            name: Project name (required, cannot be empty)
            goals: Optional list of project goals
            stakeholders: Optional list of stakeholders
            success_metrics: Optional list of success metrics

        Returns:
            Created Project instance

        Raises:
            ValueError: If name is empty or whitespace-only
        """
        if not name or not name.strip():
            raise ValueError("Project name cannot be empty")

        project = Project(
            name=name.strip(),
            phase="planning",
            goals=goals or [],
            stakeholders=stakeholders or [],
            success_metrics=success_metrics or [],
            active=False,
        )

        await self._store.insert_project(project.to_storage())
        logger.info("Created project: %s (id=%s)", project.name, project.id)

        await self._event_bus.emit(
            EventType.PROJECT_CREATED,
            {"project_id": project.id, "name": project.name},
        )

        return project

    async def get_project(self, project_id: str) -> Project | None:
        """Get a project by ID.

        Args:
            project_id: Project identifier

        Returns:
            Project instance if found, None otherwise
        """
        data = await self._store.get_project(project_id)
        if not data:
            return None

        return Project(**data)

    async def update_project(self, project_id: str, **updates) -> Project | None:
        """Update a project.

        Args:
            project_id: Project identifier
            **updates: Fields to update (name, phase, goals, etc.)

        Returns:
            Updated Project instance if found, None otherwise

        Raises:
            ValueError: If phase transition is invalid or phase value is invalid
        """
        current = await self.get_project(project_id)
        if not current:
            return None

        # Validate phase transition if phase is being updated
        if "phase" in updates:
            new_phase = updates["phase"]

            # Validate phase value
            if new_phase not in VALID_PHASES:
                raise ValueError(f"Invalid phase: {new_phase}. Must be one of {VALID_PHASES}")

            # Check if transition is allowed
            if not self._is_valid_transition(current.phase, new_phase):
                raise ValueError(f"Invalid phase transition: {current.phase} → {new_phase}")

        # Update the project
        updated_data = await self._store.update_project(project_id, updates)
        if not updated_data:
            return None

        updated = Project(**updated_data)
        logger.info("Updated project: %s (id=%s)", updated.name, project_id)

        await self._event_bus.emit(
            EventType.PROJECT_UPDATED,
            {"project_id": project_id},
        )

        return updated

    async def list_projects(self, *, active_only: bool = False) -> list[Project]:
        """List all projects.

        Args:
            active_only: If True, return only active projects

        Returns:
            List of Project instances
        """
        projects_data = await self._store.list_projects(active_only=active_only)
        return [Project(**data) for data in projects_data]

    async def set_active_project(self, project_id: str) -> bool:
        """Set a project as active, deactivating all others.

        Args:
            project_id: Project identifier to activate

        Returns:
            True if successful, False if project not found
        """
        result = await self._store.set_active_project(project_id)
        if not result:
            return False

        logger.info("Activated project: id=%s", project_id)

        await self._event_bus.emit(
            EventType.PROJECT_ACTIVATED,
            {"project_id": project_id},
        )

        return True

    async def log_progress(
        self,
        *,
        project_id: str,
        action: str,
        result: str | None = None,
        next_step: str | None = None,
    ) -> ProgressEntry:
        """Log a progress entry for a project.

        Args:
            project_id: Project identifier
            action: Action description
            result: Optional result description
            next_step: Optional next step description

        Returns:
            Created ProgressEntry instance
        """
        entry = ProgressEntry(
            project_id=project_id,
            type="progress",
            action=action,
            result=result,
            next_step=next_step,
        )

        await self._store.insert_progress(entry.to_storage())
        logger.info("Logged progress for project %s: %s", project_id, action)

        await self._event_bus.emit(
            EventType.PROGRESS_LOGGED,
            {"project_id": project_id, "type": "progress"},
        )

        return entry

    async def log_failure(
        self,
        *,
        project_id: str,
        action: str,
        result: str | None = None,
        next_step: str | None = None,
    ) -> ProgressEntry:
        """Log a failure entry for a project.

        Args:
            project_id: Project identifier
            action: Action description
            result: Optional result/error description
            next_step: Optional next step/recovery description

        Returns:
            Created ProgressEntry instance
        """
        entry = ProgressEntry(
            project_id=project_id,
            type="failure",
            action=action,
            result=result,
            next_step=next_step,
        )

        await self._store.insert_progress(entry.to_storage())
        logger.warning("Logged failure for project %s: %s", project_id, action)

        await self._event_bus.emit(
            EventType.PROGRESS_LOGGED,
            {"project_id": project_id, "type": "failure"},
        )

        return entry

    async def get_progress(
        self,
        project_id: str,
        *,
        entry_type: str | None = None,
        limit: int = 10,
    ) -> list[ProgressEntry]:
        """Get progress entries for a project.

        Args:
            project_id: Project identifier
            entry_type: Optional filter by type ("progress" or "failure")
            limit: Maximum number of entries to return (default: 10)

        Returns:
            List of ProgressEntry instances
        """
        entries_data = await self._store.get_progress(
            project_id,
            entry_type=entry_type,
            limit=limit,
        )
        return [ProgressEntry(**data) for data in entries_data]

    def _is_valid_transition(self, from_phase: str, to_phase: str) -> bool:
        """Check if a phase transition is valid.

        Args:
            from_phase: Current phase
            to_phase: Target phase

        Returns:
            True if transition is allowed, False otherwise
        """
        # Same phase is always allowed (no-op)
        if from_phase == to_phase:
            return True

        allowed_transitions = self._PHASE_TRANSITIONS.get(from_phase, set())
        return to_phase in allowed_transitions

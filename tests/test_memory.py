"""Tests for Project Memory engine."""

import pytest

from engram.core.memory import ProjectMemory
from engram.events.bus import EventBus
from engram.events.types import EventType
from engram.models.project import VALID_PHASES


@pytest.fixture
async def event_bus():
    """Create event bus for testing."""
    return EventBus()


@pytest.fixture
async def memory(store, event_bus):
    """Create ProjectMemory instance."""
    return ProjectMemory(store, event_bus)


@pytest.mark.asyncio
async def test_create_project_minimal(memory):
    """Test creating a project with minimal required fields."""
    project = await memory.create_project(name="Test Project")

    assert project is not None
    assert project.name == "Test Project"
    assert project.phase == "planning"
    assert project.active is False
    assert project.goals == []
    assert project.stakeholders == []
    assert project.success_metrics == []
    assert isinstance(project.created_at, str)
    assert project.updated_at is None


@pytest.mark.asyncio
async def test_create_project_with_all_fields(memory):
    """Test creating a project with all optional fields."""
    project = await memory.create_project(
        name="Full Project",
        goals=["Goal 1", "Goal 2"],
        stakeholders=["Alice", "Bob"],
        success_metrics=["Metric 1", "Metric 2"]
    )

    assert project.name == "Full Project"
    assert project.goals == ["Goal 1", "Goal 2"]
    assert project.stakeholders == ["Alice", "Bob"]
    assert project.success_metrics == ["Metric 1", "Metric 2"]


@pytest.mark.asyncio
async def test_create_project_emits_event(memory, event_bus):
    """Test that creating a project emits PROJECT_CREATED event."""
    events = []

    async def capture_event(event_type, data):
        events.append({"type": event_type, "data": data})

    event_bus.on(EventType.PROJECT_CREATED, capture_event)

    project = await memory.create_project(name="Event Test")

    assert len(events) == 1
    assert events[0]["type"] == EventType.PROJECT_CREATED
    assert events[0]["data"]["project_id"] == project.id
    assert events[0]["data"]["name"] == "Event Test"


@pytest.mark.asyncio
async def test_get_project_exists(memory):
    """Test getting an existing project."""
    created = await memory.create_project(name="Get Test")
    retrieved = await memory.get_project(created.id)

    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.name == created.name


@pytest.mark.asyncio
async def test_get_project_not_found(memory):
    """Test getting a non-existent project returns None."""
    result = await memory.get_project("non-existent-id")
    assert result is None


@pytest.mark.asyncio
async def test_update_project_basic_fields(memory):
    """Test updating basic project fields."""
    project = await memory.create_project(name="Original")

    updated = await memory.update_project(
        project.id,
        name="Updated",
        goals=["New Goal"],
        stakeholders=["Charlie"]
    )

    assert updated is not None
    assert updated.name == "Updated"
    assert updated.goals == ["New Goal"]
    assert updated.stakeholders == ["Charlie"]


@pytest.mark.asyncio
async def test_update_project_not_found(memory):
    """Test updating a non-existent project returns None."""
    result = await memory.update_project("non-existent-id", name="Fail")
    assert result is None


@pytest.mark.asyncio
async def test_update_project_emits_event(memory, event_bus):
    """Test that updating a project emits PROJECT_UPDATED event."""
    events = []

    async def capture_event(event_type, data):
        events.append({"type": event_type, "data": data})

    event_bus.on(EventType.PROJECT_UPDATED, capture_event)

    project = await memory.create_project(name="Update Event Test")
    await memory.update_project(project.id, name="Changed")

    assert len(events) == 1
    assert events[0]["type"] == EventType.PROJECT_UPDATED
    assert events[0]["data"]["project_id"] == project.id


@pytest.mark.asyncio
async def test_phase_transition_planning_to_active(memory):
    """Test valid transition: planning → active."""
    project = await memory.create_project(name="Phase Test")
    assert project.phase == "planning"

    updated = await memory.update_project(project.id, phase="active")
    assert updated is not None
    assert updated.phase == "active"


@pytest.mark.asyncio
async def test_phase_transition_active_to_paused(memory):
    """Test valid transition: active → paused."""
    project = await memory.create_project(name="Pause Test")
    await memory.update_project(project.id, phase="active")

    updated = await memory.update_project(project.id, phase="paused")
    assert updated is not None
    assert updated.phase == "paused"


@pytest.mark.asyncio
async def test_phase_transition_active_to_done(memory):
    """Test valid transition: active → done."""
    project = await memory.create_project(name="Done Test")
    await memory.update_project(project.id, phase="active")

    updated = await memory.update_project(project.id, phase="done")
    assert updated is not None
    assert updated.phase == "done"


@pytest.mark.asyncio
async def test_phase_transition_paused_to_active(memory):
    """Test valid transition: paused → active."""
    project = await memory.create_project(name="Resume Test")
    await memory.update_project(project.id, phase="active")
    await memory.update_project(project.id, phase="paused")

    updated = await memory.update_project(project.id, phase="active")
    assert updated is not None
    assert updated.phase == "active"


@pytest.mark.asyncio
async def test_phase_transition_paused_to_done(memory):
    """Test valid transition: paused → done."""
    project = await memory.create_project(name="Paused Done Test")
    await memory.update_project(project.id, phase="active")
    await memory.update_project(project.id, phase="paused")

    updated = await memory.update_project(project.id, phase="done")
    assert updated is not None
    assert updated.phase == "done"


@pytest.mark.asyncio
async def test_phase_transition_planning_to_paused_invalid(memory):
    """Test invalid transition: planning → paused."""
    project = await memory.create_project(name="Invalid Test")

    with pytest.raises(ValueError, match="Invalid phase transition"):
        await memory.update_project(project.id, phase="paused")


@pytest.mark.asyncio
async def test_phase_transition_done_to_active_invalid(memory):
    """Test invalid transition: done → active (done is final)."""
    project = await memory.create_project(name="Final Test")
    await memory.update_project(project.id, phase="active")
    await memory.update_project(project.id, phase="done")

    with pytest.raises(ValueError, match="Invalid phase transition"):
        await memory.update_project(project.id, phase="active")


@pytest.mark.asyncio
async def test_phase_transition_done_to_paused_invalid(memory):
    """Test invalid transition: done → paused (done is final)."""
    project = await memory.create_project(name="Final Pause Test")
    await memory.update_project(project.id, phase="active")
    await memory.update_project(project.id, phase="done")

    with pytest.raises(ValueError, match="Invalid phase transition"):
        await memory.update_project(project.id, phase="paused")


@pytest.mark.asyncio
async def test_list_projects_empty(memory):
    """Test listing projects when none exist."""
    projects = await memory.list_projects()
    assert projects == []


@pytest.mark.asyncio
async def test_list_projects_multiple(memory):
    """Test listing multiple projects."""
    await memory.create_project(name="Project 1")
    await memory.create_project(name="Project 2")
    await memory.create_project(name="Project 3")

    projects = await memory.list_projects()
    assert len(projects) == 3
    assert {p.name for p in projects} == {"Project 1", "Project 2", "Project 3"}


@pytest.mark.asyncio
async def test_list_projects_active_only(memory):
    """Test listing only active projects."""
    p1 = await memory.create_project(name="Active 1")
    p2 = await memory.create_project(name="Inactive")
    p3 = await memory.create_project(name="Active 2")

    await memory.set_active_project(p1.id)
    await memory.set_active_project(p3.id)

    active_projects = await memory.list_projects(active_only=True)
    assert len(active_projects) == 1
    assert active_projects[0].name == "Active 2"


@pytest.mark.asyncio
async def test_set_active_project_success(memory):
    """Test setting a project as active."""
    project = await memory.create_project(name="Activate Test")
    assert project.active is False

    result = await memory.set_active_project(project.id)
    assert result is True

    updated = await memory.get_project(project.id)
    assert updated.active is True


@pytest.mark.asyncio
async def test_set_active_project_not_found(memory):
    """Test setting a non-existent project as active returns False."""
    result = await memory.set_active_project("non-existent-id")
    assert result is False


@pytest.mark.asyncio
async def test_set_active_project_deactivates_others(memory):
    """Test that activating a project deactivates all others."""
    p1 = await memory.create_project(name="Project 1")
    p2 = await memory.create_project(name="Project 2")
    p3 = await memory.create_project(name="Project 3")

    await memory.set_active_project(p1.id)
    await memory.set_active_project(p2.id)

    p1_updated = await memory.get_project(p1.id)
    p2_updated = await memory.get_project(p2.id)
    p3_updated = await memory.get_project(p3.id)

    assert p1_updated.active is False
    assert p2_updated.active is True
    assert p3_updated.active is False


@pytest.mark.asyncio
async def test_set_active_project_emits_event(memory, event_bus):
    """Test that activating a project emits PROJECT_ACTIVATED event."""
    events = []

    async def capture_event(event_type, data):
        events.append({"type": event_type, "data": data})

    event_bus.on(EventType.PROJECT_ACTIVATED, capture_event)

    project = await memory.create_project(name="Activate Event Test")
    await memory.set_active_project(project.id)

    assert len(events) == 1
    assert events[0]["type"] == EventType.PROJECT_ACTIVATED
    assert events[0]["data"]["project_id"] == project.id


@pytest.mark.asyncio
async def test_log_progress_minimal(memory):
    """Test logging progress with minimal fields."""
    project = await memory.create_project(name="Progress Test")

    entry = await memory.log_progress(
        project_id=project.id,
        action="Completed feature X"
    )

    assert entry is not None
    assert entry.project_id == project.id
    assert entry.type == "progress"
    assert entry.action == "Completed feature X"
    assert entry.result is None
    assert entry.next_step is None
    assert isinstance(entry.created_at, str)


@pytest.mark.asyncio
async def test_log_progress_with_all_fields(memory):
    """Test logging progress with all optional fields."""
    project = await memory.create_project(name="Full Progress Test")

    entry = await memory.log_progress(
        project_id=project.id,
        action="Implemented authentication",
        result="All tests passing",
        next_step="Add authorization layer"
    )

    assert entry.action == "Implemented authentication"
    assert entry.result == "All tests passing"
    assert entry.next_step == "Add authorization layer"


@pytest.mark.asyncio
async def test_log_failure(memory):
    """Test logging a failure entry."""
    project = await memory.create_project(name="Failure Test")

    entry = await memory.log_failure(
        project_id=project.id,
        action="Deploy to production",
        result="Database migration failed",
        next_step="Rollback and fix migration script"
    )

    assert entry.type == "failure"
    assert entry.action == "Deploy to production"
    assert entry.result == "Database migration failed"


@pytest.mark.asyncio
async def test_log_progress_emits_event(memory, event_bus):
    """Test that logging progress emits PROGRESS_LOGGED event."""
    events = []

    async def capture_event(event_type, data):
        events.append({"type": event_type, "data": data})

    event_bus.on(EventType.PROGRESS_LOGGED, capture_event)

    project = await memory.create_project(name="Event Test")
    await memory.log_progress(project_id=project.id, action="Test action")

    assert len(events) == 1
    assert events[0]["type"] == EventType.PROGRESS_LOGGED
    assert events[0]["data"]["project_id"] == project.id
    assert events[0]["data"]["type"] == "progress"


@pytest.mark.asyncio
async def test_log_failure_emits_event(memory, event_bus):
    """Test that logging failure emits PROGRESS_LOGGED event."""
    events = []

    async def capture_event(event_type, data):
        events.append({"type": event_type, "data": data})

    event_bus.on(EventType.PROGRESS_LOGGED, capture_event)

    project = await memory.create_project(name="Failure Event Test")
    await memory.log_failure(project_id=project.id, action="Test failure")

    assert len(events) == 1
    assert events[0]["type"] == EventType.PROGRESS_LOGGED
    assert events[0]["data"]["project_id"] == project.id
    assert events[0]["data"]["type"] == "failure"


@pytest.mark.asyncio
async def test_get_progress_all_entries(memory):
    """Test getting all progress entries for a project."""
    project = await memory.create_project(name="Progress History Test")

    await memory.log_progress(project_id=project.id, action="Action 1")
    await memory.log_progress(project_id=project.id, action="Action 2")
    await memory.log_failure(project_id=project.id, action="Action 3")

    entries = await memory.get_progress(project.id)
    assert len(entries) == 3
    assert {e.action for e in entries} == {"Action 1", "Action 2", "Action 3"}


@pytest.mark.asyncio
async def test_get_progress_filter_by_type(memory):
    """Test filtering progress entries by type."""
    project = await memory.create_project(name="Filter Test")

    await memory.log_progress(project_id=project.id, action="Progress 1")
    await memory.log_progress(project_id=project.id, action="Progress 2")
    await memory.log_failure(project_id=project.id, action="Failure 1")

    progress_only = await memory.get_progress(project.id, entry_type="progress")
    assert len(progress_only) == 2
    assert all(e.type == "progress" for e in progress_only)

    failures_only = await memory.get_progress(project.id, entry_type="failure")
    assert len(failures_only) == 1
    assert all(e.type == "failure" for e in failures_only)


@pytest.mark.asyncio
async def test_get_progress_limit(memory):
    """Test limiting the number of progress entries returned."""
    project = await memory.create_project(name="Limit Test")

    for i in range(15):
        await memory.log_progress(project_id=project.id, action=f"Action {i}")

    entries = await memory.get_progress(project.id, limit=5)
    assert len(entries) == 5


@pytest.mark.asyncio
async def test_get_progress_default_limit(memory):
    """Test that default limit is 10."""
    project = await memory.create_project(name="Default Limit Test")

    for i in range(15):
        await memory.log_progress(project_id=project.id, action=f"Action {i}")

    entries = await memory.get_progress(project.id)
    assert len(entries) == 10


@pytest.mark.asyncio
async def test_get_progress_empty(memory):
    """Test getting progress for a project with no entries."""
    project = await memory.create_project(name="Empty Progress Test")

    entries = await memory.get_progress(project.id)
    assert entries == []


@pytest.mark.asyncio
async def test_create_project_empty_name_raises(memory):
    """Test that creating a project with empty name raises ValueError."""
    with pytest.raises(ValueError, match="Project name cannot be empty"):
        await memory.create_project(name="")


@pytest.mark.asyncio
async def test_create_project_whitespace_name_raises(memory):
    """Test that creating a project with whitespace-only name raises ValueError."""
    with pytest.raises(ValueError, match="Project name cannot be empty"):
        await memory.create_project(name="   ")


@pytest.mark.asyncio
async def test_phase_transition_invalid_phase_value(memory):
    """Test that updating to an invalid phase raises ValueError."""
    project = await memory.create_project(name="Invalid Phase Test")

    with pytest.raises(ValueError, match="Invalid phase"):
        await memory.update_project(project.id, phase="invalid_phase")

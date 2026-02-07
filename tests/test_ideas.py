"""Tests for Idea Lifecycle Engine."""

import pytest

from engram.core.ideas import IdeaEngine
from engram.events.bus import EventBus
from engram.events.types import EventType
from engram.models.idea import Idea
from engram.models.node import Node


@pytest.fixture
async def engine(store):
    """Create IdeaEngine with event bus."""
    bus = EventBus()
    return IdeaEngine(store, bus)


@pytest.mark.asyncio
async def test_create_idea_minimal(engine):
    """Test creating idea with minimal required fields."""
    idea = await engine.create(title="Test Idea")

    assert idea is not None
    assert idea.title == "Test Idea"
    assert idea.status == "draft"
    assert idea.visibility == "private"
    assert idea.category is None
    assert idea.score is None


@pytest.mark.asyncio
async def test_create_idea_full(engine):
    """Test creating idea with all fields."""
    idea = await engine.create(
        title="Full Idea",
        category="feature",
        score=8.5,
        properties={"priority": "high"},
        visibility="workspace"
    )

    assert idea.title == "Full Idea"
    assert idea.status == "draft"
    assert idea.category == "feature"
    assert idea.score == 8.5
    assert idea.properties == {"priority": "high"}
    assert idea.visibility == "workspace"


@pytest.mark.asyncio
async def test_create_idea_emits_event(engine, store):
    """Test that creating an idea emits IDEA_CREATED event."""
    events = []

    async def handler(event_type, data):
        events.append({"type": event_type, "data": data})

    engine._event_bus.on(EventType.IDEA_CREATED, handler)

    idea = await engine.create(title="Event Test")

    assert len(events) == 1
    assert events[0]["type"] == EventType.IDEA_CREATED
    assert events[0]["data"]["idea_id"] == idea.id
    assert events[0]["data"]["title"] == "Event Test"


@pytest.mark.asyncio
async def test_get_idea_exists(engine):
    """Test getting an existing idea."""
    created = await engine.create(title="Get Test")
    retrieved = await engine.get(created.id)

    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.title == created.title


@pytest.mark.asyncio
async def test_get_idea_not_exists(engine):
    """Test getting non-existent idea returns None."""
    result = await engine.get("nonexistent-id")
    assert result is None


@pytest.mark.asyncio
async def test_update_idea_title(engine):
    """Test updating idea title."""
    idea = await engine.create(title="Original")
    updated = await engine.update(idea.id, title="Updated")

    assert updated is not None
    assert updated.title == "Updated"
    assert updated.id == idea.id


@pytest.mark.asyncio
async def test_update_idea_score(engine):
    """Test updating idea score."""
    idea = await engine.create(title="Score Test")
    updated = await engine.update(idea.id, score=9.0)

    assert updated is not None
    assert updated.score == 9.0


@pytest.mark.asyncio
async def test_update_idea_category(engine):
    """Test updating idea category."""
    idea = await engine.create(title="Category Test")
    updated = await engine.update(idea.id, category="bug-fix")

    assert updated is not None
    assert updated.category == "bug-fix"


@pytest.mark.asyncio
async def test_update_idea_properties(engine):
    """Test updating idea properties."""
    idea = await engine.create(title="Props Test", properties={"a": 1})
    updated = await engine.update(idea.id, properties={"b": 2})

    assert updated is not None
    assert updated.properties == {"b": 2}


@pytest.mark.asyncio
async def test_update_idea_emits_event(engine):
    """Test that updating idea emits IDEA_UPDATED event."""
    events = []

    async def handler(event_type, data):
        events.append({"type": event_type, "data": data})

    engine._event_bus.on(EventType.IDEA_UPDATED, handler)

    idea = await engine.create(title="Update Event Test")
    await engine.update(idea.id, title="Changed", score=7.0)

    assert len(events) == 1
    assert events[0]["type"] == EventType.IDEA_UPDATED
    assert events[0]["data"]["idea_id"] == idea.id
    assert set(events[0]["data"]["changes"]) == {"title", "score"}


@pytest.mark.asyncio
async def test_update_nonexistent_idea(engine):
    """Test updating non-existent idea returns None."""
    result = await engine.update("nonexistent-id", title="Fail")
    assert result is None


@pytest.mark.asyncio
async def test_list_ideas_empty(engine):
    """Test listing ideas when none exist."""
    ideas = await engine.list_ideas()
    assert ideas == []


@pytest.mark.asyncio
async def test_list_ideas_basic(engine):
    """Test listing all ideas."""
    await engine.create(title="Idea 1")
    await engine.create(title="Idea 2")
    await engine.create(title="Idea 3")

    ideas = await engine.list_ideas()
    assert len(ideas) == 3
    assert all(isinstance(i, Idea) for i in ideas)


@pytest.mark.asyncio
async def test_list_ideas_filter_by_status(engine):
    """Test filtering ideas by status."""
    idea1 = await engine.create(title="Draft")
    idea2 = await engine.create(title="Approved")
    # Must go through evaluating first
    await engine.update(idea2.id, status="evaluating")
    await engine.update(idea2.id, status="approved")

    drafts = await engine.list_ideas(status="draft")
    approved = await engine.list_ideas(status="approved")

    assert len(drafts) == 1
    assert drafts[0].id == idea1.id
    assert len(approved) == 1
    assert approved[0].id == idea2.id


@pytest.mark.asyncio
async def test_list_ideas_filter_by_category(engine):
    """Test filtering ideas by category."""
    await engine.create(title="Feature", category="feature")
    await engine.create(title="Bug", category="bug")
    await engine.create(title="No Category")

    features = await engine.list_ideas(category="feature")
    bugs = await engine.list_ideas(category="bug")

    assert len(features) == 1
    assert features[0].category == "feature"
    assert len(bugs) == 1
    assert bugs[0].category == "bug"


@pytest.mark.asyncio
async def test_list_ideas_limit(engine):
    """Test limiting number of ideas returned."""
    for i in range(5):
        await engine.create(title=f"Idea {i}")

    ideas = await engine.list_ideas(limit=3)
    assert len(ideas) == 3


@pytest.mark.asyncio
async def test_list_ideas_offset(engine):
    """Test offsetting ideas list."""
    for i in range(5):
        await engine.create(title=f"Idea {i}")

    # Get all ideas to establish the order
    all_ideas = await engine.list_ideas(limit=10, offset=0)
    assert len(all_ideas) == 5

    # Now test offset
    ideas_with_offset = await engine.list_ideas(limit=10, offset=2)
    assert len(ideas_with_offset) == 3

    # The offset ideas should match the last 3 from the full list
    expected_ids = [i.id for i in all_ideas[2:]]
    returned_ids = [i.id for i in ideas_with_offset]
    assert returned_ids == expected_ids


@pytest.mark.asyncio
async def test_list_ideas_combined_filters(engine):
    """Test combining status and category filters."""
    await engine.create(title="Draft Feature", category="feature")
    idea2 = await engine.create(title="Approved Feature", category="feature")
    # Must go through evaluating first
    await engine.update(idea2.id, status="evaluating")
    await engine.update(idea2.id, status="approved")
    await engine.create(title="Draft Bug", category="bug")

    results = await engine.list_ideas(status="approved", category="feature")

    assert len(results) == 1
    assert results[0].id == idea2.id


@pytest.mark.asyncio
async def test_status_transition_draft_to_evaluating(engine):
    """Test valid transition from draft to evaluating."""
    idea = await engine.create(title="Transition Test")
    updated = await engine.update(idea.id, status="evaluating")

    assert updated is not None
    assert updated.status == "evaluating"


@pytest.mark.asyncio
async def test_status_transition_evaluating_to_approved(engine):
    """Test valid transition from evaluating to approved."""
    idea = await engine.create(title="Eval Test")
    await engine.update(idea.id, status="evaluating")
    updated = await engine.update(idea.id, status="approved")

    assert updated is not None
    assert updated.status == "approved"


@pytest.mark.asyncio
async def test_status_transition_evaluating_to_archived(engine):
    """Test valid transition from evaluating to archived (rejection)."""
    idea = await engine.create(title="Reject Test")
    await engine.update(idea.id, status="evaluating")
    updated = await engine.update(idea.id, status="archived")

    assert updated is not None
    assert updated.status == "archived"


@pytest.mark.asyncio
async def test_status_transition_approved_to_implementing(engine):
    """Test valid transition from approved to implementing."""
    idea = await engine.create(title="Implement Test")
    await engine.update(idea.id, status="evaluating")
    await engine.update(idea.id, status="approved")
    updated = await engine.update(idea.id, status="implementing")

    assert updated is not None
    assert updated.status == "implementing"


@pytest.mark.asyncio
async def test_status_transition_implementing_to_done(engine):
    """Test valid transition from implementing to done."""
    idea = await engine.create(title="Done Test")
    await engine.update(idea.id, status="evaluating")
    await engine.update(idea.id, status="approved")
    await engine.update(idea.id, status="implementing")
    updated = await engine.update(idea.id, status="done")

    assert updated is not None
    assert updated.status == "done"


@pytest.mark.asyncio
async def test_status_transition_done_to_archived(engine):
    """Test valid transition from done to archived."""
    idea = await engine.create(title="Archive Test")
    await engine.update(idea.id, status="evaluating")
    await engine.update(idea.id, status="approved")
    await engine.update(idea.id, status="implementing")
    await engine.update(idea.id, status="done")
    updated = await engine.update(idea.id, status="archived")

    assert updated is not None
    assert updated.status == "archived"


@pytest.mark.asyncio
async def test_status_transition_archived_to_draft(engine):
    """Test valid transition from archived back to draft (revival)."""
    idea = await engine.create(title="Revive Test")
    await engine.update(idea.id, status="evaluating")
    await engine.update(idea.id, status="archived")
    updated = await engine.update(idea.id, status="draft")

    assert updated is not None
    assert updated.status == "draft"


@pytest.mark.asyncio
async def test_status_transition_invalid_skip_step(engine):
    """Test invalid transition that skips a step."""
    idea = await engine.create(title="Skip Test")

    with pytest.raises(ValueError, match="Invalid status transition"):
        await engine.update(idea.id, status="approved")


@pytest.mark.asyncio
async def test_status_transition_invalid_backward(engine):
    """Test invalid backward transition."""
    idea = await engine.create(title="Backward Test")
    await engine.update(idea.id, status="evaluating")
    await engine.update(idea.id, status="approved")
    await engine.update(idea.id, status="implementing")
    await engine.update(idea.id, status="done")

    with pytest.raises(ValueError, match="Invalid status transition"):
        await engine.update(idea.id, status="implementing")


@pytest.mark.asyncio
async def test_status_transition_invalid_from_approved(engine):
    """Test invalid transition from approved to draft."""
    idea = await engine.create(title="Invalid Test")
    await engine.update(idea.id, status="evaluating")
    await engine.update(idea.id, status="approved")

    with pytest.raises(ValueError, match="Invalid status transition"):
        await engine.update(idea.id, status="draft")


@pytest.mark.asyncio
async def test_advance_draft_to_evaluating(engine):
    """Test advancing from draft to evaluating."""
    idea = await engine.create(title="Advance Test")
    advanced = await engine.advance(idea.id)

    assert advanced is not None
    assert advanced.status == "evaluating"


@pytest.mark.asyncio
async def test_advance_evaluating_to_approved(engine):
    """Test advancing from evaluating to approved."""
    idea = await engine.create(title="Advance Test")
    await engine.advance(idea.id)
    advanced = await engine.advance(idea.id)

    assert advanced is not None
    assert advanced.status == "approved"


@pytest.mark.asyncio
async def test_advance_approved_to_implementing(engine):
    """Test advancing from approved to implementing."""
    idea = await engine.create(title="Advance Test")
    await engine.advance(idea.id)
    await engine.advance(idea.id)
    advanced = await engine.advance(idea.id)

    assert advanced is not None
    assert advanced.status == "implementing"


@pytest.mark.asyncio
async def test_advance_implementing_to_done(engine):
    """Test advancing from implementing to done."""
    idea = await engine.create(title="Advance Test")
    await engine.advance(idea.id)
    await engine.advance(idea.id)
    await engine.advance(idea.id)
    advanced = await engine.advance(idea.id)

    assert advanced is not None
    assert advanced.status == "done"


@pytest.mark.asyncio
async def test_advance_from_done_returns_none(engine):
    """Test advancing from done returns None (no next step)."""
    idea = await engine.create(title="Advance Test")
    await engine.advance(idea.id)
    await engine.advance(idea.id)
    await engine.advance(idea.id)
    await engine.advance(idea.id)

    result = await engine.advance(idea.id)
    assert result is None


@pytest.mark.asyncio
async def test_advance_from_archived_returns_none(engine):
    """Test advancing from archived returns None."""
    idea = await engine.create(title="Advance Test")
    await engine.update(idea.id, status="evaluating")
    await engine.update(idea.id, status="archived")

    result = await engine.advance(idea.id)
    assert result is None


@pytest.mark.asyncio
async def test_advance_nonexistent_idea(engine):
    """Test advancing non-existent idea returns None."""
    result = await engine.advance("nonexistent-id")
    assert result is None


@pytest.mark.asyncio
async def test_link_to_node_creates_edge(engine, store):
    """Test linking idea to a node creates an edge."""
    # Create idea
    idea = await engine.create(title="Linked Idea")

    # Create target node
    node = Node(
        namespace="test",
        type="concept",
        name="Target Node",
        visibility="workspace"
    )
    await store.insert_node(node.to_storage())

    # Link idea to node
    edge = await engine.link_to_node(idea.id, node.id)

    assert edge is not None
    assert edge.source_id == idea.id
    assert edge.target_id == node.id
    assert edge.type == "idea_relates_to"


@pytest.mark.asyncio
async def test_link_to_node_custom_edge_type(engine, store):
    """Test linking with custom edge type."""
    idea = await engine.create(title="Custom Edge")
    node = Node(
        namespace="test",
        type="concept",
        name="Target",
        visibility="workspace"
    )
    await store.insert_node(node.to_storage())

    edge = await engine.link_to_node(idea.id, node.id, edge_type="idea_implements")

    assert edge is not None
    assert edge.type == "idea_implements"


@pytest.mark.asyncio
async def test_link_to_node_creates_idea_node(engine, store):
    """Test linking idea creates a node for the idea in the graph."""
    idea = await engine.create(title="Graph Idea", visibility="workspace")
    node = Node(
        namespace="test",
        type="concept",
        name="Target",
        visibility="workspace"
    )
    await store.insert_node(node.to_storage())

    await engine.link_to_node(idea.id, node.id)

    # Verify idea node was created
    idea_node_data = await store.get_node(idea.id)
    assert idea_node_data is not None
    assert idea_node_data["type"] == "idea"
    assert idea_node_data["name"] == "Graph Idea"
    assert idea_node_data["namespace"] == "idea"
    assert idea_node_data["visibility"] == "workspace"


@pytest.mark.asyncio
async def test_link_to_node_idea_not_found(engine, store):
    """Test linking non-existent idea returns None."""
    node = Node(
        namespace="test",
        type="concept",
        name="Target",
        visibility="workspace"
    )
    await store.insert_node(node.to_storage())

    result = await engine.link_to_node("nonexistent-idea", node.id)
    assert result is None


@pytest.mark.asyncio
async def test_link_to_node_target_not_found(engine):
    """Test linking to non-existent node returns None."""
    idea = await engine.create(title="Orphan")
    result = await engine.link_to_node(idea.id, "nonexistent-node")
    assert result is None


@pytest.mark.asyncio
async def test_link_to_node_reuses_existing_idea_node(engine, store):
    """Test that linking idea twice reuses the same idea node."""
    idea = await engine.create(title="Reuse Test")

    node1 = Node(namespace="test", type="concept", name="Target 1", visibility="workspace")
    node2 = Node(namespace="test", type="concept", name="Target 2", visibility="workspace")
    await store.insert_node(node1.to_storage())
    await store.insert_node(node2.to_storage())

    await engine.link_to_node(idea.id, node1.id)
    await engine.link_to_node(idea.id, node2.id)

    # Verify only one idea node was created
    idea_node_data = await store.get_node(idea.id)
    assert idea_node_data is not None


@pytest.mark.asyncio
async def test_create_idea_empty_title_fails(engine):
    """Test creating idea with empty title raises error."""
    with pytest.raises(ValueError, match="title cannot be empty"):
        await engine.create(title="")


@pytest.mark.asyncio
async def test_create_idea_invalid_status_fails(engine):
    """Test creating idea with invalid status in properties."""
    # Note: create() doesn't accept status parameter, always starts as "draft"
    # This test ensures we can't bypass via properties
    idea = await engine.create(title="Test", properties={"status": "invalid"})
    assert idea.status == "draft"  # Should ignore invalid status in properties

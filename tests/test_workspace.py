"""Tests for workspace metadata store and multi-workspace isolation."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

import aiosqlite
import pytest

from engram.storage.metadata_store import MetadataStore


@pytest.fixture
async def metadata_store(tmp_path: Path) -> AsyncGenerator[MetadataStore, None]:
    """Create and initialize a metadata store for testing."""
    db_path = tmp_path / "metadata.db"
    store = MetadataStore(db_path)
    await store.initialize()
    yield store
    await store.close()


class TestUserCRUD:
    """Test user CRUD operations."""

    async def test_create_user(self, metadata_store: MetadataStore) -> None:
        user = await metadata_store.create_user(
            user_id="user-1",
            email="test@example.com",
            name="Test User",
        )

        assert user["user_id"] == "user-1"
        assert user["email"] == "test@example.com"
        assert user["name"] == "Test User"
        assert user["auth_provider"] == "local"
        assert user["is_active"] is True

    async def test_get_user(self, metadata_store: MetadataStore) -> None:
        await metadata_store.create_user("user-1", "test@example.com", "Test User")
        user = await metadata_store.get_user("user-1")

        assert user is not None
        assert user["user_id"] == "user-1"
        assert user["email"] == "test@example.com"

    async def test_get_user_not_found(self, metadata_store: MetadataStore) -> None:
        user = await metadata_store.get_user("nonexistent")
        assert user is None

    async def test_update_user(self, metadata_store: MetadataStore) -> None:
        await metadata_store.create_user("user-1", "test@example.com", "Test User")
        updated = await metadata_store.update_user("user-1", {"name": "Updated Name"})

        assert updated is not None
        assert updated["name"] == "Updated Name"
        assert updated["email"] == "test@example.com"

    async def test_list_users(self, metadata_store: MetadataStore) -> None:
        await metadata_store.create_user("user-1", "u1@example.com", "User One")
        await metadata_store.create_user("user-2", "u2@example.com", "User Two")

        users = await metadata_store.list_users()
        assert len(users) == 2
        assert any(u["user_id"] == "user-1" for u in users)
        assert any(u["user_id"] == "user-2" for u in users)

    async def test_duplicate_email(self, metadata_store: MetadataStore) -> None:
        await metadata_store.create_user("user-1", "test@example.com", "User One")

        with pytest.raises(aiosqlite.IntegrityError):
            await metadata_store.create_user("user-2", "test@example.com", "User Two")


class TestOrganizationCRUD:
    """Test organization CRUD operations."""

    async def test_create_org(self, metadata_store: MetadataStore) -> None:
        await metadata_store.create_user("user-1", "test@example.com", "Test User")
        org = await metadata_store.create_org(
            org_id="org-1",
            name="Test Org",
            created_by="user-1",
        )

        assert org["org_id"] == "org-1"
        assert org["name"] == "Test Org"
        assert org["created_by"] == "user-1"
        assert org["plan_tier"] == "free"
        assert org["max_workspaces"] == 1
        assert org["max_members"] == 1

    async def test_get_org(self, metadata_store: MetadataStore) -> None:
        await metadata_store.create_user("user-1", "test@example.com", "Test User")
        await metadata_store.create_org("org-1", "Test Org", "user-1")
        org = await metadata_store.get_org("org-1")

        assert org is not None
        assert org["org_id"] == "org-1"

    async def test_list_orgs(self, metadata_store: MetadataStore) -> None:
        await metadata_store.create_user("user-1", "test@example.com", "Test User")
        await metadata_store.create_org("org-1", "Org One", "user-1")
        await metadata_store.create_org("org-2", "Org Two", "user-1")

        orgs = await metadata_store.list_orgs()
        assert len(orgs) == 2

    async def test_create_org_invalid_user(self, metadata_store: MetadataStore) -> None:
        with pytest.raises(aiosqlite.IntegrityError):
            await metadata_store.create_org("org-1", "Test Org", "nonexistent-user")


class TestWorkspaceCRUD:
    """Test workspace CRUD operations."""

    async def test_create_workspace(self, metadata_store: MetadataStore) -> None:
        await metadata_store.create_user("user-1", "test@example.com", "Test User")
        await metadata_store.create_org("org-1", "Test Org", "user-1")

        workspace = await metadata_store.create_workspace(
            workspace_id="ws-1",
            org_id="org-1",
            name="Test Workspace",
            created_by="user-1",
            description="A test workspace",
        )

        assert workspace["workspace_id"] == "ws-1"
        assert workspace["org_id"] == "org-1"
        assert workspace["name"] == "Test Workspace"
        assert workspace["visibility"] == "org"

    async def test_get_workspace(self, metadata_store: MetadataStore) -> None:
        await metadata_store.create_user("user-1", "test@example.com", "Test User")
        await metadata_store.create_org("org-1", "Test Org", "user-1")
        await metadata_store.create_workspace("ws-1", "org-1", "Test Workspace", "user-1")

        workspace = await metadata_store.get_workspace("ws-1")
        assert workspace is not None
        assert workspace["workspace_id"] == "ws-1"

    async def test_list_workspaces(self, metadata_store: MetadataStore) -> None:
        await metadata_store.create_user("user-1", "test@example.com", "Test User")
        await metadata_store.create_org("org-1", "Test Org", "user-1")
        await metadata_store.create_workspace("ws-1", "org-1", "Workspace One", "user-1")
        await metadata_store.create_workspace("ws-2", "org-1", "Workspace Two", "user-1")

        workspaces = await metadata_store.list_workspaces()
        assert len(workspaces) == 2

    async def test_list_workspaces_for_user(self, metadata_store: MetadataStore) -> None:
        await metadata_store.create_user("user-1", "u1@example.com", "User One")
        await metadata_store.create_user("user-2", "u2@example.com", "User Two")
        await metadata_store.create_org("org-1", "Test Org", "user-1")
        await metadata_store.create_workspace("ws-1", "org-1", "Workspace One", "user-1")
        await metadata_store.create_workspace("ws-2", "org-1", "Workspace Two", "user-1")

        await metadata_store.add_member("ws-1", "user-1", "owner")
        await metadata_store.add_member("ws-2", "user-2", "contributor")

        user1_workspaces = await metadata_store.list_workspaces_for_user("user-1")
        assert len(user1_workspaces) == 1
        assert user1_workspaces[0]["workspace_id"] == "ws-1"

        user2_workspaces = await metadata_store.list_workspaces_for_user("user-2")
        assert len(user2_workspaces) == 1
        assert user2_workspaces[0]["workspace_id"] == "ws-2"


class TestWorkspaceMembers:
    """Test workspace member management."""

    async def test_add_member(self, metadata_store: MetadataStore) -> None:
        await metadata_store.create_user("user-1", "u1@example.com", "User One")
        await metadata_store.create_user("user-2", "u2@example.com", "User Two")
        await metadata_store.create_org("org-1", "Test Org", "user-1")
        await metadata_store.create_workspace("ws-1", "org-1", "Test Workspace", "user-1")

        member = await metadata_store.add_member("ws-1", "user-2", "contributor")
        assert member["workspace_id"] == "ws-1"
        assert member["user_id"] == "user-2"
        assert member["role"] == "contributor"

    async def test_get_members(self, metadata_store: MetadataStore) -> None:
        await metadata_store.create_user("user-1", "u1@example.com", "User One")
        await metadata_store.create_user("user-2", "u2@example.com", "User Two")
        await metadata_store.create_org("org-1", "Test Org", "user-1")
        await metadata_store.create_workspace("ws-1", "org-1", "Test Workspace", "user-1")

        await metadata_store.add_member("ws-1", "user-1", "owner")
        await metadata_store.add_member("ws-1", "user-2", "reader")

        members = await metadata_store.get_members("ws-1")
        assert len(members) == 2
        assert any(m["user_id"] == "user-1" for m in members)
        assert any(m["user_id"] == "user-2" for m in members)

    async def test_get_member_role(self, metadata_store: MetadataStore) -> None:
        await metadata_store.create_user("user-1", "u1@example.com", "User One")
        await metadata_store.create_org("org-1", "Test Org", "user-1")
        await metadata_store.create_workspace("ws-1", "org-1", "Test Workspace", "user-1")
        await metadata_store.add_member("ws-1", "user-1", "owner")

        role = await metadata_store.get_member_role("ws-1", "user-1")
        assert role == "owner"

    async def test_get_member_role_not_member(self, metadata_store: MetadataStore) -> None:
        await metadata_store.create_user("user-1", "u1@example.com", "User One")
        await metadata_store.create_org("org-1", "Test Org", "user-1")
        await metadata_store.create_workspace("ws-1", "org-1", "Test Workspace", "user-1")

        role = await metadata_store.get_member_role("ws-1", "user-1")
        assert role is None

    async def test_remove_member(self, metadata_store: MetadataStore) -> None:
        await metadata_store.create_user("user-1", "u1@example.com", "User One")
        await metadata_store.create_user("user-2", "u2@example.com", "User Two")
        await metadata_store.create_org("org-1", "Test Org", "user-1")
        await metadata_store.create_workspace("ws-1", "org-1", "Test Workspace", "user-1")
        await metadata_store.add_member("ws-1", "user-2", "contributor")

        removed = await metadata_store.remove_member("ws-1", "user-2")
        assert removed is True

        members = await metadata_store.get_members("ws-1")
        assert not any(m["user_id"] == "user-2" for m in members)


class TestWorkspaceIsolation:
    """Test that knowledge in one workspace is not visible in another."""

    async def test_workspace_isolation_basic(self, metadata_store: MetadataStore) -> None:
        await metadata_store.create_user("user-1", "u1@example.com", "User One")
        await metadata_store.create_org("org-1", "Test Org", "user-1")
        await metadata_store.create_workspace("ws-a", "org-1", "Workspace A", "user-1")
        await metadata_store.create_workspace("ws-b", "org-1", "Workspace B", "user-1")

        await metadata_store.add_member("ws-a", "user-1", "owner")
        await metadata_store.add_member("ws-b", "user-1", "owner")

        user_workspaces = await metadata_store.list_workspaces_for_user("user-1")
        workspace_ids = {ws["workspace_id"] for ws in user_workspaces}

        assert "ws-a" in workspace_ids
        assert "ws-b" in workspace_ids
        assert len(workspace_ids) == 2

    async def test_user_can_only_see_their_workspaces(
        self, metadata_store: MetadataStore
    ) -> None:
        await metadata_store.create_user("user-1", "u1@example.com", "User One")
        await metadata_store.create_user("user-2", "u2@example.com", "User Two")
        await metadata_store.create_org("org-1", "Test Org", "user-1")
        await metadata_store.create_workspace("ws-a", "org-1", "Workspace A", "user-1")
        await metadata_store.create_workspace("ws-b", "org-1", "Workspace B", "user-1")

        await metadata_store.add_member("ws-a", "user-1", "owner")
        await metadata_store.add_member("ws-b", "user-2", "owner")

        user1_workspaces = await metadata_store.list_workspaces_for_user("user-1")
        user2_workspaces = await metadata_store.list_workspaces_for_user("user-2")

        assert len(user1_workspaces) == 1
        assert user1_workspaces[0]["workspace_id"] == "ws-a"

        assert len(user2_workspaces) == 1
        assert user2_workspaces[0]["workspace_id"] == "ws-b"

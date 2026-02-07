-- Kairn Central Metadata Schema (metadata.db)
-- Version: 1.0

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    email TEXT UNIQUE,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    auth_provider TEXT DEFAULT 'local',
    is_active BOOLEAN DEFAULT 1,
    last_active TEXT
);

CREATE TABLE IF NOT EXISTS organizations (
    org_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL REFERENCES users(user_id),
    plan_tier TEXT DEFAULT 'free' CHECK(plan_tier IN ('free', 'team', 'business')),
    max_workspaces INTEGER DEFAULT 1,
    max_members INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS workspaces (
    workspace_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL REFERENCES organizations(org_id),
    name TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL REFERENCES users(user_id),
    visibility TEXT DEFAULT 'org' CHECK(visibility IN ('private', 'team', 'org', 'public')),
    workspace_type TEXT DEFAULT 'project',
    repo_url TEXT,
    tech_stack TEXT
);

CREATE TABLE IF NOT EXISTS workspace_members (
    workspace_id TEXT NOT NULL REFERENCES workspaces(workspace_id),
    user_id TEXT NOT NULL REFERENCES users(user_id),
    role TEXT DEFAULT 'contributor' CHECK(role IN ('owner', 'maintainer', 'contributor', 'reader')),
    joined_at TEXT NOT NULL,
    PRIMARY KEY (workspace_id, user_id)
);

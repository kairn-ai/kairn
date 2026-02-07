"""Event type constants for Engram."""

from enum import StrEnum


class EventType(StrEnum):
    NODE_CREATED = "node.created"
    NODE_UPDATED = "node.updated"
    NODE_DELETED = "node.deleted"
    NODE_RESTORED = "node.restored"

    EDGE_CREATED = "edge.created"
    EDGE_DELETED = "edge.deleted"

    EXPERIENCE_CREATED = "experience.created"
    EXPERIENCE_ACCESSED = "experience.accessed"
    EXPERIENCE_PROMOTED = "experience.promoted"
    EXPERIENCE_PRUNED = "experience.pruned"

    PROJECT_CREATED = "project.created"
    PROJECT_UPDATED = "project.updated"
    PROJECT_ACTIVATED = "project.activated"

    PROGRESS_LOGGED = "progress.logged"

    IDEA_CREATED = "idea.created"
    IDEA_UPDATED = "idea.updated"

    KNOWLEDGE_LEARNED = "knowledge.learned"
    KNOWLEDGE_RECALLED = "knowledge.recalled"
    CROSSREF_FOUND = "crossref.found"

    ROUTE_UPDATED = "route.updated"

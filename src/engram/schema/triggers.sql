-- Engram FTS5 + Auto-Promotion Triggers
-- Applied AFTER workspace.sql tables are created
-- Version: 1.0

-- FTS5 full-text search for nodes
CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
    name, description, content=nodes, content_rowid=rowid
);

-- FTS5 sync triggers for nodes
CREATE TRIGGER IF NOT EXISTS nodes_fts_ai AFTER INSERT ON nodes BEGIN
    INSERT INTO nodes_fts(rowid, name, description)
    VALUES (new.rowid, new.name, new.description);
END;

CREATE TRIGGER IF NOT EXISTS nodes_fts_ad AFTER DELETE ON nodes BEGIN
    INSERT INTO nodes_fts(nodes_fts, rowid, name, description)
    VALUES('delete', old.rowid, old.name, old.description);
END;

CREATE TRIGGER IF NOT EXISTS nodes_fts_au AFTER UPDATE ON nodes BEGIN
    INSERT INTO nodes_fts(nodes_fts, rowid, name, description)
    VALUES('delete', old.rowid, old.name, old.description);
    INSERT INTO nodes_fts(rowid, name, description)
    VALUES (new.rowid, new.name, new.description);
END;

-- FTS5 full-text search for experiences
CREATE VIRTUAL TABLE IF NOT EXISTS experiences_fts USING fts5(
    content, context, content=experiences, content_rowid=rowid
);

-- FTS5 sync triggers for experiences
CREATE TRIGGER IF NOT EXISTS exp_fts_ai AFTER INSERT ON experiences BEGIN
    INSERT INTO experiences_fts(rowid, content, context)
    VALUES (new.rowid, new.content, new.context);
END;

CREATE TRIGGER IF NOT EXISTS exp_fts_ad AFTER DELETE ON experiences BEGIN
    INSERT INTO experiences_fts(experiences_fts, rowid, content, context)
    VALUES('delete', old.rowid, old.content, old.context);
END;

CREATE TRIGGER IF NOT EXISTS exp_fts_au AFTER UPDATE ON experiences BEGIN
    INSERT INTO experiences_fts(experiences_fts, rowid, content, context)
    VALUES('delete', old.rowid, old.content, old.context);
    INSERT INTO experiences_fts(rowid, content, context)
    VALUES (new.rowid, new.content, new.context);
END;

-- Experience auto-promotion flag trigger
-- When access_count reaches threshold, flag for application-level promotion
CREATE TRIGGER IF NOT EXISTS exp_auto_promote AFTER UPDATE OF access_count ON experiences
WHEN new.access_count >= 5 AND new.promoted_to_node_id IS NULL
BEGIN
    UPDATE experiences SET properties = json_set(COALESCE(properties, '{}'), '$.needs_promotion', 1)
    WHERE id = new.id;
END;

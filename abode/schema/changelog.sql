CREATE TABLE IF NOT EXISTS changelog (
    entity_id text,
    version integer,
    field text,
    value text,

    PRIMARY KEY (entity_id, version)
);
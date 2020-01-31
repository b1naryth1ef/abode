CREATE TABLE IF NOT EXISTS emoji (
    id BIGINT PRIMARY KEY,
    guild_id BIGINT,
    author_id BIGINT,
    name text,
    require_colons boolean,
    managed boolean,
    animated boolean,
    roles jsonb,
    created_at timestamp,
    deleted boolean
);
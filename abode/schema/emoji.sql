CREATE TABLE IF NOT EXISTS emoji (
    id text PRIMARY KEY,
    guild_id text,
    author_id text,
    name text,
    require_colons integer,
    managed integer,
    animated integer,
    roles text,
    created_at integer,
    
    -- currently unused
    deleted integer
);
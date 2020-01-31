CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS guilds (
    id BIGINT PRIMARY KEY,
    owner_id BIGINT,
    name text,
    icon text,

    -- materialized values
    is_currently_joined boolean

    -- -- unused as of now
    -- banner text,
    -- description text,
    -- features text,
    -- splash text,
    -- discovery_splash text
);

CREATE INDEX IF NOT EXISTS guilds_name_trgm ON guilds USING gin (name gin_trgm_ops);
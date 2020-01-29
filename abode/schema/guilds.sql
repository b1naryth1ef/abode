CREATE TABLE IF NOT EXISTS guilds (
    id text PRIMARY KEY,
    owner_id text,
    name text,
    icon text,

    -- materialized values
    is_currently_joined integer,

    -- unused as of now
    banner text,
    description text,
    features text,
    splash text,
    discovery_splash text
);
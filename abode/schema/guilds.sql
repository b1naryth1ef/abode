CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS guilds (
    id BIGINT PRIMARY KEY,
    owner_id BIGINT,
    name text,
    region text,
    icon text,
    is_currently_joined boolean,
    features jsonb,
    banner text,
    description text,
    splash text,
    discovery_splash text,
    premium_tier smallint,
    premium_subscription_count int
);

CREATE INDEX IF NOT EXISTS guilds_name_trgm ON guilds USING gin (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS guilds_owner_id_idx ON guilds (owner_id);
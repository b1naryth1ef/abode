CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS channels (
    id BIGINT PRIMARY KEY,
    type SMALLINT NOT NULL,
    name text,
    topic text,
    guild_id BIGINT,
    category_id BIGINT,
    position BIGINT,
    slowmode_delay BIGINT,
    overwrites jsonb,
    bitrate INT,
    user_limit SMALLINT,
    recipients jsonb,
    owner_id BIGINT,
    icon text
);

CREATE INDEX IF NOT EXISTS channels_name_trgm ON channels USING gin (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS channels_type_idx ON channels (type);
CREATE INDEX IF NOT EXISTS channels_guild_id_idx ON channels (guild_id);
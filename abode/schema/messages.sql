CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS messages (
    id BIGINT PRIMARY KEY,
    guild_id BIGINT,
    channel_id BIGINT NOT NULL,
    author_id BIGINT NOT NULL,
    webhook_id BIGINT,

    tts boolean NOT NULL,
    type integer NOT NULL,
    content text NOT NULL,
    embeds jsonb,
    mention_everyone boolean NOT NULL,
    flags integer NOT NULL,
    activity jsonb,
    application jsonb,

    created_at timestamp NOT NULL,
    edited_at timestamp,
    deleted boolean NOT NULL
);

CREATE INDEX IF NOT EXISTS messages_content_trgm ON messages USING gin (content gin_trgm_ops);
CREATE INDEX IF NOT EXISTS messages_content_fts ON messages USING gin (to_tsvector('english', content)); 
CREATE INDEX IF NOT EXISTS messages_guild_id_idx ON messages (guild_id);
CREATE INDEX IF NOT EXISTS messages_channel_id_idx ON messages (channel_id);
CREATE INDEX IF NOT EXISTS messages_author_id_idx ON messages (author_id);
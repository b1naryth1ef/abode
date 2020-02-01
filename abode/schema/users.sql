CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY,
    name text NOT NULL,
    discriminator smallint NOT NULL,
    avatar text,
    bot boolean,
    system boolean
);

CREATE INDEX IF NOT EXISTS users_name_trgm ON users USING gin (name gin_trgm_ops);
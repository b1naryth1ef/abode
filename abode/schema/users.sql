CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY,
    name text NOT NULL,
    discriminator smallint NOT NULL,
    avatar text,
    bot boolean,
    system boolean
);
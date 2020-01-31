from dataclasses import dataclass, fields
from typing import Optional
from . import (
    with_conn,
    build_insert_query,
    build_select_query,
    convert_to_type,
    Snowflake,
    BaseModel,
)


@dataclass
class Guild(BaseModel):
    id: Snowflake
    owner_id: Snowflake
    name: str
    icon: Optional[str]
    is_currently_joined: bool = None

    _pk = "id"
    _refs = {}
    _external_indexes = {}
    _fts = set()

    @classmethod
    def from_attrs(cls, guild, is_currently_joined=None):
        kwargs = {"is_currently_joined": is_currently_joined}
        for field in fields(cls):
            if not hasattr(guild, field.name):
                continue

            kwargs[field.name] = convert_to_type(getattr(guild, field.name), field.type)
        return cls(**kwargs)


@with_conn
async def upsert_guild(conn, guild, is_currently_joined=None):
    from .emoji import upsert_emoji

    new_guild = Guild.from_attrs(guild, is_currently_joined=is_currently_joined)

    # TODO: calculate diff
    existing_guild = await conn.fetchrow(
        build_select_query(new_guild, "id = $1"), new_guild.id
    )

    query, args = build_insert_query(new_guild, upsert=True)
    await conn.execute(query, *args)

    if existing_guild is not None:
        existing_guild = Guild.from_record(existing_guild)
        diff = list(new_guild.diff(existing_guild))
        if diff:
            print(f"[guilds] diff is {diff}")

    for emoji in guild.emojis:
        await upsert_emoji(emoji, conn=conn)

from dataclasses import dataclass, fields
from typing import Optional
from . import (
    with_cursor,
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
    is_currently_joined: bool

    _refs = {}
    _external_indexes = {}

    @classmethod
    def from_attrs(cls, guild, is_currently_joined=None):
        kwargs = {"is_currently_joined": is_currently_joined}
        for field in fields(cls):
            if not hasattr(guild, field.name):
                continue

            kwargs[field.name] = convert_to_type(getattr(guild, field.name), field.type)
        return cls(**kwargs)


@with_cursor
async def upsert_guild(cursor, guild, is_currently_joined=None):
    guild = Guild.from_attrs(guild, is_currently_joined=is_currently_joined)

    # TODO: calculate diff
    await cursor.execute(build_select_query(guild, "id = ?"), guild.id)
    existing_guild = await cursor.fetchone()

    query, args = build_insert_query(guild, upsert=True)
    await cursor.execute(query, *args)

    if existing_guild is not None:
        existing_guild = Guild.from_attrs(existing_guild)
        diff = list(guild.diff(existing_guild))
        if diff:
            print(f"[guilds] diff is {diff}")

from dataclasses import dataclass
from typing import Optional
from datetime import datetime
from . import (
    with_conn,
    build_insert_query,
    build_select_query,
    JSONB,
    Snowflake,
    BaseModel,
)
from .guilds import Guild


@dataclass
class Emoji(BaseModel):
    id: Snowflake
    guild_id: Snowflake
    author_id: Optional[Snowflake]
    name: str
    require_colons: bool
    animated: bool
    managed: bool
    roles: JSONB
    created_at: datetime
    deleted: bool

    _pk = "id"
    _table_name = "emoji"
    _refs = {"guild": (Guild, ("guild_id", "id"), True)}
    _fts = set()

    @classmethod
    def from_discord(cls, emoji, deleted=False):
        return cls(
            id=emoji.id,
            guild_id=emoji.guild.id,
            author_id=emoji.user.id if emoji.user else None,
            name=emoji.name,
            require_colons=bool(emoji.require_colons),
            managed=bool(emoji.managed),
            animated=bool(emoji.animated),
            roles=[str(i.id) for i in emoji.roles],
            created_at=emoji.created_at,
            deleted=deleted,
        )


@with_conn
async def upsert_emoji(conn, emoji):
    emoji = Emoji.from_discord(emoji)

    # TODO: calculate diff
    existing_emoji = await conn.fetchrow(build_select_query(emoji, "id = $1"), emoji.id)

    query, args = build_insert_query(emoji, upsert=True)
    await conn.execute(query, *args)

    if existing_emoji is not None:
        existing_emoji = Emoji.from_record(existing_emoji)
        diff = list(emoji.diff(existing_emoji))
        if diff:
            print(f"[emoji] diff is {diff}")

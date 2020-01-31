from dataclasses import dataclass, fields
from typing import Optional
from . import (
    with_cursor,
    build_insert_query,
    build_select_query,
    to_json_str,
    convert_to_type,
    FTS,
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
    roles: str
    created_at: int
    deleted: bool

    _table_name = "emoji"
    _refs = {"guild": (Guild, ("guild_id", "id"))}
    _external_indexes = {}

    @classmethod
    def from_discord(cls, emoji, deleted=False):
        return cls(
            id=str(emoji.id),
            guild_id=str(emoji.guild.id),
            author_id=str(emoji.user.id) if emoji.user else None,
            name=emoji.name,
            require_colons=bool(emoji.require_colons),
            managed=bool(emoji.managed),
            animated=bool(emoji.animated),
            roles=to_json_str([str(i.id) for i in emoji.roles]),
            created_at=int(emoji.created_at.timestamp()),
            deleted=deleted,
        )

    @classmethod
    def from_attrs(cls, instance, deleted=None):
        kwargs = {}
        for field in fields(cls):
            kwargs[field.name] = convert_to_type(
                getattr(instance, field.name), field.type
            )
        if deleted:
            kwargs["deleted"] = deleted
        return cls(**kwargs)


@with_cursor
async def upsert_emoji(cursor, emoji):
    emoji = Emoji.from_discord(emoji)

    # TODO: calculate diff
    await cursor.execute(build_select_query(emoji, "id = ?"), emoji.id)
    existing_emoji = await cursor.fetchone()

    query, args = build_insert_query(emoji, upsert=True)
    await cursor.execute(query, *args)

    if existing_emoji is not None:
        existing_emoji = Emoji.from_attrs(existing_emoji)
        diff = list(emoji.diff(existing_emoji))
        if diff:
            print(f"[emoji] diff is {diff}")

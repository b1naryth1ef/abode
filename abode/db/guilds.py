from dataclasses import dataclass, fields
from typing import Optional
from . import (
    with_conn,
    build_insert_query,
    build_select_query,
    convert_to_type,
    Snowflake,
    BaseModel,
    JSONB,
)
from .users import User


@dataclass
class Guild(BaseModel):
    id: Snowflake
    owner_id: Snowflake
    name: str
    region: str
    icon: Optional[str]
    features: JSONB
    banner: Optional[str]
    description: Optional[str]
    splash: Optional[str]
    discovery_splash: Optional[str]
    premium_tier: int
    premium_subscription_count: int
    is_currently_joined: bool = None

    _pk = "id"
    _refs = {"owner": (User, ("owner_id", "id"), True)}
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
    from .users import upsert_user
    from .channels import upsert_channel

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

    for channel in guild.channels:
        await upsert_channel(channel, conn=conn)

    for emoji in guild.emojis:
        await upsert_emoji(emoji, conn=conn)

    for member in guild.members:
        await upsert_user(member, conn=conn)

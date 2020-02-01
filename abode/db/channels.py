import discord
from dataclasses import dataclass
from typing import Optional
from .guilds import Guild
from .users import User
from . import (
    with_conn,
    build_insert_query,
    build_select_query,
    JSONB,
    Snowflake,
    BaseModel,
)


@dataclass
class Channel(BaseModel):
    id: Snowflake
    type: int

    name: Optional[str] = None
    topic: Optional[str] = None

    # Guild Specific
    guild_id: Optional[Snowflake] = None
    category_id: Optional[Snowflake] = None
    position: Optional[int] = None
    slowmode_delay: Optional[int] = None
    overwrites: Optional[JSONB] = None

    # Voice Specific
    bitrate: Optional[int] = None
    user_limit: Optional[int] = None

    # DMs
    recipients: Optional[JSONB] = None
    owner_id: Optional[Snowflake] = None
    icon: Optional[str] = None

    _pk = "id"
    _refs = {
        "guild": (Guild, ("guild_id", "id"), False),
        "owner": (User, ("owner_id", "id"), False),
    }
    _fts = set()

    @classmethod
    def from_discord(cls, channel):
        inst = cls(id=channel.id, type=channel.type.value)

        if isinstance(
            channel,
            (discord.TextChannel, discord.VoiceChannel, discord.CategoryChannel),
        ):
            inst.guild_id = channel.guild.id
            inst.name = channel.name
            inst.category_id = channel.category_id
            inst.position = channel.position
            inst.overwrites = {
                str(k.id): [i.value for i in v.pair()]
                for k, v in channel.overwrites.items()
            }

            if isinstance(channel, discord.TextChannel):
                inst.slowmode_delay = channel.slowmode_delay
                inst.topic = channel.topic
            elif isinstance(channel, discord.VoiceChannel):
                inst.bitrate = channel.bitrate
                inst.user_limit = channel.user_limit
        elif isinstance(channel, discord.DMChannel):
            inst.recipients = [channel.recipient.id]
        elif isinstance(channel, discord.GroupChannel):
            inst.recipients = [i.id for i in channel.recipients]
            inst.owner_id = channel.owner.id
            inst.icon = channel.icon
            inst.name = channel.name

        return inst


@with_conn
async def upsert_channel(conn, channel):
    new_channel = Channel.from_discord(channel)

    # TODO: calculate diff
    existing_channel = await conn.fetchrow(
        build_select_query(new_channel, "id = $1"), channel.id
    )

    query, args = build_insert_query(new_channel, upsert=True)
    await conn.execute(query, *args)

    if existing_channel is not None:
        existing_channel = Channel.from_record(existing_channel)
        diff = list(new_channel.diff(existing_channel))
        if diff:
            print(f"[channel] diff is {diff}")

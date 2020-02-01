from dataclasses import dataclass, fields
from datetime import datetime
from typing import Optional
from . import (
    with_conn,
    build_insert_query,
    convert_to_type,
    JSONB,
    Snowflake,
    BaseModel,
)
from .users import User, upsert_user
from .guilds import Guild


@dataclass
class Message(BaseModel):
    id: Snowflake
    channel_id: Snowflake
    guild_id: Optional[Snowflake]
    author_id: Optional[Snowflake]
    webhook_id: Optional[Snowflake]
    tts: bool
    type: int
    content: str
    embeds: Optional[JSONB]
    mention_everyone: bool
    flags: int
    activity: Optional[JSONB]
    application: Optional[JSONB]
    created_at: datetime
    edited_at: Optional[datetime]
    deleted: bool

    # TODO: eventually these could be types, but I am far too baked for that
    #   refactor at the moment.
    _pk = "id"
    _refs = {
        "guild": (Guild, ("guild_id", "id")),
        "author": (User, ("author_id", "id")),
    }
    _fts = {"content"}

    @classmethod
    def from_discord(cls, message, deleted=False):
        return cls(
            id=message.id,
            guild_id=message.guild.id if message.guild else None,
            channel_id=message.channel.id,
            author_id=message.author.id,
            webhook_id=message.webhook_id if message.webhook_id else None,
            tts=bool(message.tts),
            type=message.type.value,
            content=message.content,
            embeds=[i.to_dict() for i in message.embeds],
            mention_everyone=bool(message.mention_everyone),
            flags=message.flags.value,
            activity=message.activity,
            application=message.application,
            created_at=message.created_at,
            edited_at=message.edited_at,
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


@with_conn
async def insert_message(conn, message):
    new_message = Message.from_discord(message)

    query, args = build_insert_query(new_message, ignore_existing=True)
    try:
        await conn.execute(query, *args)
    except Exception:
        print(query)
        print(args)
        raise

    await upsert_user(message.author, conn=conn)


@with_conn
async def update_message(conn, message):
    pass

from dataclasses import dataclass, fields
from typing import Optional
from . import (
    with_cursor,
    build_insert_query,
    to_json_str,
    convert_to_type,
)
from .guilds import Guild


@dataclass
class Message:
    id: str
    guild_id: str
    channel_id: str
    author_id: Optional[str]
    webhook_id: Optional[str]
    tts: bool
    type: int
    content: str
    embeds: str
    mention_everyone: bool
    flags: int
    activity: str
    application: str
    created_at: int
    edited_at: Optional[int]
    deleted: bool

    # TODO: eventually these could be types, but I am far too baked for that
    #   refactor at the moment.
    _refs = {"guild": (Guild, ("guild_id", "id"))}
    _external_indexes = {"content": ("messages_fts", ("id", "rowid"))}

    @classmethod
    def from_discord(cls, message, deleted=False):
        return cls(
            id=str(message.id),
            guild_id=str(message.guild.id if message.guild else None),
            channel_id=str(message.channel.id),
            author_id=str(message.author.id),
            webhook_id=str(message.webhook_id) if message.webhook_id else None,
            tts=bool(message.tts),
            type=message.type.value,
            content=message.content,
            embeds=to_json_str([i.to_dict() for i in message.embeds]),
            mention_everyone=bool(message.mention_everyone),
            flags=message.flags.value,
            activity=to_json_str(message.activity),
            application=to_json_str(message.application),
            created_at=message.created_at.timestamp(),
            edited_at=message.edited_at.timestamp() if message.edited_at else None,
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

    def diff(self, other):
        for field in fields(self):
            if getattr(other, field.name) != getattr(self, field.name):
                yield {"field": field.name, "value": getattr(other, field.name)}


@with_cursor
async def insert_message(cursor, message):
    message = Message.from_discord(message)

    query, args = build_insert_query(message)
    try:
        await cursor.execute(query, *args)
    except Exception:
        print(query)
        print(args)
        raise


@with_cursor
async def update_message(cursor, message):
    pass

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


@dataclass
class User(BaseModel):
    id: Snowflake
    name: str
    discriminator: int
    avatar: Optional[str]
    bot: bool
    system: bool

    _pk = "id"
    _refs = {}
    _external_indexes = {}
    _fts = set()

    @classmethod
    def from_discord(cls, user):
        return cls(
            id=user.id,
            name=user.name,
            discriminator=int(user.discriminator),
            avatar=user.avatar,
            bot=user.bot,
            system=user.system,
        )


@with_conn
async def upsert_user(conn, user):
    user = User.from_discord(user)

    # TODO: calculate diff
    existing_user = await conn.fetchrow(build_select_query(user, "id = $1"), user.id)

    query, args = build_insert_query(user, upsert=True)
    await conn.execute(query, *args)

    if existing_user is not None:
        existing_user = User.from_record(existing_user)
        diff = list(user.diff(existing_user))
        if diff:
            print(f"[user] diff is {diff}")

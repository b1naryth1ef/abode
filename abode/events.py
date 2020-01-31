from abode.db.guilds import upsert_guild
from abode.db.messages import insert_message
from abode.db.emoji import upsert_emoji


async def on_ready(client):
    print("Connected!")
    for guild in client.guilds:
        print(f"Updating guild {guild.name}")
        await upsert_guild(guild, is_currently_joined=True)


async def on_guild_join(client, guild):
    await upsert_guild(guild, is_currently_joined=True)


async def on_guild_update(client, old, new):
    await upsert_guild(new, is_currently_joined=True)


async def on_guild_remove(client, guild):
    await upsert_guild(guild, is_currently_joined=False)


async def on_message(client, message):
    await insert_message(message)

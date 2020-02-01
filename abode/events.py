import asyncio
from abode.db.guilds import upsert_guild
from abode.db.messages import insert_message
from abode.db.channels import upsert_channel
from abode.backfill import backfill_channel, backfill_guild


async def backfill(client, message, args):
    snowflake = int(args)
    channel = client.get_channel(snowflake)
    if not channel:
        user = client.get_user(snowflake)
        channel = user.dm_channel or await user.create_dm()

    if channel:
        await message.add_reaction(client.get_emoji(580596825128697874))
        await backfill_channel(channel)
    else:
        await message.add_reaction(client.get_emoji(494901623731126272))


async def backfillg(client, message, args):
    guild = client.get_guild(int(args))
    if guild:
        await message.add_reaction(client.get_emoji(580596825128697874))
        await backfill_guild(guild)
    else:
        await message.add_reaction(client.get_emoji(494901623731126272))


async def backfilldms(client, message, args):
    await message.add_reaction(client.get_emoji(580596825128697874))
    for channel in client.private_channels:
        await backfill_channel(channel)


commands = {"backfill": backfill, "backfillg": backfillg, "backfilldms": backfilldms}


async def on_ready(client):
    print("Connected!")

    await asyncio.wait([upsert_channel(channel) for channel in client.private_channels])

    await asyncio.wait(
        [upsert_guild(guild, is_currently_joined=True) for guild in client.guilds]
    )


async def on_guild_join(client, guild):
    await upsert_guild(guild, is_currently_joined=True)


async def on_guild_update(client, old, new):
    await upsert_guild(new, is_currently_joined=True)


async def on_guild_remove(client, guild):
    await upsert_guild(guild, is_currently_joined=False)


async def on_message(client, message):
    await insert_message(message)

    if message.author.id == client.user.id:
        if message.content.startswith(";"):
            command, args = message.content.split(" ")
            fn = commands.get(command[1:])
            if fn:
                await fn(client, message, args)

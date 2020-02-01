from .db.messages import insert_message
from .db.channels import upsert_channel
from discord import TextChannel


async def backfill_channel(channel):
    print(f"Backfilling channel {channel.id}")
    await upsert_channel(channel)
    idx = 0
    async for message in channel.history(limit=None, oldest_first=True):
        idx += 1
        try:
            await insert_message(message)
        except Exception as e:
            print(f"  [{channel.id}] failed to backfill message {message.id}: {e}")

        if idx % 5000 == 0:
            print(f"  [{channel.id}] {idx} messages")
    print(f"Done backfilling channel {channel.id}, scanned {idx}")


async def backfill_guild(guild):
    print(f"Backfilling guild {guild.id}")
    for channel in guild.channels:
        if isinstance(channel, TextChannel):
            try:
                await upsert_channel(channel)
                await backfill_channel(channel)
            except Exception as e:
                print(f"failed to backfill channel {channel.id}: {e}")

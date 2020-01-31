from .db.messages import insert_message


async def backfill_channel(channel):
    print(f"Backfilling channel {channel.id}")
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

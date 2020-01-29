import discord
import functools


from .events import (
    on_ready,
    on_guild_join,
    on_guild_update,
    on_guild_remove,
    on_message,
)


USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:72.0) Gecko/20100101 Firefox/72.0"


def setup_client(config, loop):
    client = discord.Client(loop=loop)

    def bind(fn):
        return functools.partial(fn, client)

    client.on_ready = bind(on_ready)
    client.on_guild_join = bind(on_guild_join)
    client.on_guild_update = bind(on_guild_update)
    client.on_guild_remove = bind(on_guild_remove)
    client.on_message = bind(on_message)

    # TODO: cf cookies, IDENTIFY information
    client.http.user_agent = USER_AGENT
    return client.start(config["token"], bot=False), client.logout()

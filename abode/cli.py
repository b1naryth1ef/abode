import os
import json
import asyncio

from .db import init_db
from .client import setup_client
from .server import setup_server


def main():
    with open(os.getenv("ABODE_CONFIG_PATH", "config.json"), "r") as f:
        config = json.load(f)

    server_start = setup_server(config)

    loop = asyncio.get_event_loop()
    loop.create_task(init_db(config, loop))
    client_start, client_logout = setup_client(config, loop)

    try:
        loop.create_task(server_start)
        loop.run_until_complete(client_start)
    except KeyboardInterrupt:
        loop.run_until_complete(client_logout)
    finally:
        loop.close()


if __name__ == "__main__":
    main()

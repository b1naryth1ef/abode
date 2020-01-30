import os
import json
import asyncio
import argparse

from .db import init_db, close_db
from .client import setup_client
from .server import setup_server

parser = argparse.ArgumentParser("abode")
parser.add_argument("--run-api", action="store_true")
parser.add_argument("--run-client", action="store_true")


def main():
    args = parser.parse_args()

    with open(os.getenv("ABODE_CONFIG_PATH", "config.json"), "r") as f:
        config = json.load(f)

    start_tasks = []
    cleanup_tasks = []

    if args.run_api:
        server_start = setup_server(config)
        start_tasks.append(server_start)

    loop = asyncio.get_event_loop()
    loop.create_task(init_db(config, loop))
    cleanup_tasks.append(close_db())

    if args.run_client:
        client_start, client_logout = setup_client(config, loop)
        start_tasks.append(client_start)
        cleanup_tasks.append(client_logout)

    try:
        for task in start_tasks:
            loop.create_task(task)
        loop.run_forever()
    except KeyboardInterrupt:
        for task in cleanup_tasks:
            loop.run_until_complete(task)
    finally:
        loop.close()


if __name__ == "__main__":
    main()

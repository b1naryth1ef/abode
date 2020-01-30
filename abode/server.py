from sanic import Sanic
from sanic.response import json
from abode.lib.query import compile_query
from abode.db.guilds import Guild
from abode.db import get_pool

app = Sanic()


def setup_server(config):
    return app.create_server(
        host=config.get("host", "0.0.0.0"),
        port=config.get("port", 9999),
        return_asyncio_server=True,
    )


@app.route("/search", methods=["POST"])
async def route_search(request):
    query = request.json.get("query", "")
    try:
        sql, args = compile_query(query, Guild)
    except Exception as e:
        return json({"error": e})

    print(sql)
    print(args)

    results = []
    try:
        async with get_pool().acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(sql, *args)
                results = await cursor.fetchall()
    except Exception as e:
        return json({"error": e})

    return json({"results": [Guild.from_attrs(i) for i in results]})

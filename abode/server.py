import time
from sanic import Sanic
from sanic.response import json
from abode.lib.query import compile_query
from abode.db.guilds import Guild
from abode.db.messages import Message
from abode.db.emoji import Emoji
from abode.db import get_pool

app = Sanic()


SUPPORTED_MODELS = {
    "guild": Guild,
    "message": Message,
    "emoji": Emoji,
}


def setup_server(config):
    return app.create_server(
        host=config.get("host", "0.0.0.0"),
        port=config.get("port", 9999),
        return_asyncio_server=True,
    )


@app.route("/search/<model>", methods=["POST"])
async def route_search(request, model):
    model = SUPPORTED_MODELS.get(model)
    if not model:
        return json({"error": "unsupported model"}, status=404)

    limit = request.json.get("limit", 100)
    page = request.json.get("page", 1)
    order_by = request.json.get("order_by")
    order_dir = request.json.get("order_dir", "ASC")

    query = request.json.get("query", "")
    try:
        sql, args = compile_query(
            query,
            model,
            limit=limit,
            offset=(limit * (page - 1)),
            order_by=order_by,
            order_dir=order_dir,
        )
    except Exception as e:
        return json({"error": e})

    _debug = {"args": args, "sql": sql, "limit": limit, "page": page}

    results = []
    try:
        async with get_pool().acquire() as conn:
            async with conn.cursor() as cursor:
                start = time.time()
                await cursor.execute(sql, *args)
                results = await cursor.fetchall()
                _debug["ms"] = int((time.time() - start) * 1000)
    except Exception as e:
        return json({"error": e, "_debug": _debug})

    return json({"results": [model.from_attrs(i) for i in results], "_debug": _debug})

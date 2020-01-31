import time
from sanic import Sanic
from sanic.response import json
from abode.lib.query import compile_query
from abode.db.guilds import Guild
from abode.db.messages import Message
from abode.db import get_pool

app = Sanic()


SUPPORTED_MODELS = {
    "guild": Guild,
    "message": Message,
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

    limit = request.args.get("limit", 100)
    page = request.args.get("page", 1)

    query = request.json.get("query", "")
    try:
        sql, args = compile_query(
            query, model, limit=int(limit), offset=(int(limit) * (int(page) - 1))
        )
    except Exception as e:
        return json({"error": e})

    _debug = {"args": args, "sql": sql, "limit": int(limit), "page": int(page)}

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

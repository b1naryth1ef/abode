import time
from sanic import Sanic
from sanic.response import json
from abode.lib.query import compile_query, decode_query_record
from abode.db.guilds import Guild
from abode.db.messages import Message
from abode.db.emoji import Emoji
from abode.db.users import User
from abode.db.channels import Channel
from abode.db import get_pool

app = Sanic()
app.static("/", "./frontend/index.html")
app.static("/styles.css", "./frontend/styles.css")
app.static("/script.js", "./frontend/script.js")
app.static("/templates/", "./frontend/templates")


SUPPORTED_MODELS = {
    "guild": Guild,
    "message": Message,
    "emoji": Emoji,
    "user": User,
    "channel": Channel,
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
    include_foreign_data = request.json.get("foreign_data", True)

    query = request.json.get("query", "")
    try:
        sql, args, models = compile_query(
            query,
            model,
            limit=limit,
            offset=(limit * (page - 1)),
            order_by=order_by,
            order_dir=order_dir,
            include_foreign_data=include_foreign_data,
        )
    except Exception as e:
        return json({"error": e})

    _debug = {
        "args": args,
        "sql": sql,
        "request": request.json,
        "models": [i.__name__ for i in models],
    }

    results = []
    try:
        async with get_pool().acquire() as conn:
            start = time.time()
            results = await conn.fetch(sql, *args)
            _debug["ms"] = int((time.time() - start) * 1000)
    except Exception as e:
        return json({"error": e, "_debug": _debug})

    try:
        results = [list(decode_query_record(row, models)) for row in results]
        return json(
            {
                "results": {
                    model.__name__.lower(): [i[idx].serialize() for i in results]
                    for idx, model in enumerate(models)
                },
                "_debug": _debug,
            }
        )
    except Exception as e:
        return json({"error": e, "_debug": _debug})

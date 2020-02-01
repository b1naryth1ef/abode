import time
from sanic import Sanic
from sanic.response import json
from abode.lib.query import compile_query
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

    _debug = {
        "args": args,
        "sql": sql,
        "limit": limit,
        "page": page,
        "order": [order_by, order_dir],
    }

    results = []
    try:
        async with get_pool().acquire() as conn:
            start = time.time()
            results = await conn.fetch(sql, *args)
            _debug["ms"] = int((time.time() - start) * 1000)
    except Exception as e:
        return json({"error": e, "_debug": _debug})

    return json({"results": [model.from_record(i) for i in results], "_debug": _debug})

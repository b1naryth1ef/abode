from abode.lib.query import QueryParser, compile_query, _compile_selector
from abode.db.guilds import Guild
from abode.db.messages import Message
from abode.db.users import User


def test_parse_basic_queries():
    assert QueryParser.parsed("hello world") == [
        {"type": "symbol", "value": "hello"},
        {"type": "symbol", "value": "AND"},
        {"type": "symbol", "value": "world"},
    ]

    assert QueryParser.parsed('"Hello \\" World"') == [
        {"type": "string", "value": 'Hello " World'}
    ]

    assert QueryParser.parsed("(group me daddy)") == [
        {
            "type": "group",
            "value": [
                {"type": "symbol", "value": "group"},
                {"type": "symbol", "value": "AND"},
                {"type": "symbol", "value": "me"},
                {"type": "symbol", "value": "AND"},
                {"type": "symbol", "value": "daddy"},
            ],
        }
    ]

    assert QueryParser.parsed("x:y") == [
        {
            "type": "label",
            "name": "x",
            "value": {"type": "symbol", "value": "y"},
            "exact": False,
        }
    ]

    assert QueryParser.parsed("x=y") == [
        {
            "type": "label",
            "name": "x",
            "value": {"type": "symbol", "value": "y"},
            "exact": True,
        }
    ]

    assert QueryParser.parsed("x:(y z)") == [
        {
            "type": "label",
            "name": "x",
            "value": {
                "type": "group",
                "value": [
                    {"type": "symbol", "value": "y"},
                    {"type": "symbol", "value": "AND"},
                    {"type": "symbol", "value": "z"},
                ],
            },
            "exact": False,
        }
    ]

    assert QueryParser.parsed("x:/.* lol \\d me daddy/") == [
        {
            "type": "label",
            "name": "x",
            "value": {"type": "regex", "value": ".* lol \\d me daddy", "flags": []},
            "exact": False,
        }
    ]

    assert QueryParser.parsed("x:/.* lol \\d me daddy/i") == [
        {
            "type": "label",
            "name": "x",
            "value": {"type": "regex", "value": ".* lol \\d me daddy", "flags": ["i"]},
            "exact": False,
        }
    ]


def test_parse_complex_queries():
    assert QueryParser.parsed(
        'type:attachment guild:"discord api" (from:Jake#0001 OR from=danny#0007)'
    ) == [
        {
            "type": "label",
            "name": "type",
            "value": {"type": "symbol", "value": "attachment"},
            "exact": False,
        },
        {"type": "symbol", "value": "AND"},
        {
            "type": "label",
            "name": "guild",
            "value": {"type": "string", "value": "discord api"},
            "exact": False,
        },
        {"type": "symbol", "value": "AND"},
        {
            "type": "group",
            "value": [
                {
                    "type": "label",
                    "name": "from",
                    "value": {"type": "symbol", "value": "Jake#0001"},
                    "exact": False,
                },
                {"type": "symbol", "value": "OR"},
                {
                    "type": "label",
                    "name": "from",
                    "value": {"type": "symbol", "value": "danny#0007"},
                    "exact": True,
                },
            ],
        },
    ]


def test_compile_basic_queries():
    assert compile_query("name:blob", Guild) == (
        "SELECT guilds.* FROM guilds WHERE guilds.name ILIKE $1",
        ("%blob%",),
        (Guild,),
    )

    assert compile_query('name:"blob"', Guild) == (
        "SELECT guilds.* FROM guilds WHERE guilds.name ILIKE $1",
        ("blob",),
        (Guild,),
    )

    assert compile_query("name:(blob emoji)", Guild) == (
        "SELECT guilds.* FROM guilds WHERE (guilds.name ILIKE $1 AND guilds.name ILIKE $2)",
        ("%blob%", "%emoji%",),
        (Guild,),
    )

    assert compile_query("name:(blob AND emoji)", Guild) == (
        "SELECT guilds.* FROM guilds WHERE (guilds.name ILIKE $1 AND guilds.name ILIKE $2)",
        ("%blob%", "%emoji%",),
        (Guild,),
    )

    assert compile_query("name:(discord AND NOT api)", Guild) == (
        "SELECT guilds.* FROM guilds WHERE (guilds.name ILIKE $1 AND NOT guilds.name ILIKE $2)",
        ("%discord%", "%api%",),
        (Guild,),
    )

    assert compile_query("id:1", Guild) == (
        "SELECT guilds.* FROM guilds WHERE guilds.id = $1",
        (1,),
        (Guild,),
    )

    assert compile_query("", Guild, limit=100, offset=150, order_by="id") == (
        "SELECT guilds.* FROM guilds ORDER BY guilds.id ASC LIMIT 100 OFFSET 150",
        (),
        (Guild,),
    )

    assert compile_query("", Guild, order_by="id", order_dir="DESC") == (
        "SELECT guilds.* FROM guilds ORDER BY guilds.id DESC",
        (),
        (Guild,),
    )

    assert compile_query("id=1", Guild) == (
        "SELECT guilds.* FROM guilds WHERE guilds.id = $1",
        (1,),
        (Guild,),
    )


def test_compile_complex_queries():
    assert compile_query("name:blob OR name:api", Guild) == (
        "SELECT guilds.* FROM guilds WHERE guilds.name ILIKE $1 OR guilds.name ILIKE $2",
        ("%blob%", "%api%"),
        (Guild,),
    )

    assert compile_query("guild.name:blob", Message) == (
        "SELECT messages.* FROM messages JOIN guilds ON messages.guild_id = guilds.id WHERE guilds.name ILIKE $1",
        ("%blob%",),
        (Message,),
    )

    assert compile_query("content:yeet", Message) == (
        "SELECT messages.* FROM messages WHERE to_tsvector('english', messages.content) @@ to_tsquery($1)",
        ("yeet",),
        (Message,),
    )

    assert compile_query('guild.name:(a "b")', Message) == (
        "SELECT messages.* FROM messages JOIN guilds ON messages.guild_id = guilds.id WHERE (guilds.name ILIKE $1 AND "
        "guilds.name ILIKE $2)",
        ("%a%", "b"),
        (Message,),
    )

    assert compile_query("guild.owner.name:Danny", Message) == (
        "SELECT messages.* FROM messages JOIN guilds ON messages.guild_id = guilds.id JOIN users ON "
        "guilds.owner_id = users.id WHERE users.name ILIKE $1",
        ("%Danny%",),
        (Message,),
    )

    message_selector = _compile_selector(Message)
    guild_selector = _compile_selector(Guild)
    author_selector = _compile_selector(User)

    assert compile_query("", Message, include_foreign_data=True) == (
        f"SELECT {message_selector}, {guild_selector}, {author_selector} FROM messages JOIN guilds ON messages.guild_id = guilds.id"
        " JOIN users ON messages.author_id = users.id",
        (),
        (Message, Guild, User),
    )

    assert compile_query("guild.id:1", Message, include_foreign_data=True) == (
        f"SELECT {message_selector}, {guild_selector}, {author_selector} FROM messages JOIN guilds ON messages.guild_id = guilds.id"
        " JOIN users ON messages.author_id = users.id WHERE guilds.id = $1",
        (1,),
        (Message, Guild, User),
    )

    assert compile_query("name: /xxx.*xxx/i", Guild) == (
        f"SELECT guilds.* FROM guilds WHERE guilds.name ~* $1",
        ("xxx.*xxx",),
        (Guild,),
    )


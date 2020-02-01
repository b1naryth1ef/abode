from abode.lib.query import QueryParser, compile_query
from abode.db.guilds import Guild
from abode.db.messages import Message


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
    )

    assert compile_query('name:"blob"', Guild) == (
        "SELECT guilds.* FROM guilds WHERE guilds.name ILIKE $1",
        ("blob",),
    )

    assert compile_query("name:(blob emoji)", Guild) == (
        "SELECT guilds.* FROM guilds WHERE (guilds.name ILIKE $1 AND guilds.name ILIKE $2)",
        ("%blob%", "%emoji%",),
    )

    assert compile_query("name:(blob AND emoji)", Guild) == (
        "SELECT guilds.* FROM guilds WHERE (guilds.name ILIKE $1 AND guilds.name ILIKE $2)",
        ("%blob%", "%emoji%",),
    )

    assert compile_query("name:(discord AND NOT api)", Guild) == (
        "SELECT guilds.* FROM guilds WHERE (guilds.name ILIKE $1 AND NOT guilds.name ILIKE $2)",
        ("%discord%", "%api%",),
    )

    assert compile_query("id:1", Guild) == (
        "SELECT guilds.* FROM guilds WHERE guilds.id = $1",
        (1,),
    )

    assert compile_query("", Guild, limit=100, offset=150, order_by="id") == (
        "SELECT guilds.* FROM guilds ORDER BY guilds.id ASC LIMIT 100 OFFSET 150",
        (),
    )

    assert compile_query("", Guild, order_by="id", order_dir="DESC") == (
        "SELECT guilds.* FROM guilds ORDER BY guilds.id DESC",
        (),
    )

    assert compile_query("id=1", Guild) == (
        "SELECT guilds.* FROM guilds WHERE guilds.id = $1",
        (1,),
    )


def test_compile_complex_queries():
    assert compile_query("name:blob OR name:api", Guild) == (
        "SELECT guilds.* FROM guilds WHERE guilds.name ILIKE $1 OR guilds.name ILIKE $2",
        ("%blob%", "%api%"),
    )

    assert compile_query("guild.name:blob", Message) == (
        "SELECT messages.* FROM messages JOIN guilds ON messages.guild_id = guilds.id WHERE guilds.name ILIKE $1",
        ("%blob%",),
    )

    assert compile_query("content:yeet", Message) == (
        "SELECT messages.* FROM messages WHERE messages.content @@ to_tsquery($1)",
        ("yeet",),
    )

    assert compile_query('guild.name:(a "b")', Message) == (
        "SELECT messages.* FROM messages JOIN guilds ON messages.guild_id = guilds.id WHERE (guilds.name ILIKE $1 AND "
        "guilds.name ILIKE $2)",
        ("%a%", "b"),
    )

    assert compile_query("guild.owner.name:Danny", Message) == (
        "SELECT messages.* FROM messages JOIN guilds ON messages.guild_id = guilds.id JOIN users ON "
        "guilds.owner_id = users.id WHERE users.name ILIKE $1",
        ("%Danny%",),
    )

    assert compile_query("", Message, include_foreign_data=True) == (
        "SELECT messages.* FROM messages",
        (),
    )

    assert compile_query("guild.id:1", Message, include_foreign_data=True) == (
        "SELECT messages.*, guilds.* FROM messages JOIN guilds ON messages.guild_id = guilds.id WHERE guilds.id = $1",
        (1,),
    )

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
        {"type": "label", "name": "x", "value": {"type": "symbol", "value": "y"}}
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
        }
    ]


def test_parse_complex_queries():
    assert QueryParser.parsed(
        'type:attachment guild:"discord api" (from:Jake#0001 OR from:danny#0007)'
    ) == [
        {
            "type": "label",
            "name": "type",
            "value": {"type": "symbol", "value": "attachment"},
        },
        {"type": "symbol", "value": "AND"},
        {
            "type": "label",
            "name": "guild",
            "value": {"type": "string", "value": "discord api"},
        },
        {"type": "symbol", "value": "AND"},
        {
            "type": "group",
            "value": [
                {
                    "type": "label",
                    "name": "from",
                    "value": {"type": "symbol", "value": "Jake#0001"},
                },
                {"type": "symbol", "value": "OR"},
                {
                    "type": "label",
                    "name": "from",
                    "value": {"type": "symbol", "value": "danny#0007"},
                },
            ],
        },
    ]


def test_compile_basic_queries():
    assert compile_query("name:blob", Guild) == (
        "SELECT * FROM guilds WHERE name LIKE ?",
        ("%blob%",),
    )

    assert compile_query('name:"blob"', Guild) == (
        "SELECT * FROM guilds WHERE name LIKE ?",
        ("blob",),
    )

    assert compile_query("name:(blob emoji)", Guild) == (
        "SELECT * FROM guilds WHERE name LIKE ? AND name LIKE ?",
        ("%blob%", "%emoji%",),
    )

    assert compile_query("name:(blob AND emoji)", Guild) == (
        "SELECT * FROM guilds WHERE name LIKE ? AND name LIKE ?",
        ("%blob%", "%emoji%",),
    )

    assert compile_query("name:(discord AND NOT api)", Guild) == (
        "SELECT * FROM guilds WHERE name LIKE ? AND NOT name LIKE ?",
        ("%discord%", "%api%",),
    )


def test_compile_complex_queries():
    assert compile_query("name:blob OR name:api", Guild) == (
        "SELECT * FROM guilds WHERE name LIKE ? OR name LIKE ?",
        ("%blob%", "%api%"),
    )

    assert compile_query("guild.name:blob", Message) == (
        "SELECT * FROM messages JOIN guilds ON messages.guild_id = guilds.id WHERE guilds.name LIKE ?",
        ("%blob%",),
    )

    assert compile_query("content:yeet", Message) == (
        "SELECT * FROM messages JOIN messages_fts ON messages.id = messages_fts.rowid WHERE messages_fts.content LIKE ?",
        ("%yeet%",),
    )

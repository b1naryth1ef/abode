import aioodbc
import functools
import os
import dataclasses
import json
import typing

pool = None

FTS = typing.NewType("FTS", str)
Snowflake = typing.NewType("Snowflake", str)


def to_json_str(obj):
    if isinstance(obj, str):
        return obj
    return json.dumps(obj)


async def init_db(config, loop):
    global pool
    database = config.get("dbpath", "test.db")
    pool = await aioodbc.create_pool(
        dsn=f"Driver=SQLite3;Database={database}", loop=loop
    )

    conn = await pool.acquire()
    cursor = await conn.cursor()

    sql_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "schema"))
    for sql_file in os.listdir(sql_dir):
        with open(os.path.join(sql_dir, sql_file), "r") as f:
            await cursor.execute(f.read())
            await cursor.commit()

    await cursor.close()
    await conn.close()


async def close_db():
    get_pool().close()


def get_pool():
    return pool


def with_cursor(func):
    @functools.wraps(func)
    async def wrapped(*args, **kwargs):
        async with get_pool().acquire() as conn:
            async with conn.cursor() as cursor:
                return await func(cursor, *args, **kwargs)

    return wrapped


def build_insert_query(instance, upsert=False):
    dataclass = instance.__class__

    column_names = []
    column_values = []
    updates = []
    for field in dataclasses.fields(dataclass):
        column_names.append(field.name)
        column_values.append(convert_to_type(getattr(instance, field.name), field.type))

        if upsert:
            updates.append(f"{field.name}=excluded.{field.name}")
    values = ", ".join(["?"] * len(column_names))

    upsert_contents = ""
    if upsert:
        updates = ",\n".join(updates)
        upsert_contents = f"""
            ON CONFLICT (id) DO UPDATE SET
                {updates}
        """

    return (
        f"""
        INSERT INTO {table_name(dataclass)} ({', '.join(column_names)})
        VALUES ({values})
        {upsert_contents}
    """,
        tuple(column_values),
    )


def build_select_query(instance, where=None):
    dataclass = instance.__class__
    select_fields = ", ".join([field.name for field in dataclasses.fields(dataclass)])
    where = f"WHERE {where}" if where else ""

    return f"""
        SELECT {select_fields} FROM {table_name(dataclass)}
        {where}
    """


def convert_to_type(value, target_type):
    if typing.get_origin(target_type) is typing.Union:
        if type(None) in typing.get_args(target_type):
            if value is None:
                return None
            return next(i for i in typing.get_args(target_type) if i is not type(None))(
                value
            )
        assert False
    return target_type(value)


def table_name(model):
    return model.__name__.lower() + "s"


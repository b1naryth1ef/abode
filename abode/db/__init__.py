import asyncpg
import functools
import os
import dataclasses
import json
import typing
from datetime import datetime

pool = None


T = typing.TypeVar("T")


class JSONB(typing.Generic[T]):
    inner: T


class FTS:
    def __init__(self, inner):
        self.inner = inner


def Snowflake(i):
    return int(i)


def to_json_str(obj):
    if isinstance(obj, str):
        return obj
    return json.dumps(obj)


async def init_db(config, loop):
    global pool

    pool = await asyncpg.create_pool(dsn=config.get("postgres_dsn"))

    async with pool.acquire() as connection:
        sql_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "schema")
        )
        for sql_file in os.listdir(sql_dir):
            with open(os.path.join(sql_dir, sql_file), "r") as f:
                await connection.execute(f.read())


async def close_db():
    await get_pool().close()


def get_pool():
    return pool


def with_conn(func):
    @functools.wraps(func)
    async def wrapped(*args, **kwargs):
        if "conn" in kwargs:
            return await func(kwargs.pop("conn"), *args, **kwargs)

        async with pool.acquire() as connection:
            return await func(connection, *args, **kwargs)

    return wrapped


def build_insert_query(instance, upsert=False, ignore_existing=False):
    dataclass = instance.__class__

    column_names = []
    column_values = []
    updates = []
    for field in dataclasses.fields(dataclass):
        column_names.append(field.name)
        column_values.append(
            convert_to_type(getattr(instance, field.name), field.type, to_pg=True)
        )

        if upsert:
            updates.append(f"{field.name}=excluded.{field.name}")
    values = ", ".join([f"${i}" for i in range(1, len(column_names) + 1)])

    upsert_contents = ""
    if upsert:
        updates = ",\n".join(updates)
        upsert_contents = f"""
            ON CONFLICT (id) DO UPDATE SET
                {updates}
        """

    if ignore_existing:
        assert not upsert
        upsert_contents = """
            ON CONFLICT (id) DO NOTHING
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


def convert_to_type(value, target_type, to_pg=False, from_pg=False, to_js=False):
    if typing.get_origin(target_type) is typing.Union:
        if type(None) in typing.get_args(target_type):
            if value is None:
                return None
            target_type = next(
                i for i in typing.get_args(target_type) if i is not type(None)
            )
        else:
            assert False

    if (
        to_js
        and target_type == Snowflake
        or (target_type == typing.Optional[Snowflake] and value is not None)
    ):
        return str(value)

    if (
        to_js
        and target_type == datetime
        or (target_type == typing.Optional[datetime] and value is not None)
    ):
        return value.isoformat()

    if typing.get_origin(target_type) == list:
        return list(value)

    if type(value) == target_type:
        return value

    if to_pg and typing.get_origin(target_type) == JSONB:
        return json.dumps(value)

    if from_pg and typing.get_origin(target_type) == JSONB:
        return json.loads(value)

    try:
        return target_type(value)
    except Exception:
        print(type(value))
        print(target_type)
        print(typing.get_origin(target_type))
        raise


def table_name(model):
    return getattr(model, "_table_name", model.__name__.lower() + "s")


class BaseModel:
    _refs = {}
    _fts = set()
    _virtual_fields = {}

    def serialize(self, **kwargs):
        return {
            field.name: convert_to_type(
                getattr(self, field.name), field.type, to_js=True
            )
            for field in dataclasses.fields(self)
        }

    def diff(self, other):
        for field in dataclasses.fields(self):
            if getattr(other, field.name) != getattr(self, field.name):
                yield {
                    "field": field.name,
                    "old": getattr(other, field.name),
                    "new": getattr(self, field.name),
                }

    @classmethod
    def from_record(cls, record):
        return cls(
            **{
                field.name: convert_to_type(record[idx], field.type, from_pg=True)
                for idx, field in enumerate(dataclasses.fields(cls))
            }
        )

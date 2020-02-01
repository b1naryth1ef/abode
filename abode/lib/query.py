"""
This module implements everything required for processing and executing user-written
queries in our custom search DSL. As the language is small and simple enough there
is no real concept of a lexer, and instead we directly parse search queries into
an extremely simple AST.

From an AST we can then generate a query based on a given model and query options.
This query is returned in a form that can be easily passed to SQL interfaces
(query, (args...)).
"""
import dataclasses
import typing
from abode.db import table_name, FTS, Snowflake

JOINERS = ("AND", "OR")


class QueryParser:
    def __init__(self, query_string):
        self.idx = 0
        self.buffer = query_string

    @classmethod
    def parsed(cls, query):
        inst = cls(query)
        return inst._fix(inst._parse())

    def _next_char(self):
        if self.idx >= len(self.buffer):
            return None
        char = self.buffer[self.idx]
        self.idx += 1
        return char

    def _peek_char(self, n=0):
        if self.idx + n >= len(self.buffer):
            return None
        return self.buffer[self.idx + n]

    def _parse_string(self):
        escaped = False
        parts = ""
        while True:
            char = self._next_char()
            assert char is not None
            if char == '"':
                if escaped:
                    escaped = False
                else:
                    return parts
            elif char == "\\":
                escaped = True
                continue
            parts += char

    def _parse_symbol(self):
        parts = ""
        while True:
            char = self._peek_char()
            if char in (" ", ":", "=", '"', "(", ")", None):
                return parts
            parts += self._next_char()

    def _parse_one(self):
        while True:
            char = self._next_char()
            if char is None or char == ")":
                return None
            elif char == '"':
                string = self._parse_string()
                return {"type": "string", "value": string}
            elif char == "(":
                return {"type": "group", "value": self._parse()}
            elif char == " ":
                continue
            else:
                self.idx -= 1
                symbol = self._parse_symbol()
                if not symbol:
                    return None

                if self._peek_char() in (":", "="):
                    exact = self._next_char() == "="
                    return {
                        "type": "label",
                        "name": symbol,
                        "value": self._parse_one(),
                        "exact": exact,
                    }

                return {"type": "symbol", "value": symbol}

    def _parse(self):
        parts = []

        while True:
            one = self._parse_one()
            if not one:
                return parts
            parts.append(one)

    def _fix(self, tree):
        result = []
        previous_node = None
        for node in tree:
            if node["type"] == "group":
                node["value"] = self._fix(node["value"])
            elif node["type"] == "symbol":
                if node["value"] == "NOT":
                    if not previous_node or (
                        previous_node["type"] == "symbol"
                        and previous_node["value"] not in JOINERS
                    ):
                        raise Exception("NOT requires a joiner prefix (and/or)")
                elif node["value"] in JOINERS:
                    if (
                        previous_node
                        and previous_node["type"] == "symbol"
                        and previous_node["value"] in JOINERS
                    ):
                        raise Exception("One side of joiners cannot be another joiner")
            elif node["type"] == "label" and node["value"]["type"] == "group":
                # TODO: HMMMMM, need _fix_one(node, previous=xxx) ??
                node["value"]["value"] = self._fix(node["value"]["value"])

            # Injects 'AND' in between bare non-joiners
            if (
                (node["type"] != "symbol" or node["value"] not in JOINERS)
                and previous_node
                and (
                    previous_node["type"] != "symbol"
                    or previous_node["value"] not in JOINERS + ("NOT",)
                )
            ):
                result.append({"type": "symbol", "value": "AND"})
            previous_node = node
            result.append(node)
        return result


class SubqueryOptimized(object):
    def __init__(self, inner, ref_model, join):
        self.inner = inner
        self.ref_model = ref_model
        self.join = join


def _resolve_foreign_model_field(field_name, model, joins=None):
    rest = None
    foreign_field_name, field_name = field_name.split(".", 1)
    if "." in field_name:
        field_name, rest = field_name.split(".", 1)

    ref_model, on, _ = model._refs[foreign_field_name]

    if not joins:
        joins = {}

    joins.update(
        {ref_model: f"{table_name(model)}.{on[0]} = {table_name(ref_model)}.{on[1]}"}
    )

    if rest:
        return _resolve_foreign_model_field(field_name + "." + rest, ref_model, joins)

    _, ref_type, _ = resolve_model_field(field_name, ref_model)

    return (f"{table_name(ref_model)}.{field_name}", ref_type, joins)


def resolve_model_field(field_name, model):
    """
    Resolves a field name within a given model. This function will generate joins
    for cases where the target field is on a relation or is stored within an
    external index.

    The result of this function is a tuple of the target field name, the field
    result type, and a dictionary of joins.

    >>> resolve_model_field("guilds.name", Message)
    ("guilds.name", str, {"guilds": "messages.guild_id = guilds.id"})

    >>> resolve_model_field("content", Message)
    ("messages_fts.content", FTS(str), {"messages_fts": "messages.id = messages_fts.rowid"})
    """
    if "." in field_name:
        return _resolve_foreign_model_field(field_name, model)

    for field in dataclasses.fields(model):
        if field.name == field_name:
            if field.name in model._fts:
                return (
                    f"to_tsvector('english', {table_name(model)}.{field.name})",
                    FTS(field.type),
                    {},
                )

            return f"{table_name(model)}.{field.name}", field.type, {}
    raise Exception(f"no such field on {model}: `{field_name}``")


def _compile_field_query_op(field_type, token, varidx):
    """
    Compiles a single token against a given field type into a single query filter.
    Sadly this function also encodes some more complex logic about querying, such
    as wildcard processing and exact matching.

    Returns a tuple of the filter operator and the processed token value as an
    argument to the operator.
    """
    var = f"${varidx}"
    assert token["type"] in ("symbol", "string")

    if typing.get_origin(field_type) is typing.Union:
        args = typing.get_args(field_type)
        field_type = next(i for i in args if i != type(None))

    if isinstance(field_type, FTS):
        return ("@@", token["value"], f"to_tsquery({var})")
    elif field_type == Snowflake:
        return ("=", Snowflake(token["value"]), var)
    elif field_type == str or field_type == typing.Optional[str]:
        if token.get("exact"):
            return ("=", token["value"], var)
        elif token["type"] == "symbol":
            # TODO: regex this so we can handle escapes?
            if "*" in token["value"]:
                return ("ILIKE", token["value"].replace("*", "%"), var)
            return ("ILIKE", "%" + token["value"] + "%", var)
        else:
            # Like just gives us case insensitivity here
            return ("ILIKE", token["value"], var)
    elif field_type == int or field_type == typing.Optional[int]:
        return ("=", int(token["value"]), var)
    else:
        print(token)
        raise Exception(f"cannot query against field of type {field_type}")


def _compile_token_for_query(token, model, field=None, field_type=None, varidx=0):
    """
    Compile a single token into a single filter against the model.

    Returns a tuple of the where clause, variables, and joins.
    """

    if token["type"] == "label":
        field, field_type, field_joins = resolve_model_field(token["name"], model)
        token["value"]["exact"] = token["exact"]
        where, variables, joins, varidx = _compile_token_for_query(
            token["value"], model, field=field, field_type=field_type, varidx=varidx
        )
        joins.update(field_joins)
        return where, variables, joins, varidx
    elif token["type"] == "symbol":
        if token["value"] in ("AND", "OR", "NOT"):
            return (token["value"], [], {}, varidx)
        elif isinstance(field_type, SubqueryOptimized):
            varidx += 1
            op, arg, var = _compile_field_query_op(field_type.inner, token, varidx)
            return (
                f"{table_name(model)}.{field_type.join[0]} IN (SELECT {field_type.join[1]} FROM "
                f"{table_name(field_type.ref_model)} WHERE {field} {op} {var})",
                [arg],
                {},
                varidx,
            )
        elif field:
            # messages.guild_id IN (SELECT id FROM guilds WHERE x LIKE y)
            varidx += 1
            op, arg, var = _compile_field_query_op(field_type, token, varidx)
            return (f"{field} {op} {var}", [arg], {}, varidx)
        else:
            value = token["value"]

            joins = {}
            ref_model = model
            while value.split(".", 1)[0] in ref_model._refs:
                ref_model, join_on, _ = model._refs[value]

                joins.update(
                    {
                        ref_model: f"{table_name(model)}.{join_on[0]} = {table_name(ref_model)}.{join_on[1]}"
                    }
                )

                if "." not in value:
                    return (f"true", [], joins, varidx)

                value = value.split(".", 1)[1]

            raise Exception(f"unlabeled symbol cannot be matched: `{value}`")
    elif token["type"] == "string" and field:
        if isinstance(field_type, SubqueryOptimized):
            varidx += 1
            op, arg, var = _compile_field_query_op(field_type.inner, token, varidx)
            return (
                f"{table_name(model)}.{field_type.join[0]} IN (SELECT {field_type.join[1]} FROM "
                f"{table_name(field_type.ref_model)} WHERE {field} {op} {var})",
                [arg],
                {},
                varidx,
            )
        varidx += 1
        op, arg, var = _compile_field_query_op(field_type, token, varidx)
        return (f"{field} {op} {var}", [arg], {}, varidx)
    elif token["type"] == "group":
        where = []
        variables = []
        joins = {}
        for child_token in token["value"]:
            child_token["exact"] = token.get("exact", False)
            where_part, variables_part, joins_part, varidx = _compile_token_for_query(
                child_token, model, field=field, field_type=field_type, varidx=varidx
            )
            joins.update(joins_part)
            where.append(where_part)
            variables.extend(variables_part)
        return "(" + " ".join(where) + ")", variables, joins, varidx
    else:
        assert False


def _compile_selector(model):
    return ", ".join(
        f"{table_name(model)}.{field.name}" for field in dataclasses.fields(model)
    )


def _compile_query_for_model(
    tokens,
    model,
    limit=None,
    offset=None,
    order_by=None,
    order_dir="ASC",
    include_foreign_data=False,
):
    parts = []
    varidx = 0
    for token in tokens:
        a, b, c, varidx = _compile_token_for_query(token, model, varidx=varidx)
        parts.append((a, b, c))

    where = []
    variables = []
    joins = {}

    for where_part, variables_part, joins_part in parts:
        where.append(where_part)
        variables.extend(variables_part)
        joins.update(joins_part)

    if order_by:
        field, field_type, order_joins = resolve_model_field(order_by, model)
        joins.update(order_joins)
        assert order_dir in ("ASC", "DESC")
        order_by = f" ORDER BY {field} {order_dir}"
    else:
        order_by = ""

    models = [model]
    if include_foreign_data:
        for ref_model, join_on, always in model._refs.values():
            if ref_model in joins:
                models.append(ref_model)
                continue

            if always:
                joins.update(
                    {
                        ref_model: f"{table_name(model)}.{join_on[0]} = {table_name(ref_model)}.{join_on[1]}"
                    }
                )
                models.append(ref_model)

    if len(models) > 1:
        selectors = ", ".join(_compile_selector(model) for model in models)
    else:
        selectors = f"{table_name(model)}.*"

    if joins:
        joins = "".join(
            f" JOIN {table_name(model)} ON {cond}" for model, cond in joins.items()
        )
    else:
        joins = ""

    if where:
        where = " WHERE " + " ".join(where)
    else:
        where = ""

    suffix = []
    if limit is not None and limit > 0:
        suffix.append(f" LIMIT {limit}")

        if offset is not None and offset > 0:
            suffix.append(f" OFFSET {offset}")

    suffix = "".join(suffix)

    return (
        f"SELECT {selectors} FROM {table_name(model)}{joins}{where}{order_by}{suffix}",
        tuple(variables),
        tuple(models),
    )


def compile_query(query, model, **kwargs):
    tokens = QueryParser.parsed(query)
    return _compile_query_for_model(tokens, model, **kwargs)


def decode_query_record(record, models):
    idx = 0
    for model in models:
        num_fields = len(dataclasses.fields(model))
        model_data = record[idx : idx + num_fields]
        idx += num_fields
        yield model.from_record(model_data)

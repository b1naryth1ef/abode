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


def resolve_model_field(field_name, model, use_subquery_optimize=False):
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
    # TODO: we need to seperate out this logic into another function so we can
    #  properly recurse and handle x.y.z cases.

    if "." in field_name:
        assert field_name.count(".") == 1
        left, right = field_name.split(".", 1)

        ref_model, on, can_subquery_optimize = model._refs[left]
        for ref_field in dataclasses.fields(ref_model):
            if ref_field.name == right:
                break
        else:
            raise Exception(f"no field `{right}` on model `{ref_model}`")

        if use_subquery_optimize and can_subquery_optimize:
            # Emit no join
            # Somehow op results in message.guild_id in (SELECT id FROM guilds WHERE name LIKE xxx)
            return (right, SubqueryOptimized(ref_field.type, ref_model, on), {})
        else:
            return (
                f"{table_name(ref_model)}.{right}",
                ref_field.type,
                {
                    table_name(
                        ref_model
                    ): f"{table_name(model)}.{on[0]} = {table_name(ref_model)}.{on[1]}"
                },
            )

    if field_name in model._external_indexes:
        ref_table, on, field_type = model._external_indexes[field_name]
        return (
            f"{ref_table}.{field_name}",
            field_type,
            {ref_table: f"{table_name(model)}.{on[0]} = {ref_table}.{on[1]}"},
        )

    for field in dataclasses.fields(model):
        if field.name == field_name:
            if field.name in model._fts:
                return f"{table_name(model)}.{field.name}", FTS(field.type), {}

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

    if field_type == FTS:
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
    else:
        print(token)
        raise Exception(f"cannot query against field of type {field_type}")


def _compile_token_for_query(
    token, model, field=None, field_type=None, use_subquery_optimize=False, varidx=0
):
    """
    Compile a single token into a single filter against the model.

    Returns a tuple of the where clause, variables, and joins.
    """

    if token["type"] == "label":
        field, field_type, field_joins = resolve_model_field(
            token["name"], model, use_subquery_optimize=use_subquery_optimize
        )
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


def _compile_query_for_model(
    tokens,
    model,
    limit=None,
    offset=None,
    order_by=None,
    order_dir="ASC",
    use_subquery_optimize=False,
):
    parts = []
    varidx = 0
    for token in tokens:
        a, b, c, varidx = _compile_token_for_query(
            token, model, use_subquery_optimize=use_subquery_optimize, varidx=varidx
        )
        parts.append((a, b, c))

    where = []
    variables = []
    joins = {}

    for where_part, variables_part, joins_part in parts:
        where.append(where_part)
        variables.extend(variables_part)
        joins.update(joins_part)

    if not order_by:
        order_by = model._pk

    field, field_type, order_joins = resolve_model_field(order_by, model)
    joins.update(order_joins)
    assert order_dir in ("ASC", "DESC")
    order_by = f" ORDER BY {field} {order_dir}"

    if joins:
        joins = "".join(f" JOIN {table} ON {cond}" for table, cond in joins.items())
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
        f"SELECT {table_name(model)}.* FROM {table_name(model)}{joins}{where}{order_by}{suffix}",
        tuple(variables),
    )


def compile_query(query, model, **kwargs):
    tokens = QueryParser.parsed(query)
    return _compile_query_for_model(tokens, model, **kwargs)

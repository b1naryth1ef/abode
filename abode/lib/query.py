import dataclasses
from abode.db import table_name

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
            if char in (" ", ":", '"', "(", ")", None):
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

                if self._peek_char() == ":":
                    self._next_char()
                    return {"type": "label", "name": symbol, "value": self._parse_one()}

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


def _match_model_field(field_name, model):
    # guild.name -> "guilds.name", {"guilds": "message.guild_id = guild.id"}
    if "." in field_name:
        assert field_name.count(".") == 1  # TODO: recursive lol
        left, right = field_name.split(".", 1)

        ref_model, on = model._refs[left]
        return (
            f"{table_name(ref_model)}.{right}",
            {
                table_name(
                    ref_model
                ): f"{table_name(model)}.{on[0]} = {table_name(ref_model)}.{on[1]}"
            },
        )

    # content -> "messages_fts.content", {"messages_fts": "message.id = messages_fts.rowid"}
    if field_name in model._external_indexes:
        ref_table, on = model._external_indexes[field_name]
        return (
            f"{ref_table}.{field_name}",
            {ref_table: f"{table_name(model)}.{on[0]} = {ref_table}.{on[1]}"},
        )

    for field in dataclasses.fields(model):
        if field.name == field_name:
            return field.name, {}
    raise Exception(f"no such field on {model}: `{field_name}``")


def _compile_token_for_query(token, model, field=None):
    if token["type"] == "label":
        field, field_joins = _match_model_field(token["name"], model)
        where, variables, joins = _compile_token_for_query(
            token["value"], model, field=field
        )
        joins.update(field_joins)
        return where, variables, joins
    elif token["type"] == "symbol":
        if token["value"] in ("AND", "OR", "NOT"):
            return (token["value"], [], {})
        elif field:
            return (f"{field} LIKE ?", ["%" + token["value"] + "%"], {})
        else:
            value = token["value"]
            raise Exception(f"unlabeled symbol cannot be matched: `{value}`")
    elif token["type"] == "string" and field:
        # Like just gives us case insensitivity here
        return (f"{field} LIKE ?", [token["value"]], {})
    elif token["type"] == "group":
        where = []
        variables = []
        joins = {}
        for child_token in token["value"]:
            where_part, variables_part, joins_part = _compile_token_for_query(
                child_token, model, field
            )
            joins.update(joins_part)
            where.append(where_part)
            variables.extend(variables_part)
        return " ".join(where), variables, joins
    else:
        assert False


def _compile_query_for_model(tokens, model, limit=None, offset=None):
    parts = []
    for token in tokens:
        parts.append(_compile_token_for_query(token, model))

    where = []
    variables = []
    joins = {}

    for where_part, variables_part, joins_part in parts:
        where.append(where_part)
        variables.extend(variables_part)
        joins.update(joins_part)

    if joins:
        joins = "".join(f" JOIN {table} ON {cond}" for table, cond in joins.items())
    else:
        joins = ""

    if where:
        where = " WHERE " + " ".join(where)
    else:
        where = ""

    suffix = []
    if limit is not None:
        suffix.append(f" LIMIT {limit}")

    if offset is not None:
        suffix.append(f" OFFSET {offset}")

    suffix = "".join(suffix)

    return (
        f"SELECT * FROM {table_name(model)}{joins}{where}{suffix}",
        tuple(variables),
    )


def compile_query(query, model, **kwargs):
    tokens = QueryParser.parsed(query)
    return _compile_query_for_model(tokens, model, **kwargs)

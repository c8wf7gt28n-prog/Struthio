"""A small, dependency-free JSON Schema (draft 2020-12 subset) validator.

The ARC-1 SDK must run offline with only the Python standard library, so it
cannot rely on the third-party ``jsonschema`` package. This module implements
the subset of keywords the SDK schemas use and *fails closed*: a schema that
uses any keyword outside SUPPORTED raises SchemaError instead of being
silently ignored, so a schema author cannot believe a constraint is enforced
when it is not.

The test suite cross-checks this validator against the reference
``jsonschema`` package when that package happens to be installed.
"""

import re

SUPPORTED = frozenset({
    "$schema", "$id", "$ref", "$defs", "$comment", "title", "description",
    "examples", "default",
    "type", "enum", "const",
    "properties", "required", "additionalProperties",
    "items", "minItems", "maxItems", "uniqueItems",
    "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
    "minLength", "maxLength", "pattern",
    "allOf", "anyOf", "oneOf", "not", "if", "then", "else",
})


class SchemaError(Exception):
    """The schema itself is invalid or uses an unsupported keyword."""


def _type_ok(value, name):
    if name == "null":
        return value is None
    if name == "boolean":
        return isinstance(value, bool)
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool) or (
            isinstance(value, float) and value.is_integer())
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if name == "string":
        return isinstance(value, str)
    if name == "array":
        return isinstance(value, list)
    if name == "object":
        return isinstance(value, dict)
    raise SchemaError("unknown type name %r" % name)


def _equal(a, b):
    # JSON equality: booleans are not numbers.
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    return a == b


def _ptr(path):
    if not path:
        return "/"
    return "".join("/" + str(p).replace("~", "~0").replace("/", "~1") for p in path)


class Validator:
    def __init__(self, schema):
        if not isinstance(schema, dict):
            raise SchemaError("root schema must be an object")
        self.root = schema
        self.check_schema(schema)

    def check_schema(self, schema, where="#"):
        if isinstance(schema, bool):
            return
        if not isinstance(schema, dict):
            raise SchemaError("%s: schema must be an object or boolean" % where)
        unknown = set(schema) - SUPPORTED
        if unknown:
            raise SchemaError("%s: unsupported keyword(s) %s" % (where, sorted(unknown)))
        for key in ("properties", "$defs"):
            for name, sub in schema.get(key, {}).items():
                self.check_schema(sub, "%s/%s/%s" % (where, key, name))
        for key in ("items", "additionalProperties", "not", "if", "then", "else"):
            if key in schema and not isinstance(schema[key], bool):
                self.check_schema(schema[key], "%s/%s" % (where, key))
        for key in ("allOf", "anyOf", "oneOf"):
            for i, sub in enumerate(schema.get(key, [])):
                self.check_schema(sub, "%s/%s/%d" % (where, key, i))
        if "pattern" in schema:
            try:
                re.compile(schema["pattern"])
            except re.error as e:
                raise SchemaError("%s: bad pattern: %s" % (where, e))
        if "$ref" in schema:
            self._resolve(schema["$ref"])

    def _resolve(self, ref):
        if not ref.startswith("#/"):
            raise SchemaError("only local $ref is supported: %r" % ref)
        node = self.root
        for part in ref[2:].split("/"):
            part = part.replace("~1", "/").replace("~0", "~")
            if not isinstance(node, dict) or part not in node:
                raise SchemaError("unresolvable $ref %r" % ref)
            node = node[part]
        return node

    def errors(self, instance):
        """Returns a list of (json_pointer, message), empty when valid."""
        out = []
        self._validate(instance, self.root, [], out)
        return out

    def _validate(self, inst, schema, path, out):
        if schema is True:
            return
        if schema is False:
            out.append((_ptr(path), "no value is allowed here"))
            return
        if "$ref" in schema:
            self._validate(inst, self._resolve(schema["$ref"]), path, out)

        if "type" in schema:
            types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
            if not any(_type_ok(inst, t) for t in types):
                out.append((_ptr(path), "expected type %s" % " or ".join(types)))
                return
        if "enum" in schema and not any(_equal(inst, e) for e in schema["enum"]):
            out.append((_ptr(path), "value %r is not one of %r" % (inst, schema["enum"])))
        if "const" in schema and not _equal(inst, schema["const"]):
            out.append((_ptr(path), "value must be %r" % (schema["const"],)))

        if isinstance(inst, str):
            if "minLength" in schema and len(inst) < schema["minLength"]:
                out.append((_ptr(path), "string shorter than %d" % schema["minLength"]))
            if "maxLength" in schema and len(inst) > schema["maxLength"]:
                out.append((_ptr(path), "string longer than %d" % schema["maxLength"]))
            if "pattern" in schema and not re.search(schema["pattern"], inst):
                out.append((_ptr(path), "does not match pattern %s" % schema["pattern"]))

        if isinstance(inst, (int, float)) and not isinstance(inst, bool):
            if "minimum" in schema and inst < schema["minimum"]:
                out.append((_ptr(path), "less than minimum %r" % schema["minimum"]))
            if "maximum" in schema and inst > schema["maximum"]:
                out.append((_ptr(path), "greater than maximum %r" % schema["maximum"]))
            if "exclusiveMinimum" in schema and inst <= schema["exclusiveMinimum"]:
                out.append((_ptr(path), "must be greater than %r" % schema["exclusiveMinimum"]))
            if "exclusiveMaximum" in schema and inst >= schema["exclusiveMaximum"]:
                out.append((_ptr(path), "must be less than %r" % schema["exclusiveMaximum"]))

        if isinstance(inst, list):
            if "minItems" in schema and len(inst) < schema["minItems"]:
                out.append((_ptr(path), "fewer than %d items" % schema["minItems"]))
            if "maxItems" in schema and len(inst) > schema["maxItems"]:
                out.append((_ptr(path), "more than %d items" % schema["maxItems"]))
            if schema.get("uniqueItems"):
                for i in range(len(inst)):
                    for j in range(i):
                        if _equal(inst[i], inst[j]):
                            out.append((_ptr(path + [i]), "duplicate item"))
            if "items" in schema:
                for i, item in enumerate(inst):
                    self._validate(item, schema["items"], path + [i], out)

        if isinstance(inst, dict):
            for name in schema.get("required", []):
                if name not in inst:
                    out.append((_ptr(path + [name]), "required property is missing"))
            props = schema.get("properties", {})
            for name, value in inst.items():
                if name in props:
                    self._validate(value, props[name], path + [name], out)
                elif "additionalProperties" in schema:
                    ap = schema["additionalProperties"]
                    if ap is False:
                        out.append((_ptr(path + [name]), "unexpected property"))
                    else:
                        self._validate(value, ap, path + [name], out)

        for sub in schema.get("allOf", []):
            self._validate(inst, sub, path, out)
        if "anyOf" in schema:
            if not any(not self._sub_errors(inst, s, path) for s in schema["anyOf"]):
                out.append((_ptr(path), "does not match any allowed form (anyOf)"))
        if "oneOf" in schema:
            n = sum(1 for s in schema["oneOf"] if not self._sub_errors(inst, s, path))
            if n != 1:
                out.append((_ptr(path), "must match exactly one form (oneOf), matched %d" % n))
        if "not" in schema and not self._sub_errors(inst, schema["not"], path):
            out.append((_ptr(path), "matches a forbidden form (not)"))
        if "if" in schema:
            branch = "then" if not self._sub_errors(inst, schema["if"], path) else "else"
            if branch in schema:
                self._validate(inst, schema[branch], path, out)

    def _sub_errors(self, inst, schema, path):
        out = []
        self._validate(inst, schema, path, out)
        return out

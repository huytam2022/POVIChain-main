import json
import os
from typing import Any, Dict, List

from ..core.errors import SchemaError


def load_schema(schema_path: str) -> Dict[str, Any]:
    if not os.path.isfile(schema_path):
        raise SchemaError("schema_file_missing:" + schema_path)
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _type_check(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def _resolve_ref(root: Dict[str, Any], ref: str) -> Dict[str, Any]:
    if not ref.startswith("#/"):
        raise SchemaError("ref_unsupported:" + ref)
    node: Any = root
    for part in ref[2:].split("/"):
        if not isinstance(node, dict) or part not in node:
            raise SchemaError("ref_not_found:" + ref)
        node = node[part]
    return node


def _validate(root: Dict[str, Any], schema: Dict[str, Any], value: Any, path: str, errors: List[str]) -> None:
    if "$ref" in schema:
        target = _resolve_ref(root, schema["$ref"])
        _validate(root, target, value, path, errors)
        return
    if "type" in schema:
        expected = schema["type"]
        if isinstance(expected, list):
            if not any(_type_check(value, e) for e in expected):
                errors.append(path + ":type_mismatch")
                return
        else:
            if not _type_check(value, expected):
                errors.append(path + ":type_mismatch:expected=" + expected)
                return
    if "enum" in schema and value not in schema["enum"]:
        errors.append(path + ":enum_violation")
    if "const" in schema and value != schema["const"]:
        errors.append(path + ":const_violation")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(path + ":minimum_violation")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(path + ":maximum_violation")
        if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
            errors.append(path + ":exclusive_minimum_violation")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(path + "." + key + ":missing_required")
        props = schema.get("properties", {})
        for pname, pschema in props.items():
            if pname in value:
                _validate(root, pschema, value[pname], path + "." + pname, errors)
    if isinstance(value, list):
        items = schema.get("items")
        if items is not None:
            for idx, item in enumerate(value):
                _validate(root, items, item, path + "[" + str(idx) + "]", errors)
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(path + ":min_items_violation")


def validate_json_against_schema(data: Any, schema: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    _validate(schema, schema, data, "$", errors)
    return errors

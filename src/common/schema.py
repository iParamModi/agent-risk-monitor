"""Validate records against configs/schemas/*.schema.json."""
import json
from functools import lru_cache

from jsonschema import Draft202012Validator

from src.common.io import REPO_ROOT

SCHEMA_DIR = REPO_ROOT / "configs" / "schemas"


@lru_cache(maxsize=None)
def validator(name: str = "record") -> Draft202012Validator:
    schema = json.loads((SCHEMA_DIR / f"{name}.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def schema_errors(obj: dict, name: str = "record") -> list[str]:
    """Empty list means valid."""
    return [f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}"
            for e in validator(name).iter_errors(obj)]

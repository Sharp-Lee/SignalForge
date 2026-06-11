import json
from pathlib import Path


_SCHEMA_FILES = {
    "signal-contract": "signal-contract.schema.json",
    "thesis-contract": "thesis-contract.schema.json",
    "target-contract": "target-contract.schema.json",
}


def load_contract_schema(name: str) -> dict:
    try:
        filename = _SCHEMA_FILES[name]
    except KeyError as exc:
        raise ValueError(f"unknown contract schema: {name}") from exc

    path = Path(__file__).with_name(filename)
    return json.loads(path.read_text(encoding="utf-8"))


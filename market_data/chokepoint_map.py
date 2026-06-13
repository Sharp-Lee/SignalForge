"""Structured chokepoint map loader for deriving the reviewed A-share universe.

Names recorded in the map are review snapshots only. Runtime target-universe
construction must continue stamping company names from market-data providers.
"""

from __future__ import annotations

from pathlib import Path
import json
from typing import Any, Literal, NotRequired, TypedDict


SCHEMA_VERSION = "0.1"
DEFAULT_MAP_PATH = Path(__file__).resolve().parent.parent / "config" / "chokepoint_map.json"


class ChokepointMapError(RuntimeError):
    """Raised when the chokepoint map cannot be loaded safely."""


class AShareRecord(TypedDict):
    code: str
    name: str
    role: NotRequired[str]
    purity: NotRequired[Literal["high", "mid", "low"]]
    confidence: NotRequired[Literal["high", "mid", "low"]]


class ChokepointNode(TypedDict, total=False):
    domain: str
    curation_status: Literal["seed", "curated"]
    branch: list[str]
    node: str
    structure: Literal["monopoly", "oligopoly", "fragmented"]
    chokepoint_holder: str
    china_position: Literal["dominant", "substitute", "absent"]
    elasticity: Literal["high", "mid", "low"]
    triggers: list[str]
    a_share: list[AShareRecord]
    caveats: list[str]
    evidence: list[str]
    screen_pass: bool | None


class ChokepointMap(TypedDict):
    schema_version: str
    nodes: list[ChokepointNode]


class CompactChokepointNode(TypedDict):
    node: str
    chokepoint_holder: str
    china_position: str
    triggers: list[str]
    a_share: list[dict[str, str]]


_STRUCTURES = {"monopoly", "oligopoly", "fragmented"}
_CHINA_POSITIONS = {"dominant", "substitute", "absent"}
_LEVELS = {"high", "mid", "low"}


def load_map(path: str | Path | None = None) -> ChokepointMap:
    """Load and lightly validate the chokepoint map."""

    map_path = Path(path) if path is not None else DEFAULT_MAP_PATH
    try:
        with map_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError as exc:
        raise ChokepointMapError(f"chokepoint map not found: {map_path}") from exc
    except json.JSONDecodeError as exc:
        raise ChokepointMapError(f"invalid chokepoint map JSON at {map_path}: {exc.msg}") from exc
    except OSError as exc:
        raise ChokepointMapError(f"could not read chokepoint map {map_path}: {exc}") from exc

    _validate_map(payload, map_path)
    return payload


def universe_codes(path: str | Path | None = None) -> list[str]:
    """Return included A-share codes in map order, de-duplicated by first use."""

    codes: list[str] = []
    seen: set[str] = set()
    for node in load_map(path)["nodes"]:
        status = node["curation_status"]
        included = status == "seed" or (status == "curated" and node.get("screen_pass") is True)
        if not included:
            continue
        for record in node["a_share"]:
            code = record["code"]
            if code not in seen:
                seen.add(code)
                codes.append(code)
    return codes


def symbol_names(path: str | Path | None = None) -> dict[str, str]:
    """Return map-recorded code names for review display, not runtime stamping."""

    names: dict[str, str] = {}
    for node in load_map(path)["nodes"]:
        for record in node["a_share"]:
            code = record["code"]
            if code not in names:
                names[code] = record.get("name", "")
    return names


def trigger_index(path: str | Path | None = None) -> dict[str, list[str]]:
    """Return curated node trigger strings keyed by node name."""

    index: dict[str, list[str]] = {}
    for node in load_map(path)["nodes"]:
        if node["curation_status"] != "curated":
            continue
        node_name = node.get("node")
        triggers = node.get("triggers") or []
        if node_name and triggers:
            index[node_name] = list(triggers)
    return index


def curated_nodes(path: str | Path | None = None) -> list[CompactChokepointNode]:
    """Return compact curated screen-passing nodes for relevance matching."""

    compact: list[CompactChokepointNode] = []
    for node in load_map(path)["nodes"]:
        if node["curation_status"] != "curated" or node.get("screen_pass") is not True:
            continue
        compact.append(
            {
                "node": node["node"],
                "chokepoint_holder": node["chokepoint_holder"],
                "china_position": node["china_position"],
                "triggers": list(node.get("triggers") or []),
                "a_share": [
                    {
                        "code": record["code"],
                        "name": record.get("name", ""),
                    }
                    for record in node.get("a_share", [])
                ],
            }
        )
    return compact


def _validate_map(payload: Any, path: Path) -> None:
    if not isinstance(payload, dict):
        raise ChokepointMapError(f"{path}: top-level map must be an object")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ChokepointMapError(f"{path}: schema_version must be {SCHEMA_VERSION!r}")
    nodes = payload.get("nodes")
    if not isinstance(nodes, list):
        raise ChokepointMapError(f"{path}: nodes must be an array")
    for index, node in enumerate(nodes):
        _validate_node(node, f"nodes[{index}]")


def _validate_node(node: Any, location: str) -> None:
    if not isinstance(node, dict):
        raise ChokepointMapError(f"{location}: node must be an object")
    _require_nonempty_string(node, "domain", location)
    status = node.get("curation_status")
    if status not in {"seed", "curated"}:
        raise ChokepointMapError(f"{location}: curation_status must be seed or curated")
    records = node.get("a_share")
    if status == "seed":
        if node.get("screen_pass") is True:
            raise ChokepointMapError(f"{location}: seed node must not set screen_pass true")
        if not isinstance(records, list) or not records:
            raise ChokepointMapError(f"{location}: seed node requires at least one a_share record")
    else:
        _validate_curated_node(node, location)
        if not isinstance(records, list):
            raise ChokepointMapError(f"{location}: curated node requires a_share array")

    for record_index, record in enumerate(records):
        _validate_a_share_record(record, f"{location}.a_share[{record_index}]")

    for field in ("caveats",):
        if field in node:
            _require_string_list(node[field], f"{location}.{field}")


def _validate_curated_node(node: dict, location: str) -> None:
    _require_string_list(node.get("branch"), f"{location}.branch")
    _require_nonempty_string(node, "node", location)
    _require_enum(node, "structure", _STRUCTURES, location)
    _require_nonempty_string(node, "chokepoint_holder", location)
    _require_enum(node, "china_position", _CHINA_POSITIONS, location)
    _require_enum(node, "elasticity", _LEVELS, location)
    _require_string_list(node.get("triggers"), f"{location}.triggers")
    _require_string_list(node.get("evidence"), f"{location}.evidence")
    if not isinstance(node.get("screen_pass"), bool):
        raise ChokepointMapError(f"{location}: screen_pass must be boolean for curated nodes")


def _validate_a_share_record(record: Any, location: str) -> None:
    if not isinstance(record, dict):
        raise ChokepointMapError(f"{location}: a_share record must be an object")
    _require_nonempty_string(record, "code", location)
    if "name" in record and not isinstance(record["name"], str):
        raise ChokepointMapError(f"{location}: name must be a string when present")
    for field in ("role",):
        if field in record and not isinstance(record[field], str):
            raise ChokepointMapError(f"{location}: {field} must be a string when present")
    for field in ("purity", "confidence"):
        if field in record and record[field] not in _LEVELS:
            raise ChokepointMapError(f"{location}: {field} must be one of {sorted(_LEVELS)}")


def _require_nonempty_string(node: dict, field: str, location: str) -> None:
    value = node.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ChokepointMapError(f"{location}: {field} must be a non-empty string")


def _require_enum(node: dict, field: str, allowed: set[str], location: str) -> None:
    value = node.get(field)
    if value not in allowed:
        raise ChokepointMapError(f"{location}: {field} must be one of {sorted(allowed)}")


def _require_string_list(value: Any, location: str) -> None:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ChokepointMapError(f"{location}: must be a list of non-empty strings")

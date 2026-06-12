import json

import pytest
from jsonschema import Draft202012Validator, ValidationError

from market_data import DEFAULT_A_SHARE_ALLOWLIST
from market_data.chokepoint_map import ChokepointMapError, load_map, symbol_names, trigger_index, universe_codes


OLD_A_SHARE_ALLOWLIST = [
    "300308.SZ",
    "300502.SZ",
    "002463.SZ",
    "002851.SZ",
    "300394.SZ",
    "300570.SZ",
    "300620.SZ",
    "300548.SZ",
    "688498.SH",
    "688205.SH",
    "600522.SH",
    "600487.SH",
    "002281.SZ",
    "000988.SZ",
    "002916.SZ",
    "603228.SH",
    "002384.SZ",
    "600183.SH",
    "688183.SH",
    "002436.SZ",
    "300476.SZ",
    "002475.SZ",
    "601138.SH",
    "000977.SZ",
    "603019.SH",
    "000938.SZ",
    "688041.SH",
    "688256.SH",
    "603986.SH",
    "002371.SZ",
    "688012.SH",
    "688008.SH",
    "002156.SZ",
    "600584.SH",
    "688525.SH",
    "000063.SZ",
    "300604.SZ",
    "688072.SH",
    "688409.SH",
    "688981.SH",
]


CHOKEPOINT_MAP_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "required": ["schema_version", "nodes"],
    "properties": {
        "schema_version": {"const": "0.1"},
        "nodes": {
            "type": "array",
            "items": {"$ref": "#/$defs/node"},
        },
    },
    "$defs": {
        "a_share": {
            "type": "object",
            "additionalProperties": False,
            "required": ["code"],
            "properties": {
                "code": {"type": "string", "minLength": 1},
                "name": {"type": "string"},
                "role": {"type": "string"},
                "purity": {"enum": ["high", "mid", "low"]},
                "confidence": {"enum": ["high", "mid", "low"]},
            },
        },
        "node": {
            "type": "object",
            "additionalProperties": False,
            "required": ["domain", "curation_status", "a_share"],
            "properties": {
                "domain": {"type": "string", "minLength": 1},
                "curation_status": {"enum": ["seed", "curated"]},
                "branch": {"type": "array", "items": {"type": "string", "minLength": 1}},
                "node": {"type": "string", "minLength": 1},
                "structure": {"enum": ["monopoly", "oligopoly", "fragmented"]},
                "chokepoint_holder": {"type": "string", "minLength": 1},
                "china_position": {"enum": ["dominant", "substitute", "absent"]},
                "elasticity": {"enum": ["high", "mid", "low"]},
                "triggers": {"type": "array", "items": {"type": "string", "minLength": 1}},
                "a_share": {"type": "array", "items": {"$ref": "#/$defs/a_share"}},
                "caveats": {"type": "array", "items": {"type": "string"}},
                "evidence": {"type": "array", "items": {"type": "string", "minLength": 1}},
                "screen_pass": {"type": ["boolean", "null"]},
            },
            "allOf": [
                {
                    "if": {"properties": {"curation_status": {"const": "seed"}}},
                    "then": {
                        "properties": {"a_share": {"minItems": 1}},
                        "not": {
                            "required": ["screen_pass"],
                            "properties": {"screen_pass": {"const": True}},
                        },
                    },
                },
                {
                    "if": {"properties": {"curation_status": {"const": "curated"}}},
                    "then": {
                        "required": [
                            "branch",
                            "node",
                            "structure",
                            "chokepoint_holder",
                            "china_position",
                            "elasticity",
                            "triggers",
                            "evidence",
                            "screen_pass",
                        ],
                        "properties": {"a_share": {"type": "array"}},
                    },
                },
            ],
        },
    },
}


def test_chokepoint_map_seed_json_validates_against_schema():
    Draft202012Validator(CHOKEPOINT_MAP_SCHEMA).validate(load_map())


def test_curated_node_missing_required_fields_is_rejected_by_schema():
    malformed = {
        "schema_version": "0.1",
        "nodes": [
            {
                "domain": "AI生态",
                "curation_status": "curated",
                "a_share": [],
                "screen_pass": True,
            }
        ],
    }

    with pytest.raises(ValidationError):
        Draft202012Validator(CHOKEPOINT_MAP_SCHEMA).validate(malformed)


def test_seed_node_must_not_claim_screen_pass_true():
    malformed = {
        "schema_version": "0.1",
        "nodes": [
            {
                "domain": "AI生态",
                "curation_status": "seed",
                "screen_pass": True,
                "a_share": [{"code": "300308.SZ", "name": ""}],
            }
        ],
    }

    with pytest.raises(ValidationError):
        Draft202012Validator(CHOKEPOINT_MAP_SCHEMA).validate(malformed)


def test_universe_codes_match_old_allowlist_exactly():
    assert universe_codes() == OLD_A_SHARE_ALLOWLIST
    assert set(universe_codes()) == set(OLD_A_SHARE_ALLOWLIST)
    assert DEFAULT_A_SHARE_ALLOWLIST == OLD_A_SHARE_ALLOWLIST


def test_loader_interfaces_return_initial_seed_shapes():
    loaded = load_map()
    names = symbol_names()

    assert loaded["schema_version"] == "0.1"
    assert len(loaded["nodes"]) == 40
    assert names["300308.SZ"] == "中际旭创"
    assert all(names.values())  # seed names tushare-stamped; no empty placeholder remains
    assert len(names) == 40
    assert trigger_index() == {}


def test_universe_codes_preserve_order_and_dedupe_first_occurrence(tmp_path):
    path = tmp_path / "map.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                "nodes": [
                    {"domain": "AI生态", "curation_status": "seed", "a_share": [{"code": "300001.SZ", "name": "A"}]},
                    {"domain": "AI生态", "curation_status": "seed", "a_share": [{"code": "300002.SZ", "name": "B"}]},
                    {"domain": "AI生态", "curation_status": "seed", "a_share": [{"code": "300001.SZ", "name": "A2"}]},
                    {
                        "domain": "AI生态",
                        "curation_status": "curated",
                        "branch": ["算力"],
                        "node": "不通过节点",
                        "structure": "fragmented",
                        "chokepoint_holder": "none",
                        "china_position": "dominant",
                        "elasticity": "low",
                        "triggers": ["ignore"],
                        "a_share": [{"code": "300003.SZ", "name": "C"}],
                        "evidence": ["fixture"],
                        "screen_pass": False,
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    assert universe_codes(path) == ["300001.SZ", "300002.SZ"]
    assert symbol_names(path) == {"300001.SZ": "A", "300002.SZ": "B", "300003.SZ": "C"}


def test_trigger_index_returns_curated_node_triggers(tmp_path):
    path = tmp_path / "map.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                "nodes": [
                    {
                        "domain": "AI生态",
                        "curation_status": "curated",
                        "branch": ["算力", "网络"],
                        "node": "CPO",
                        "structure": "oligopoly",
                        "chokepoint_holder": "global optical module leaders",
                        "china_position": "substitute",
                        "elasticity": "high",
                        "triggers": ["co-packaged optics", "CPO"],
                        "a_share": [{"code": "300308.SZ", "name": "中际旭创"}],
                        "evidence": ["fixture"],
                        "screen_pass": True,
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    assert trigger_index(path) == {"CPO": ["co-packaged optics", "CPO"]}


def test_load_map_reports_invalid_json_clearly(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not-json", encoding="utf-8")

    with pytest.raises(ChokepointMapError, match="invalid chokepoint map JSON"):
        load_map(path)


def test_runtime_loader_rejects_malformed_curated_node(tmp_path):
    path = tmp_path / "bad-curated.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                "nodes": [
                    {
                        "domain": "AI生态",
                        "curation_status": "curated",
                        "a_share": [],
                        "screen_pass": True,
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ChokepointMapError, match="branch"):
        load_map(path)

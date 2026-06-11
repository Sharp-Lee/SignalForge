from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .validation import (
    CalibrationNotImplemented,
    ContractError,
    DEFAULT_DEDUP_THRESHOLD,
    dedup_hash,
    validate_signal,
    validate_target,
    validate_thesis,
)


class ContractStore:
    def __init__(self, path: str | Path, dedup_threshold: float = DEFAULT_DEDUP_THRESHOLD):
        self.path = Path(path)
        self.dedup_threshold = dedup_threshold
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("pragma foreign_keys = on")
        self._create_tables()

    def add_signal(self, signal: dict) -> str:
        existing = self._recent_signals()
        result = validate_signal(signal, existing=existing, dedup_threshold=self.dedup_threshold)
        if not result.accepted:
            raise ContractError(result.reason or "signal rejected")
        record = result.record
        hash_value = dedup_hash(record)
        with self.connection:
            self.connection.execute(
                """
                insert into signals (
                    id, source_id, published_at, url, signal_origin, type_tag, dedup_hash, payload_json, raw_payload_json
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["id"],
                    record["source"]["id"],
                    record["source"]["published_at"],
                    record["source"]["url"],
                    record["signal_origin"],
                    record["type_tag"],
                    hash_value,
                    json.dumps(record, ensure_ascii=False, sort_keys=True),
                    json.dumps(record.get("raw_payload", {}), ensure_ascii=False, sort_keys=True),
                ),
            )
        return record["id"]

    def add_thesis(self, thesis: dict) -> str:
        result = validate_thesis(thesis)
        record = result.record
        with self.connection:
            self.connection.execute(
                "insert into theses (id, status, payload_json) values (?, ?, ?)",
                (record["id"], record["status"], json.dumps(record, ensure_ascii=False, sort_keys=True)),
            )
            if record.get("track_record"):
                track = record["track_record"]
                self.connection.execute(
                    """
                    insert into track_record (
                        thesis_id, direction, falsifiable_expectation, window_start, window_end, created_at, result_json
                    ) values (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record["id"],
                        track["direction"],
                        track["falsifiable_expectation"],
                        track["verification_window"]["start"],
                        track["verification_window"]["end"],
                        track["created_at"],
                        None,
                    ),
                )
            if record["status"] == "confirmed":
                for index, step in enumerate(record.get("transmission_path", [])):
                    self.connection.execute(
                        """
                        insert into transmission_map (
                            thesis_id, step_index, description, source_signal_ids_json
                        ) values (?, ?, ?, ?)
                        """,
                        (
                            record["id"],
                            index,
                            step["description"],
                            json.dumps(step.get("source_signal_ids", []), ensure_ascii=False, sort_keys=True),
                        ),
                    )
        return record["id"]

    def add_target(self, target: dict, confirmed_thesis_ids: set[str] | None = None) -> str:
        confirmed = confirmed_thesis_ids if confirmed_thesis_ids is not None else self._confirmed_thesis_ids()
        result = validate_target(target, confirmed_thesis_ids=confirmed)
        record = result.record
        with self.connection:
            self.connection.execute(
                "insert into targets (id, symbol, state, payload_json) values (?, ?, ?, ?)",
                (record["id"], record["symbol"], record["state"], json.dumps(record, ensure_ascii=False, sort_keys=True)),
            )
        return record["id"]

    def record_outcome(self, thesis_id: str, result: dict) -> None:
        with self.connection:
            self.connection.execute(
                "update track_record set result_json = ? where thesis_id = ?",
                (json.dumps(result, ensure_ascii=False, sort_keys=True), thesis_id),
            )

    def backfill_track_record_result(self, thesis_id: str, result: dict) -> None:
        self.record_outcome(thesis_id, result)

    def get_source_cursor(self, source_id: str) -> str | None:
        row = self.connection.execute(
            "select cursor from source_cursors where source_id = ?",
            (source_id,),
        ).fetchone()
        return row["cursor"] if row else None

    def set_source_cursor(self, source_id: str, cursor: str | None) -> None:
        with self.connection:
            self.connection.execute(
                """
                insert into source_cursors (source_id, cursor, updated_at)
                values (?, ?, datetime('now'))
                on conflict(source_id) do update set
                    cursor = excluded.cursor,
                    updated_at = excluded.updated_at
                """,
                (source_id, cursor),
            )

    def add_human_decision(self, decision: dict) -> None:
        if decision.get("decision") not in {"accepted", "rejected", "overridden"}:
            raise ContractError("human decision must be accepted, rejected, or overridden")
        for field_name in ("subject_type", "subject_id", "reason", "decided_at"):
            if not decision.get(field_name):
                raise ContractError(f"human decision {field_name} is required")
        with self.connection:
            self.connection.execute(
                """
                insert into human_decisions (
                    subject_type, subject_id, decision, reason, decided_at, payload_json
                ) values (?, ?, ?, ?, ?, ?)
                """,
                (
                    decision["subject_type"],
                    decision["subject_id"],
                    decision["decision"],
                    decision["reason"],
                    decision["decided_at"],
                    json.dumps(decision, ensure_ascii=False, sort_keys=True),
                ),
            )

    def calibrate(self) -> None:
        raise CalibrationNotImplemented(
            "feedback calibration is intentionally out of scope for define-core-contracts"
        )

    def _recent_signals(self) -> list[dict]:
        rows = self.connection.execute(
            "select payload_json from signals order by published_at desc limit 500"
        ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def _confirmed_thesis_ids(self) -> set[str]:
        rows = self.connection.execute(
            "select id from theses where status = 'confirmed'"
        ).fetchall()
        return {row["id"] for row in rows}

    def _create_tables(self) -> None:
        with self.connection:
            self.connection.executescript(
                """
                create table if not exists signals (
                    id text primary key,
                    source_id text not null,
                    published_at text not null,
                    url text not null,
                    signal_origin text not null,
                    type_tag text not null,
                    dedup_hash text not null unique,
                    payload_json text not null,
                    raw_payload_json text not null
                );

                create table if not exists theses (
                    id text primary key,
                    status text not null,
                    payload_json text not null
                );

                create table if not exists targets (
                    id text primary key,
                    symbol text not null,
                    state text not null,
                    payload_json text not null
                );

                create table if not exists track_record (
                    thesis_id text primary key,
                    direction text not null,
                    falsifiable_expectation text not null,
                    window_start text not null,
                    window_end text not null,
                    created_at text not null,
                    result_json text,
                    foreign key (thesis_id) references theses(id)
                );

                create table if not exists source_cursors (
                    source_id text primary key,
                    cursor text,
                    updated_at text
                );

                create table if not exists human_decisions (
                    id integer primary key autoincrement,
                    subject_type text not null,
                    subject_id text not null,
                    decision text not null,
                    reason text not null,
                    decided_at text not null,
                    payload_json text not null
                );

                create table if not exists transmission_map (
                    id integer primary key autoincrement,
                    thesis_id text not null,
                    step_index integer not null,
                    description text not null,
                    source_signal_ids_json text not null,
                    foreign key (thesis_id) references theses(id)
                );
                """
            )

from __future__ import annotations

from news_contracts.validation import ContractError
from source_ingestion.core import IngestionRunResult, SourceRunResult


def run_once(store, adapters) -> IngestionRunResult:
    result = IngestionRunResult()
    for adapter in adapters:
        source_id = adapter.source_id
        source_result = SourceRunResult(source_id=source_id)
        cursor = store.get_source_cursor(source_id)
        try:
            fetched = adapter.fetch(cursor)
        except Exception as exc:
            source_result.errors.append(str(exc))
            result.by_source[source_id] = source_result
            continue
        for raw_item in fetched.items:
            try:
                signals = adapter.normalize(raw_item)
            except Exception as exc:
                source_result.rejected += 1
                source_result.errors.append(str(exc))
                continue
            for signal in signals:
                try:
                    store.add_signal(signal)
                    source_result.accepted += 1
                except ContractError as exc:
                    source_result.rejected += 1
                    source_result.errors.append(str(exc))
        store.set_source_cursor(source_id, fetched.next_cursor)
        result.by_source[source_id] = source_result
    return result

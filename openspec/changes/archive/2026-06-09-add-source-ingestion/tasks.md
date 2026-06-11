## 1. Planning Validation

- [x] 1.1 Validate `add-source-ingestion` planning artifacts with OpenSpec strict mode

## 2. Adapter Protocol

- [x] 2.1 Add source-ingestion module structure
- [x] 2.2 Define Adapter protocol, fetch result, run result, and fixture fetcher shape
- [x] 2.3 Ensure Adapter fetch and normalize are separated and network I/O is injectable

## 3. Reference Adapters

- [x] 3.1 Implement RSS/Atom fixture Adapter producing `signal_origin = news`
- [x] 3.2 Implement GDELT-shaped fixture Adapter producing `signal_origin = news`
- [x] 3.3 Wrap existing last30days normalization in the unified Adapter framework
- [x] 3.4 Implement reverse-intake market move Adapter producing `signal_origin = market_move`

## 4. Cursor And Runner

- [x] 4.1 Add `source_cursors` read/write helpers to `ContractStore`
- [x] 4.2 Implement one-shot ingestion runner that calls `ContractStore.add_signal`
- [x] 4.3 Make repeated fixture runs idempotent and report rejections without aborting the run

## 5. Tests And Verification

- [x] 5.1 Add fixture tests for each Adapter and reverse-intake hard gate
- [x] 5.2 Add runner tests for persistence, cursor update, and idempotency
- [x] 5.3 Run `python3 -m pytest -q`
- [x] 5.4 Run `openspec validate add-source-ingestion --strict`

## 1. Planning

- [x] 1.1 Validate `add-real-fetchers` planning artifacts with OpenSpec strict mode

## 2. RSS/Atom Real Fetcher

- [x] 2.1 Implement injectable HTTP transport shape for RSS/Atom fetching
- [x] 2.2 Parse common RSS and Atom feed XML into raw adapter items
- [x] 2.3 Apply cursor-driven filtering so repeated fetches return only new entries

## 3. last30days Real Fetcher

- [x] 3.1 Implement injectable subprocess transport shape for last30days
- [x] 3.2 Build the real topic-query command without unsupported cursor flags
- [x] 3.3 Parse real `--emit=json` report output through `Last30DaysAdapter`

## 4. Runner Hardening

- [x] 4.1 Catch adapter fetch-level exceptions as source errors
- [x] 4.2 Continue processing remaining sources after one source fails
- [x] 4.3 Do not advance a failed source cursor
- [x] 4.4 Catch adapter normalize-level exceptions per raw item as source rejections/errors

## 5. Tests And Verification

- [x] 5.1 Add offline RSS fetcher tests for injected transport and cursor increment
- [x] 5.2 Add offline last30days fetcher tests for injected subprocess transport and cursor command
- [x] 5.3 Add runner tests for fetch failure isolation
- [x] 5.4 Add runner tests for normalize failure isolation
- [x] 5.5 Run `python3 -m pytest -q`
- [x] 5.6 Run `openspec validate add-real-fetchers --strict`

## ADDED Requirements

### Requirement: Browser User Agent For RSS HTTP Fetch
The default RSS/Atom HTTP fetcher SHALL send a browser-like User-Agent when performing real HTTP requests. Injected HTTP transports used by tests MUST remain supported and MUST NOT perform real network I/O.

#### Scenario: Default RSS fetch uses browser headers
- **WHEN** the default RSS HTTP transport performs a real request
- **THEN** it includes a browser-like `User-Agent` header

#### Scenario: Injected transport remains isolated
- **WHEN** an RSS fetcher is constructed with an injected HTTP transport
- **THEN** the fetcher uses the injected transport and does not perform default HTTP request construction

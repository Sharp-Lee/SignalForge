## Context

The persistent store contains the information needed for a daily public-account draft:

- `theses.payload_json` stores the confirmed thesis body, direction, confidence, and adversarial falsification.
- `track_record.created_at` records when the thesis entered the system.
- `targets.payload_json` stores the current watchlist view, including name, symbol, logic score, catalysts, exit triggers, price movement, and priced-in data.

The digest is an operation/readout artifact. It should not become a second contract store, a delivery system, or a new analysis layer.

## Decisions

### D1 Read-Only Store Access

`scripts/generate_digest.py` opens the SQLite database with `mode=ro` and reads existing rows directly. It does not instantiate `ContractStore`, because `ContractStore` creates tables on construction and is write-capable by design.

If the store path is missing, the script generates an empty/no-new-content digest instead of creating a database.

### D2 Date Window

Same-day theses are selected by `track_record.created_at` date prefix matching `--date YYYY-MM-DD`. This uses the existing durable timestamp written by `ContractStore.add_thesis()` and avoids adding another digest-specific timestamp.

Targets are treated as the current watchlist and are read from the `targets` table, sorted by logic score descending and symbol for stable output.

### D3 Two Output Formats

The generator writes:

- `<date>.md`: clean Markdown for review, versioning, or manual editing.
- `<date>.html`: WeChat-editor-friendly HTML using inline `style` attributes only. It emits no `<style>` or `<script>` tags because public-account editors commonly strip them.

### D4 Reader Framing

The digest is written for non-expert relatives and friends. Static labels, section titles, direction, confidence, observation conditions, invalidation conditions, and risk levels are Chinese. The system does not call an LLM to rewrite thesis bodies; it extracts a short body preview and labels it as a research logic summary.

The wording stays in the frame of "personal research notes" and avoids recommendation language. Public digest cards do not show `buy_point.status`, because "买点较好/偏贵" can read like public buy/sell advice. Instead, target sections are framed as "观察对象" with neutral follow-up conditions.

### D5 Logic-Chain Cards

The digest is organized by investment logic rather than separate thesis and target lists. Each same-day thesis becomes one card:

1. Trigger information: source signals linked by `thesis.source_signal_ids`, including title, source name, published time, and URL.
2. World context: a deterministic summary of the cross-market frame (`origin_market -> target_market`) and the signal themes involved.
3. Supporting logic: extracted `transmission_path` steps.
4. Confirmed logic: the thesis body.
5. Strongest counterargument: `adversarial_falsification.strongest_counterargument`.
6. Observation objects: only targets whose `thesis_ids` include this thesis id, shown with logic relevance, neutral price/risk context, observation conditions from catalysts, and invalidation conditions from exit triggers.

This preserves the reader-facing chain: "which information created which logic, and which objects are worth following because of that logic." Targets linked only to older theses are not shown under today's logic cards.

## Risks / Trade-offs

- [Risk] Thesis body may be English or too technical. -> Mitigation: keep the excerpt short, translate categorical labels, and leave full narrative rewriting to a later editorial/delivery change if needed.
- [Risk] Opening the store through normal sqlite could create a new empty file. -> Mitigation: use URI `mode=ro` and handle missing paths before connecting.
- [Risk] Public-account HTML rendering can vary. -> Mitigation: use simple block elements and inline styles only.
- [Risk] Missing source rows could break traceability. -> Mitigation: render the signal id with "来源未知" instead of failing the whole digest.

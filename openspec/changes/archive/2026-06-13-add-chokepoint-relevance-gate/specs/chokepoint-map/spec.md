## ADDED Requirements

### Requirement: Curated Node Matching View
The chokepoint map loader SHALL expose a compact curated-node view for relevance matching. The view MUST include only nodes with `curation_status = curated` and `screen_pass = true`. Each returned node MUST include node name, chokepoint holder, China position, triggers, and compact A-share code/name records. Seed nodes MUST NOT appear in this view.

#### Scenario: Curated nodes exclude seed nodes
- **WHEN** `curated_nodes()` is called
- **THEN** every returned item is a curated `screen_pass = true` node
- **AND** no seed node is returned

#### Scenario: Curated nodes expose compact matching fields
- **WHEN** `curated_nodes()` returns a node
- **THEN** the node includes `node`, `chokepoint_holder`, `china_position`, `triggers`, and `a_share[].code`

## MODIFIED Requirements

### Requirement: Cluster Triage Role
The LLM provider SHALL define a cluster triage role that selects pending signal clusters for deep analysis. The triage prompt MUST ask for Simplified Chinese reasons and MUST judge whether each selected cluster has real tradeable value for an AI ecosystem to A-share research workflow, including hardware, semiconductors, power/energy, data-center infrastructure, cooling, storage, and AI software adoption. The prompt MUST explicitly exclude generic commentary, market chatter, vendor marketing, pure product reviews, duplicate news, and broad technology opinion.

When curated chokepoint nodes are supplied, the triage prompt MUST include a compact list of those nodes with node name, chokepoint holder, and triggers. In that mode the prompt MUST instruct the model to prefer clusters that materially affect a supplied node's industry-level supply, demand, price, capacity, orders, domestic substitution, or competitive structure. It MUST also instruct the model to deprioritize single terminal-product launches, reviews, workstation/laptop/mini-PC/NAS/single-server news, consumer-device news, and expo demos even when they mention advanced chips. The output schema MUST remain the existing selected-cluster schema.

#### Scenario: Triage prompt describes selection criteria
- **WHEN** a triage prompt is built for candidate clusters
- **THEN** it describes AI ecosystem A-share research value, exclusion criteria, and Chinese reason output

#### Scenario: Chokepoint context is injected when supplied
- **WHEN** a triage prompt is built with curated chokepoint nodes
- **THEN** the prompt includes node names, chokepoint holders, and triggers
- **AND** it tells the model to prefer true chokepoint catalysts and mention the matched node in the Chinese reason

#### Scenario: Product noise is deprioritized with chokepoint context
- **WHEN** a triage prompt is built with curated chokepoint nodes
- **THEN** it tells the model that terminal-product launches, reviews, NAS, mini-PCs, laptops, workstations, single servers, consumer devices, and expo demos are lowest-priority unless they materially change a supplied chokepoint node

#### Scenario: Missing chokepoint context preserves legacy triage payload
- **WHEN** a triage prompt is built without curated chokepoint nodes
- **THEN** it does not include chokepoint-node context
- **AND** it keeps the existing selected-cluster output schema

## ADDED Requirements

### Requirement: Canonical Investment Logic Types
The system SHALL define a canonical set of investment logic types for classifying high-value signals before downstream chokepoint or target mapping. The initial set MUST include `supply_demand`, `substitution`, `optimization`, `policy_market_reform`, `penetration`, `margin_spread_repricing`, `technology_route_shift`, `policy_constraint_shock`, `business_model_shift`, `investment_order_cycle`, `competitive_structure`, `market_access_expansion`, `asset_capital_revaluation`, and `fundamental_delivery_inflection`.

#### Scenario: Taxonomy contains core narrative types
- **WHEN** the taxonomy is reviewed
- **THEN** it includes supply/demand, substitution, optimization, policy/market reform, penetration, margin-spread repricing, technology route-shift, policy constraint shock, business-model shift, investment/order cycle, competitive-structure, market-access, asset/capital revaluation, and fundamental-delivery logic types

### Requirement: Primary Logic With Optional Secondary Logic
The taxonomy SHALL allow a signal to have multiple logic types, but any future runtime classification MUST identify exactly one primary logic type plus zero or more secondary logic types. The primary logic type MUST represent the first causal entrance through which the news changes economic value; secondary logic types MUST represent transmission or accompanying mechanisms.

#### Scenario: Export control has a primary constraint logic
- **WHEN** a signal contains both export-control and domestic-substitution implications
- **THEN** the taxonomy permits `policy_constraint_shock` and `substitution`
- **AND** a future runtime classifier must choose the first causal entrance as primary rather than treating both labels as equal

#### Scenario: HBM shortage has secondary repricing logic
- **WHEN** a signal states that HBM capacity is sold out and prices may rise
- **THEN** `supply_demand` can be primary
- **AND** `margin_spread_repricing` can be secondary if retained margin is part of the transmission chain

### Requirement: Logic Type Reasoning Templates
Each investment logic type SHALL define a reasoning template. The template MUST include signal patterns, primary/secondary/not-this boundaries, premise validation, upward validation, transmission-chain questions, downstream decomposition questions, chokepoint-map usage, target-search guidance, minimum evidence threshold, falsification points, rejection cases, uncertainty tags, and public-facing caveat guidance.

#### Scenario: Supply-demand logic has validation and rejection rules
- **WHEN** the `supply_demand` template is reviewed
- **THEN** it includes questions for distinguishing structural demand from inventory restocking
- **AND** it rejects vague demand claims with no quantity, time window, price, backlog, utilization, inventory, order, or corroboration

#### Scenario: Substitution logic requires adoption evidence
- **WHEN** the `substitution` template is reviewed
- **THEN** it requires identifying the incumbent, the substitute, the product or chain step, and evidence such as customer qualification, design win, certification, or real supplier switch

#### Scenario: Route-shift logic handles winners and losers
- **WHEN** the `technology_route_shift` template is reviewed
- **THEN** it includes questions for old-route losers, new-route winners, switching cost, maturity, bridge beneficiaries, bypass risk, and route-delay falsification

### Requirement: Fail-Closed Logic Classification
The taxonomy SHALL define fail-closed evidence guidance so weak news does not automatically proceed into target search. Each logic type MUST define a minimum evidence threshold, rejection cases, uncertainty tags, and falsification points. Future runtime use SHOULD distinguish accepted, weak, and rejected logic states.

#### Scenario: Weak evidence does not force target search
- **WHEN** a signal only contains theme language without hard evidence or economic transmission
- **THEN** the taxonomy requires it to be treated as weak or rejected logic
- **AND** target search must not be implied by the taxonomy label alone

#### Scenario: Fundamental delivery requires a concrete metric
- **WHEN** a signal claims that a thesis is being delivered
- **THEN** `fundamental_delivery_inflection` requires concrete operating or financial evidence such as orders, revenue, margin, utilization, yield, cash flow, or guidance quality

### Requirement: Boundary Rules Between Neighboring Logic Types
The taxonomy SHALL define boundary rules for logic types that commonly overlap. These rules MUST prevent shallow tag accumulation and clarify primary logic selection.

#### Scenario: Supply-demand differs from penetration
- **WHEN** the first changed variable is adoption share
- **THEN** `penetration` is the primary logic
- **WHEN** the first changed variable is scarcity, price, inventory, lead time, or capacity tightness
- **THEN** `supply_demand` is the primary logic

#### Scenario: Substitution differs from route shift
- **WHEN** the function and architecture stay broadly the same while supplier or country changes
- **THEN** `substitution` is the primary logic
- **WHEN** architecture, BOM, standard, or route changes
- **THEN** `technology_route_shift` is the primary logic

#### Scenario: Reform differs from constraint shock
- **WHEN** policy releases access, pricing, payment, governance, or market mechanisms
- **THEN** `policy_market_reform` is the primary logic
- **WHEN** policy imposes a binding restriction, scarcity, ban, quota, or compliance shock
- **THEN** `policy_constraint_shock` is the primary logic

#### Scenario: Order cycle differs from supply-demand
- **WHEN** a signal is about committed spend, project timing, equipment orders, or supplier backlog from investment
- **THEN** `investment_order_cycle` is the primary logic
- **WHEN** a signal is about current shortage, pricing, inventory, lead time, or capacity tightness
- **THEN** `supply_demand` is the primary logic

### Requirement: Taxonomy Precedes Chokepoint Map Lookup
The taxonomy SHALL be conceptually upstream of chokepoint-map lookup. The taxonomy explains why a signal matters and which reasoning template to use; the chokepoint map helps locate where value may concentrate and which pure targets may exist.

#### Scenario: News is reasoned before target mapping
- **WHEN** a news item is evaluated
- **THEN** the intended flow is facts -> logic type -> upward validation -> transmission chain -> downstream decomposition -> chokepoint-map consultation -> target mapping or no target

#### Scenario: Chokepoint map is not a stock-output shortcut
- **WHEN** a signal matches a chokepoint-map trigger
- **THEN** the taxonomy still requires reasoning about the signal's investment logic before any target is treated as relevant

#### Scenario: Chokepoint remains structural
- **WHEN** the taxonomy is reviewed
- **THEN** `chokepoint` is treated as a downstream structural property rather than an investment logic type

### Requirement: Runtime Behavior Remains Unchanged
This change SHALL NOT modify capture, triage, analysis, target generation, digest, market data, scheduling, chokepoint-map data, prompts, schemas, persisted data, or runtime behavior.

#### Scenario: Taxonomy artifacts do not change code paths
- **WHEN** this change is applied
- **THEN** no runtime code, prompt, schema, persisted data, scheduled job, or chokepoint-map data is changed

### Requirement: Future Application Preserves Free-Form Thesis Reasoning
The taxonomy SHALL be designed as a future reasoning audit or metadata layer. Future application MUST NOT replace the free-form thesis body with a rigid table or force all thesis prose into fixed fields.

#### Scenario: Taxonomy guides reasoning without replacing prose
- **WHEN** a future change applies the taxonomy to analysis
- **THEN** it may add structured reasoning metadata
- **AND** it must preserve free-form thesis body generation and existing adversarial review boundaries

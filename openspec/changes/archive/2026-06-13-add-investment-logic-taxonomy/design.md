## Context

The system now has two important but different pieces:

- Daily signal processing: capture, triage, analysis, target generation, and digest.
- Chokepoint map: a growing memory of structural nodes, triggers, caveats, and currently pure A-share exposures.

The user clarified that the real objective is not "hit a graph and output stocks." The objective is a reusable investment reasoning skill:

1. read a news item;
2. decide whether it contains a valuable investment logic;
3. verify the logic upward against higher-level demand, policy, technology, or business-model context;
4. decompose downward into the chain where profit, scarcity, or bargaining power concentrates;
5. use the chokepoint map as memory, not as a substitute for reasoning;
6. map only sufficiently pure targets, with caveats and falsification.

This change establishes the taxonomy layer only. It deliberately does not connect the taxonomy to runtime prompts, schemas, storage, digest rendering, or map schema yet.

## Goals / Non-Goals

**Goals:**

- Define canonical investment logic types.
- Define the operating rule for one primary logic type plus optional secondary logic types.
- For each type, define:
  - what signals usually look like;
  - when the type should be primary, secondary, or rejected;
  - upward validation questions;
  - transmission-chain questions;
  - downstream decomposition questions;
  - common target-search pattern;
  - minimum evidence threshold;
  - common falsification points;
  - public-facing caveat guidance.
- Define how taxonomy relates to the chokepoint map.
- Keep the output reviewed and stable enough for later prompt/schema changes.

**Non-Goals:**

- Do not change live analysis prompts.
- Do not change `thesis-contract`, `target-contract`, or `chokepoint_map.json`.
- Do not change LLM provider schemas.
- Do not alter daily pipeline behavior, triage, target generation, digest, scheduling, or market data.
- Do not expand the universe or add new chokepoint nodes.

## Core Definition

An investment logic is not a stock pool and not a theme keyword. It is the causal path by which a news fact could change future cash flow, profit pools, competitive structure, or asset valuation.

The taxonomy should help the system ask:

```text
news fact
  -> what economic variable changed?
  -> is the premise true when validated upward?
  -> how does it transmit through the chain?
  -> where does scarcity, profit, or bargaining power concentrate?
  -> is there a pure target, or should the answer be no target?
  -> what evidence would falsify the logic?
```

The taxonomy is therefore a reasoning skill. It must not become a mechanical classifier that turns a keyword hit into a target.

## Decisions

### D1. Taxonomy is upstream of graph lookup

The reasoning order should be:

```text
news
  -> extract facts
  -> classify investment logic type(s)
  -> run type-specific upward validation
  -> run type-specific transmission-chain checks
  -> run type-specific downstream decomposition
  -> consult chokepoint map as memory
  -> map pure targets or return no target
  -> adversarial falsification
```

This prevents a mechanical flow where news triggers graph keywords and immediately emits stocks. The graph answers "where could value concentrate"; taxonomy answers "why would this news matter and how should we reason about it."

### D2. Future runtime uses one primary logic plus optional secondary logic

A single signal can have multiple logic types, but future runtime classification should select exactly one `primary_logic_type` and zero or more `secondary_logic_types`.

- Primary logic type: the first causal entrance through which the news changes economic value.
- Secondary logic type: a transmission mechanism, accompanying mechanism, or later-stage implication.

Examples:

- HBM capacity sold out:
  - primary: `supply_demand`
  - secondary: `margin_spread_repricing`, `investment_order_cycle`
- GPU export restriction:
  - primary: `policy_constraint_shock`
  - secondary: `substitution`, possibly `supply_demand`
- Liquid cooling adoption:
  - primary: `penetration` or `technology_route_shift`, depending on whether the news is about adoption rate or architecture change
  - secondary: `optimization`

This avoids weak "everything applies" reasoning while preserving secondary context.

### D3. Chokepoint is a downstream structural property

`chokepoint` should not be an investment logic type. A chokepoint is a structural property discovered during downstream decomposition:

- Is the layer monopolistic, oligopolistic, or fragmented?
- Does capacity expand slowly?
- Does a supplier control certification, yield, IP, equipment, material, or customer qualification?
- Does profit stay at this node or pass through to another layer?

The same chokepoint node can be reached by different logic types. For example, optical modules may be reached through `supply_demand`, `investment_order_cycle`, `technology_route_shift`, or `penetration`.

### D4. Canonical initial types

The initial taxonomy contains fourteen narrative-level types:

1. `supply_demand` - demand/shortage/capacity/inventory/pricing scarcity.
2. `substitution` - domestic/import/vendor/product replacement.
3. `optimization` - cost, efficiency, yield, power, performance, or productivity improvement.
4. `policy_market_reform` - pricing, marketization, payment, access, governance, or resource-allocation reform.
5. `penetration` - adoption, attach-rate, standardization, or deployment-rate inflection.
6. `margin_spread_repricing` - ASP, input cost, gross margin, spread, inventory, or contract repricing.
7. `technology_route_shift` - migration from one technical route, architecture, BOM, or standard to another.
8. `policy_constraint_shock` - bans, export controls, energy limits, environmental caps, antitrust, or safety constraints.
9. `business_model_shift` - monetization, subscription, take-rate, platform, usage-based pricing, or revenue-quality change.
10. `investment_order_cycle` - capex, plant buildout, data-center investment, equipment ordering, or capacity expansion.
11. `competitive_structure` - industry consolidation, capacity exit, share shift, pricing discipline, or leader bargaining-power improvement.
12. `market_access_expansion` - new customer, channel, region, qualification, certification, ecosystem slot, or addressable-market opening.
13. `asset_capital_revaluation` - resource, license, land, data, IP, infrastructure asset, restructuring, buyback, dividend, or capital-structure revaluation.
14. `fundamental_delivery_inflection` - orders, earnings, utilization, yield, cash flow, guidance, or old-thesis verification inflection.

The optional future type `valuation_liquidity_repricing` can be added later if the system starts handling rate, index, liquidity, and risk-appetite signals. It is deferred because the current system is focused on industrial and company-level news.

### D5. Each type has a transmission-chain template

Every logic type uses the same template shape:

- `signal_patterns`: facts that can trigger the type. These must be facts, not theme words.
- `primary_when`: when this type is the first causal entrance.
- `secondary_when`: when this type is a downstream or accompanying mechanism.
- `not_this_when`: boundary against neighboring logic types.
- `premise_to_validate`: the core investment premise that must be tested.
- `upward_validation`: higher-level questions that validate demand, policy, technology, or business context.
- `transmission_chain`: how the upper premise travels through units, prices, orders, capacity, share, margins, or regulation.
- `downstream_decomposition`: where profit pools, bottlenecks, losers, and pass-through layers sit.
- `chokepoint_mapping`: how to use the chokepoint map as memory without treating it as proof.
- `target_search`: what kind of pure exposure to seek, and when to return no target.
- `minimum_evidence_threshold`: the minimum evidence needed before the logic can be treated as more than weak.
- `falsification`: facts that would weaken or disprove the logic.
- `reject_if`: cases that should be treated as generic news or noise.
- `uncertainty_tags`: missing-evidence tags to carry forward.
- `public_caveat`: phrasing guidance for public digest output.

The template should constrain validation and falsification questions. It must not force the thesis body into a fixed table, because `thesis-contract` preserves free-form reasoning.

### D6. Fail-closed evidence policy

The taxonomy should bias toward false negatives over false positives. If evidence is too weak, the correct output is weak/no logic, not a forced target search.

Future runtime should classify evidence as:

- `accepted`: enough hard evidence to proceed into deeper analysis.
- `weak`: plausible but missing material evidence; can be kept for watch/research but should not drive target generation alone.
- `rejected`: generic news, marketing, theme language, or missing transmission.

At minimum, accepted logic should identify:

- a concrete news fact;
- a measurable or observable delta;
- a time window or adoption stage;
- an economic transmission path;
- the missing or disconfirming evidence.

## Universal Reasoning Skeleton

The HBM/Micron-style example generalizes to this rule:

```text
scarcity or change signal
  -> terminal demand / policy / technology / business premise validation
  -> unit-consumption, adoption, price, order, capacity, or margin transmission
  -> supply bottleneck / profit-pool / competitive-structure location
  -> pure target filter
  -> falsification conditions
```

For example, "memory capacity sold out next year" does not directly imply "buy memory-related stocks." The system must ask:

- Why is memory demand high?
- Is AI the source of demand, and can that be verified through GPU/ASIC shipment, cloud capex, HBM content per accelerator, or customer guidance?
- Which memory layer is constrained: HBM capacity, advanced packaging, TSV, testing, materials, equipment, or yield?
- Where does margin stay?
- Is there a sufficiently pure A-share exposure?
- What would disprove it: AI capex cut, GPU shipment delay, HBM capacity release, price reversal, or order cancellation?

## Logic Type Registry

### `supply_demand`

- Signal patterns: sold out, shortage, price hike, lead time extension, backlog, utilization, capacity allocation, inventory drawdown.
- Primary when: the news first changes expected volume, scarcity, pricing, or inventory balance.
- Secondary when: shortage is a consequence of another primary driver such as policy constraint, penetration, or investment cycle.
- Not this when: the news is mainly about adoption rate (`penetration`) or customer access (`market_access_expansion`) without evidence of tight supply/demand balance.
- Premise to validate: a supply/demand imbalance is real, material, and likely to persist long enough to affect economics.
- Upward validation: terminal demand, capex, shipment, attach-rate, utilization, pricing, inventory, or customer guidance.
- Transmission chain: demand increment -> unit usage -> constrained capacity/yield/certification -> pricing/margin/order leverage.
- Downstream decomposition: fixed supply, slow expansion, pricing power, inventory leverage, downstream squeeze.
- Chokepoint mapping: use map nodes to locate constrained upstream inputs, equipment, materials, capacity owners, and certified suppliers.
- Target search: pure capacity holder, scarce upstream input, high-margin bottleneck equipment/material, not broad downstream assemblers.
- Minimum evidence threshold: at least one hard signal such as quantity, price, lead time, backlog, utilization, inventory, order, or customer guidance.
- Falsification: rapid capacity release, order cancellation, price reversal, inventory rebuild, end-demand cut.
- Reject if: vague "demand is strong" without quantity, time window, price, backlog, or corroboration.
- Uncertainty tags: single-source, no-quantity, restocking-risk, capacity-release-risk.
- Public caveat: phrase as "current evidence supports watching the supply-demand balance" rather than "shortage guarantees upside."

### `substitution`

- Signal patterns: domestic replacement, import substitution, supplier switch, customer qualification, certification, design win, export-control workaround.
- Primary when: the first causal change is a shift from one supplier, country, product, or route to another while the function remains broadly the same.
- Secondary when: substitution follows a policy constraint, route shift, or cost optimization.
- Not this when: the old architecture/BOM/standard itself is being replaced; that is `technology_route_shift`.
- Premise to validate: the substitute can technically, commercially, and operationally replace the incumbent.
- Upward validation: incumbent constraint, cost gap, customer security requirement, certification, design win, real supplier switch.
- Transmission chain: incumbent weakness -> qualification -> volume shift -> share gain -> margin/order leverage.
- Downstream decomposition: replaceable product level, certification gate, customer adoption stage, remaining incumbent-controlled layers.
- Chokepoint mapping: map substitute nodes and the parts of the stack where domestic or alternate supply is genuinely narrow.
- Target search: pure substitute with verified customer adoption and product-level exposure.
- Minimum evidence threshold: identify incumbent, substitute, product/step, and adoption evidence.
- Falsification: incumbent regains access, cuts price, substitute fails qualification, customer adoption stalls.
- Reject if: only slogans such as domestic substitution with no product, customer, qualification, or switching evidence.
- Uncertainty tags: qualification-missing, customer-missing, volume-timing-unclear.
- Public caveat: state that substitution is conditional on verified adoption, not policy intent alone.

### `optimization`

- Signal patterns: cost reduction, power reduction, yield improvement, efficiency gain, throughput improvement, PUE improvement, productivity improvement.
- Primary when: the economic value comes from better unit economics, not from a new route or adoption inflection.
- Secondary when: optimization helps explain why a technology route or penetration event can occur.
- Not this when: the change creates a new architecture, standard, or BOM; that is `technology_route_shift`.
- Premise to validate: the optimization solves a hard buyer constraint and is large enough to change purchasing behavior or margins.
- Upward validation: buyer pain point, measurable improvement, adoption incentive, switching cost, implementation complexity.
- Transmission chain: metric improvement -> buyer ROI -> adoption -> supplier order/margin or customer cost advantage.
- Downstream decomposition: who owns the enabling tool/component/material, who captures savings, who gets price-down pressure.
- Chokepoint mapping: use map nodes to identify enabling components or systems with scarce capability.
- Target search: supplier enabling measurable cost/power/yield improvement with adoption leverage.
- Minimum evidence threshold: a quantified metric or credible customer adoption path.
- Falsification: savings too small, implementation too hard, adoption slower than expected, customer captures all economics.
- Reject if: marketing-only efficiency claims with no metric or adoption path.
- Uncertainty tags: metric-missing, adoption-path-missing, customer-pass-through-risk.
- Public caveat: describe it as an efficiency hypothesis requiring adoption proof.

### `policy_market_reform`

- Signal patterns: pricing reform, marketization, payment reform, fiscal reform, grid reform, access reform, governance reform.
- Primary when: policy changes the rules of pricing, access, payment, asset use, or profit allocation.
- Secondary when: reform amplifies another industrial logic but is not the first causal entrance.
- Not this when: policy mainly restricts activity or imposes scarcity; that is `policy_constraint_shock`.
- Premise to validate: the reform changes cash-flow distribution or return on capital, not just sentiment.
- Upward validation: executable rule, responsible body, timing, affected entities, pricing/cost/access mechanism.
- Transmission chain: rule change -> price/access/cost/competition change -> financial statement impact.
- Downstream decomposition: beneficiaries previously constrained, losers losing subsidies/protection/margin, competition response.
- Chokepoint mapping: use map nodes only after reform identifies a real economic beneficiary layer.
- Target search: directly constrained beneficiary with measurable economics.
- Minimum evidence threshold: mechanism, affected party, implementation path, and economic transmission.
- Falsification: policy delay, weak enforcement, benefits competed away, implementation diluted.
- Reject if: high-level policy wording without mechanism or beneficiary economics.
- Uncertainty tags: implementation-risk, mechanism-unclear, beneficiary-economics-missing.
- Public caveat: frame as a policy-transmission watch item, not a policy headline trade.

### `penetration`

- Signal patterns: attach-rate increase, adoption, standardization, from optional to required, deployment inflection, penetration-rate acceleration.
- Primary when: the core change is a larger share of an addressable base adopting a product, component, or standard.
- Secondary when: penetration follows from optimization, regulation, access expansion, or route shift.
- Not this when: the news is mainly about supply tightness at current adoption; that is `supply_demand`.
- Premise to validate: adoption is crossing a real threshold with a clear trigger and ceiling.
- Upward validation: current penetration, ceiling, trigger, pace, cost threshold, regulation, customer requirement.
- Transmission chain: penetration percentage -> units -> content per unit -> supplier volume/margin.
- Downstream decomposition: component value per adoption, standard setter, module supplier, price erosion risk.
- Chokepoint mapping: identify nodes with content per adoption and supply constraints.
- Target search: pure unit-volume beneficiary with high content per adoption.
- Minimum evidence threshold: base rate, trigger, adoption evidence, and time window.
- Falsification: adoption stalls, value per unit collapses, alternative standard wins.
- Reject if: "penetration will improve" without base rate, trigger, or adoption evidence.
- Uncertainty tags: base-rate-missing, trigger-unclear, value-per-unit-risk.
- Public caveat: state adoption assumptions and what would show they are wrong.

### `margin_spread_repricing`

- Signal patterns: ASP increase, price hike, cost decline, margin improvement, input-cost repricing, contract repricing, inventory gain/loss.
- Primary when: the news directly changes price, cost, gross margin, spread, or inventory economics.
- Secondary when: repricing is the financial transmission of supply/demand, policy, or competition.
- Not this when: the core change is tight demand or capacity rather than margin capture; primary should be `supply_demand`.
- Premise to validate: the company can retain spread or margin, not pass it through to customers or suppliers.
- Upward validation: durability, pricing power, cost pass-through, inventory position, contract lag, competitive behavior.
- Transmission chain: price/cost delta -> retained spread -> gross margin/cash flow -> operating leverage.
- Downstream decomposition: spread keepers, squeezed layers, inventory holders, lagged contract beneficiaries.
- Chokepoint mapping: use chokepoint status to test whether pricing power is credible.
- Target search: direct spread beneficiary, inventory holder, high operating leverage producer.
- Minimum evidence threshold: quantified price/cost move and credible retention mechanism.
- Falsification: price reversal, cost rebound, benefit competed away, customer price-down.
- Reject if: price move is small, one-off, or not linked to retained margins.
- Uncertainty tags: retention-risk, inventory-unknown, contract-lag-unknown.
- Public caveat: describe margin spread as conditional on retention and duration.

### `technology_route_shift`

- Signal patterns: route migration, architecture shift, new standard, BOM change, design migration, ecosystem transition.
- Primary when: the economic value comes from an old route losing and a new route gaining content, economics, or ecosystem control.
- Secondary when: route shift is an enabler of penetration, optimization, or substitution.
- Not this when: function remains the same and only supplier/country changes; that is `substitution`.
- Premise to validate: the new route solves a real physical/economic/ecosystem bottleneck and has adoption support.
- Upward validation: old-route limitation, new-route maturity, customer adoption, standard, ecosystem, switching cost.
- Transmission chain: bottleneck in old route -> new route adoption -> BOM/content shift -> winners/losers.
- Downstream decomposition: old-route losers, new-route winners, bridge beneficiaries, bypass risk.
- Chokepoint mapping: map nodes by new-route required tools/materials/components, not broad theme exposure.
- Target search: pure supplier to the winning route or required tooling/material.
- Minimum evidence threshold: customer adoption, standard, or economic reason beyond a concept launch.
- Falsification: route adoption delayed, old route improves enough, standard fragments.
- Reject if: technical concept has no customer adoption, standard, or economic reason.
- Uncertainty tags: adoption-missing, standard-risk, bypass-risk.
- Public caveat: emphasize route-transition risk and potential temporary beneficiaries.

### `policy_constraint_shock`

- Signal patterns: export control, ban, quota, grid limit, energy cap, environmental restriction, antitrust, safety review.
- Primary when: a binding external constraint changes supply, demand, substitution, compliance cost, or scarcity.
- Secondary when: the constraint is one driver behind substitution or supply/demand.
- Not this when: policy mainly improves market mechanisms; that is `policy_market_reform`.
- Premise to validate: the constraint is binding, durable, and economically transmitted rather than just headline risk.
- Upward validation: constrained activity, affected party, scope, enforcement, duration, workaround cost.
- Transmission chain: constraint -> blocked party/scarcity/substitution/compliance infrastructure -> economics.
- Downstream decomposition: blocked suppliers, scarce capacity, substitute suppliers, compliance/workaround providers, demand destruction.
- Chokepoint mapping: locate substitute or constrained nodes only after deciding whether demand shifts or disappears.
- Target search: substitute supplier, constrained-capacity owner, compliance infrastructure provider.
- Minimum evidence threshold: object, scope, enforcement mechanism, and likely economic direction.
- Falsification: rule relaxed, workaround commoditized, demand destroyed rather than shifted.
- Reject if: regulatory headline lacks binding mechanism or economic transmission.
- Uncertainty tags: enforcement-risk, demand-destruction-risk, workaround-risk.
- Public caveat: state whether the constraint shifts demand or may simply destroy demand.

### `business_model_shift`

- Signal patterns: subscription, monetization, take-rate increase, platform fee, SaaS conversion, usage-based pricing, revenue-recognition change.
- Primary when: the value change comes from how the company monetizes or retains customers.
- Secondary when: monetization is a consequence of market access or penetration.
- Not this when: the change is merely an accounting timing issue with no economics.
- Premise to validate: the model improves revenue quality, margin, retention, or valuation framework.
- Upward validation: willingness to pay, retention, conversion, customer ROI, competition, churn.
- Transmission chain: model change -> ARPU/take-rate/retention/gross margin -> cash-flow quality.
- Downstream decomposition: who pays, who loses channel economics, who captures incremental monetization.
- Chokepoint mapping: usually secondary; use map only if model shift depends on a scarce platform or data asset.
- Target search: platform or software/service company with pricing power and retention.
- Minimum evidence threshold: adoption/conversion/retention or credible customer willingness-to-pay evidence.
- Falsification: churn rises, conversion lower than expected, competition caps pricing.
- Reject if: pricing announcement has no adoption or retention evidence.
- Uncertainty tags: retention-risk, conversion-missing, pricing-power-risk.
- Public caveat: frame as monetization quality under observation.

### `investment_order_cycle`

- Signal patterns: capex guidance, plant buildout, data-center investment, equipment order, fab expansion, infrastructure spending.
- Primary when: committed investment or ordering changes supplier revenue timing and scale.
- Secondary when: capex follows demand, penetration, or policy.
- Not this when: the main fact is current shortage/pricing rather than new spend; primary should be `supply_demand`.
- Premise to validate: investment is committed, funded, timed, and linked to identifiable supplier layers.
- Upward validation: spender, reason, funding, approval, time table, demand backing, structural vs cyclical catch-up.
- Transmission chain: budget -> design -> equipment/material/construction/order -> backlog -> revenue.
- Downstream decomposition: first money-flow layer, order leverage, capacity/certification constraints, later-cycle layers.
- Chokepoint mapping: use map to identify bottleneck suppliers receiving earliest orders.
- Target search: equipment/material supplier, infrastructure bottleneck, service provider with order leverage.
- Minimum evidence threshold: funding/time table/order/supplier linkage, not just a long-term vision.
- Falsification: capex cut, project delay, supplier share loss, overcapacity.
- Reject if: capex number is a vague plan with no timing, funding, or supplier linkage.
- Uncertainty tags: funding-risk, timing-risk, supplier-linkage-missing.
- Public caveat: distinguish committed order cycle from aspirational capex.

### `competitive_structure`

- Signal patterns: industry exit, consolidation, capacity discipline, share shift, price discipline, competitor distress, leader bargaining power.
- Primary when: economics improve because competition changes, not because end demand alone changes.
- Secondary when: structure improvement amplifies supply/demand or margin repricing.
- Not this when: the news only shows demand growth without competitor behavior or capacity discipline.
- Premise to validate: competitive intensity is structurally improving and benefits can be retained.
- Upward validation: capacity exit, competitor financial stress, market-share data, price discipline, customer concentration.
- Transmission chain: weaker competition -> share/pricing/mix improvement -> margin/cash-flow leverage.
- Downstream decomposition: leaders vs marginal players, customers with bargaining power, capacity additions that can break discipline.
- Chokepoint mapping: use map to test whether the node has enough concentration or switching cost.
- Target search: leader or disciplined capacity owner with measurable share/pricing gain.
- Minimum evidence threshold: competitor/market data showing structure change, not just management claims.
- Falsification: new entrants, capacity restart, price war, customer dual-sourcing.
- Reject if: only "industry improves" without evidence of exit, discipline, or share migration.
- Uncertainty tags: concentration-data-missing, price-war-risk, capacity-restart-risk.
- Public caveat: present as competition-structure watch, not simple demand optimism.

### `market_access_expansion`

- Signal patterns: new major customer, channel, region, certification, qualification, ecosystem slot, platform listing, procurement access.
- Primary when: the news opens a previously unavailable market, customer, channel, or qualification gate.
- Secondary when: access expansion follows substitution, route shift, or penetration.
- Not this when: the customer already existed and only orders increased; that may be `investment_order_cycle` or `supply_demand`.
- Premise to validate: access materially increases serviceable addressable market and can convert into revenue.
- Upward validation: customer scale, qualification stage, exclusivity, volume ramp, commercial terms, competitive position.
- Transmission chain: access gate -> order eligibility -> ramp -> revenue/margin -> repeatability.
- Downstream decomposition: direct supplier, upstream content providers, qualification bottleneck, channel economics.
- Chokepoint mapping: map nodes to identify pure providers with newly unlocked access.
- Target search: company with high exposure to the new customer/channel/region and proven delivery capability.
- Minimum evidence threshold: named access gate plus credible ramp path or customer qualification evidence.
- Falsification: qualification not converted, ramp delayed, customer dual-sources away, low margin.
- Reject if: partnership/announcement lacks order eligibility, qualification, or commercial path.
- Uncertainty tags: ramp-risk, customer-concentration-risk, commercial-terms-missing.
- Public caveat: state that access is not the same as revenue until ramp evidence appears.

### `asset_capital_revaluation`

- Signal patterns: resource reserve, license, land, data, IP, infrastructure asset, spin-off, merger, buyback, dividend, capital structure, asset injection.
- Primary when: value changes through asset recognition, capital allocation, balance-sheet structure, or revaluation rather than operating chain transmission.
- Secondary when: asset revaluation supports reform, competition, or business-model change.
- Not this when: the main fact is operating orders, pricing, or demand.
- Premise to validate: the asset/capital event changes realizable value per share or future cash-flow distribution.
- Upward validation: asset ownership, legal clarity, valuation benchmark, monetization path, capital allocation policy.
- Transmission chain: asset/capital event -> per-share value/cash return/financing cost/control change -> valuation.
- Downstream decomposition: who owns the asset, who controls monetization, who bears liabilities or dilution.
- Chokepoint mapping: usually not the primary tool unless the asset itself is a scarce structural node.
- Target search: direct asset owner or capital-return beneficiary with clear governance.
- Minimum evidence threshold: verifiable asset/capital event and monetization or shareholder-return path.
- Falsification: asset not monetizable, governance blocks value, dilution, liability emerges.
- Reject if: asset story lacks ownership, monetization, or capital-allocation evidence.
- Uncertainty tags: governance-risk, valuation-benchmark-missing, monetization-risk.
- Public caveat: present as asset/capital revaluation hypothesis, not operating improvement.

### `fundamental_delivery_inflection`

- Signal patterns: orders, earnings beat, utilization, yield, cash flow, guidance upgrade, backlog conversion, production ramp, old thesis verification.
- Primary when: the news is not a new narrative but evidence that a prior thesis is now delivering.
- Secondary when: delivery validates supply/demand, penetration, substitution, or investment cycle.
- Not this when: the news only announces a future plan without current delivery evidence.
- Premise to validate: financial or operating delivery is inflecting in a material and repeatable way.
- Upward validation: orders, revenue, margin, utilization, yield, cash flow, guidance quality, one-off adjustments.
- Transmission chain: delivery data -> confidence in thesis -> earnings/cash-flow revision -> valuation support.
- Downstream decomposition: which business segment delivered, sustainability, mix, margin, working capital, customer concentration.
- Chokepoint mapping: use map to check whether delivery comes from a structural node or broad exposure.
- Target search: company with direct delivery data tied to a previously reasoned thesis.
- Minimum evidence threshold: concrete operating or financial metric and a comparable baseline.
- Falsification: one-off gain, backlog not converted, margin quality weak, cash flow divergence.
- Reject if: headline beat lacks segment evidence, quality, or repeatability.
- Uncertainty tags: one-off-risk, segment-mix-unknown, cash-flow-quality-risk.
- Public caveat: frame as thesis verification, with quality and repeatability caveats.

## Boundary Rules

The key boundary rules are:

- `supply_demand` vs `penetration`: if the first changed variable is adoption share, primary is `penetration`; if the first changed variable is scarcity, price, inventory, or lead time, primary is `supply_demand`.
- `supply_demand` vs `margin_spread_repricing`: if the news is about shortage/tightness, repricing is secondary; if the news is directly about retained margin/spread, repricing can be primary.
- `substitution` vs `technology_route_shift`: if function and architecture stay broadly the same and supplier/country changes, primary is `substitution`; if architecture/BOM/standard changes, primary is `technology_route_shift`.
- `policy_market_reform` vs `policy_constraint_shock`: if policy releases mechanism/access/pricing, primary is reform; if policy imposes binding scarcity or restriction, primary is constraint shock.
- `optimization` vs `technology_route_shift`: if the change improves unit economics within the same route, primary is optimization; if it changes route/architecture/standard, primary is route shift.
- `investment_order_cycle` vs `supply_demand`: if the news is current scarcity/pricing, primary is supply/demand; if it is committed spend/order flow in response to a premise, primary is investment/order cycle.
- `market_access_expansion` vs `substitution`: if the main fact is entering a new customer/channel/qualification gate, primary is access expansion; if it is replacing an incumbent supplier, primary is substitution.
- `competitive_structure` vs `supply_demand`: if improvement comes from reduced competition or pricing discipline, primary is competitive structure; if it comes from end-demand tightness, primary is supply/demand.

## Future Runtime Shape

This change does not implement runtime fields, but the likely future structured fragment is:

```json
{
  "primary_logic_type": "supply_demand",
  "secondary_logic_types": ["margin_spread_repricing"],
  "evidence_status": "accepted|weak|rejected",
  "premise_to_validate": "...",
  "upward_validation": ["..."],
  "transmission_chain": ["..."],
  "downstream_decomposition": ["..."],
  "chokepoint_candidates": ["..."],
  "missing_evidence": ["..."],
  "disconfirming_evidence": ["..."],
  "public_caveat": "..."
}
```

This fragment should be added in a later change, most likely as optional thesis metadata or a reasoning-audit object. It should not replace the free-form thesis body.

## Risks / Trade-offs

- [Taxonomy becomes too broad and labels everything] -> Future runtime must require one primary type, evidence status, and fail-closed rejection.
- [Taxonomy gets mistaken for graph nodes] -> Keep it narrative-level; industries and stocks stay in the chokepoint map.
- [Rigid templates suppress intuitive reasoning] -> Templates constrain validation questions, not thesis prose.
- [Taxonomy duplicates chokepoint map triggers] -> Taxonomy describes why the signal matters; map triggers describe where to look.
- [Digest overstates weak logic] -> Public output should carry caveats and maintain "personal research note / observation object" framing.

## Migration Plan

1. Review and approve taxonomy labels, operating rules, and templates.
2. Later change: `add-investment-reasoning-skill` adds a structured reasoning fragment using `primary_logic_type`, optional secondary types, evidence status, validation, decomposition, and falsification.
3. Later change: `apply-reasoning-skill-to-analysis` applies the taxonomy-aware reasoning fragment while preserving free-form thesis body.
4. Later change: `upgrade-chokepoint-map-for-reasoning` optionally adds `logic_types`, `validation_questions`, and `map_caveats` to curated nodes with schema-versioning.
5. Later change: `map-assisted-target-generation` passes confirmed thesis + reasoning audit + map candidates into target generation.
6. Later change: `digest-reasoning-chain-cards` renders logic-aware public cards while preserving non-recommendation language.

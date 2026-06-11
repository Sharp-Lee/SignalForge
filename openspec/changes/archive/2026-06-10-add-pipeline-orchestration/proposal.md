## Why

五层都建好了,但还是五个独立部件,没串成一条能跑的流水线。本 change 把 ① → ③ → ④ 组合成一条**端到端 pipeline**:采集 →(选信号)→ 分析 → 标的。跑一次,就能第一次看到一个信号走完 **信号 → 论点 → 标的 → 观察名单**。

它只是**组合既有各层**(`run_once` / `analyze` / `propose_targets`),不重造任何逻辑;各层契约校验仍权威。真 LLM/行情 provider 未来就从这条 pipeline 的注入点插进去。**保持 MVP**,不做三层调度、信号聚类、真 provider、⑤ 校准。

## What Changes

- 新增 `pipeline-orchestration` 能力:
  - **`run_pipeline(adapters, author, reviewer, proposer, price_lookup, store, ...) → PipelineResult`**:
    1. `run_once` 采集(① + ②triage 在 add_signal 里)→ 信号入库
    2. 选信号(**trivial 分组**:如取本轮新入库信号为一组;聚类/选择策略留后续)
    3. `analyze` → confirmed thesis
    4. `propose_targets` → 观察名单标的 / 空仓推荐
  - **逐阶段韧性**:某信号组 analyze 失败、或某标的生成失败,MUST 记录但 MUST NOT 拖垮整条 pipeline(沿用各层既有的错误隔离精神)。
  - **聚合结果**:采集计数、产出的 theses、观察名单标的、空仓推荐、各阶段错误,汇总进 `PipelineResult`。
  - 全程**复用既有层函数与既有 `ContractStore`**,不重造校验/编排。
- **本 change 不做**:三层调度(每日/事件/周级)、信号聚类/选择策略、真 LLM/行情 provider 接入、⑤ 校准 —— 都留后续 change(留 stub/注释边界)。

## Capabilities

### New Capabilities

- `pipeline-orchestration`:把 ① → ③ → ④ 组合成一条端到端可跑的 pipeline,含 trivial 信号选择、逐阶段韧性、聚合结果。是把五层串成一条流水线的编排入口。

### Modified Capabilities

（无。）

## Impact

- **第一次能端到端跑通** 信号 → 论点 → 标的 → 观察名单(用桩),看到整条链作为一个整体工作。
- 真 LLM、真行情、调度策略的**插入点就在这条 pipeline 上**,后续替换桩即可。
- 全程组合既有层,signal/thesis/target 各层契约校验仍权威,不被绕过。
- 三层调度、信号聚类、真 provider、⑤ 校准留作后续 change。

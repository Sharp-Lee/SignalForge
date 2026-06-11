## Why

整条 pipeline 已端到端跑通,但 ③分析 和 ④标的 还在用桩——不会真思考。两个边界早就留好(`LlmReasoner.reason` / `LlmTargetProposer.propose` 都是 `NotImplementedError`)。本 change 把**真实 Claude** 接进这两个边界,让系统第一次对真实信号产出真实论点和观察名单。

**governing fact(决定一切):** `validate_thesis` / `validate_target` 只校验**形状 + confirmed 门槛**,**不检查** 模型给的 `source_signal_ids` 是否真在输入信号里、`symbol` 是否真实证券。所以 schema 校验**必要但不充分**。provider 层必须自己承担**溯源/指称检查**,把幻觉变成**拒绝**(`raise`)而非静默坏数据。所有失败 `raise LlmProviderError`,被 `pipeline_orchestration` 既有的 per-stage `try/except` 记成 `PipelineError`——绝不落库伪造数据。pipeline / news_contracts / 各层 Stub 都不动。

## What Changes

- 新增能力 `llm-provider`:
  - **可注入 transport seam**:`Completion` Protocol + `AnthropicCompletion`(默认实现,**lazy client**——无 key/无网络时构造/导入不碰网络)+ `LlmProviderError`,放 `llm_provider/transport.py`。网络/SDK 调用**只在这一处**。
  - **真实 `LlmReasoner`**(替换 `analysis_orchestration/core.py` 的 NotImplementedError):带 `identity` + `system_prompt` + 注入 `transport`;四角色派发(free_generation / completeness_critique / adversarial_falsification)、各角色 prompt 渲染、生成 schema、`_enforce_provenance`、`_enforce_role_floors`。保留既有 `reason(role, context)->dict` 签名。
  - **真实 `LlmTargetProposer`**(替换 `target_generation/core.py` 的 NotImplementedError):带 `system_prompt` + 注入 `transport` + 可选 `symbol_universe`;标的 prompt、候选 schema、`_enforce_symbol_universe`。保留 `propose(thesis)->list` 签名。
  - **结构化输出** = `output_config.format` JSON-schema 模式;模型 `claude-opus-4-8`;reasoning-heavy 角色开 adaptive thinking;SDK 默认 timeout/重试;每次调用记 usage。
  - **生成 schema 与契约 schema 故意分离**:LLM 只产**角色片段**(`track_record`/`review_session`/`status`/`state`/`priced_in`/`thesis_ids` 由编排合成,不让模型编);且契约 schema 结构上不能当输出 schema(无 `additionalProperties:false`,含被剥离的 `min*`/`max*` 约束)。被剥离的下限(`score<=100`、非空反驳/对冲/notes)由 provider 代码 + `store.add_*` 双重补回。
  - **离线测试**:桩 transport 跑真实 prompt 构造+解析+溯源+下限路径;失败模式测试;drift-guard 测试;key-safety/laziness 测试。**一个 env-gated live smoke test,默认跳过**。
- **provider 输出仍走既有 `ContractStore` 校验**(`store.add_thesis`/`add_target`),不绕过。

## Capabilities

### New Capabilities

- `llm-provider`:可注入 transport seam + 真实 Claude 接入两个既有 reasoner/proposer 边界 + 溯源/指称/下限强制(把幻觉变拒绝)+ 结构化输出。是 ③④ 从"桩"到"真思考"的关键层。

### Modified Capabilities

（无。两个边界类原属 analysis-orchestration / target-generation,但其 LLM 行为是独立的新能力;既有 spec 的 requirement 不改。）

## Impact

- **③④ 第一次真思考**:系统对真实信号产出真实论点和观察名单。
- **幻觉被挡在边界**:模型编造 `source_signal_ids` / 不存在的 `symbol` / 越界下限 → `raise LlmProviderError` → 记为 stage error,不落库。
- 真实 provider 的**唯一注入点**已定(`Completion` seam),后续换模型/换 provider 只换这一处。
- 作者↔评审独立 = 不同 instance + 不同 persona + **不同 system prompt**(结构性,非靠提示);坦白:同底层模型下字符级独立 ≠ 统计独立,真多 provider 独立留后续。
- **不做**:streaming、prompt-cache 优化、batching、重试调优、信号聚类、⑤校准、真多 provider 独立、Pydantic/`messages.parse`、strict tool-use(留作 fallback 文档)。

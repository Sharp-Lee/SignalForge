## Why

输入腿通了,信号能流进记忆底座,但系统还没有"大脑" —— 没有任何东西把信号变成论点。③ 分析层是系统真正出 alpha 的地方:把信号经"自由生成 → 完整性批判 → 对抗证伪"编排成 confirmed thesis。

本 change 搭这层的**编排骨架**:LLM 调用放在可注入 seam 后面(和采集层的 transport 注入同一套路),测试用桩 reasoner 离线跑;**真实 LLM provider 接入留作后续**(和真实 fetcher 一样的节奏 —— 先骨架可测,再接真实)。**保持 MVP**,不碰 ④ 标的生成、⑤ 校准、信号聚类/选择策略。

契约早就定好了(thesis-contract 的自由生成、完整性批判 confirmed 门禁、对抗证伪独立性、track_record),③ 就是把它们**编排起来真正生产论点**,所有不变量仍由既有校验强制,编排层不重造。

## What Changes

- 新增 `analysis-orchestration` 能力:
  - **Reasoner 协议(可注入)**:给定角色 + 上下文返回推理结果。生产包真实 LLM,测试用桩 reasoner;LLM I/O MUST 可注入以便离线测试。
  - **三段式编排**:
    1. 自由生成(author 角色 → 自由 `body`,不强加推理模板)
    2. 完整性批判(产 `completeness_critique`:notes + 候选追加 thesis ids,且 `body_unchanged=True`,不改原 body)
    3. 对抗证伪(reviewer 角色,`reviewer_instance_id`/`reviewer_persona` MUST 区别于 author → 最强反方 + 至少一个对冲 + `review_session`)
  - **组装**:confirmed thesis 必带 `track_record`(方向 + 可证伪预期 + 验证窗)+ 置信/不确定标注;跨市场字段按需两步抽取(可简化,不强制)。
  - **持久化**:confirmed thesis 走既有 `ContractStore.add_thesis`,复用 thesis-contract 全部校验(独立性、完整性批判门禁、track_record、待核标记),MUST NOT 绕过。
  - author 与 reviewer 是**两个独立 reasoner 实例**,让对抗证伪独立性门禁能真正过(不是自导自演)。
- **本 change 不做**:真实 LLM provider 接入、信号聚类/选择策略、跨市场 transmission 的复杂抽取、④ 标的生成、⑤ 校准 —— 都留后续 change。

## Capabilities

### New Capabilities

- `analysis-orchestration`:③ 分析层的 Reasoner 协议、三段式编排(自由生成 → 完整性批判 → 对抗证伪)、confirmed thesis 的组装与持久化(复用 thesis-contract)。是信号 → 论点的实体编排层。

### Modified Capabilities

（无。）

## Impact

- 信号**首次**被编排成 confirmed thesis,打通"输入 → 分析"。
- LLM I/O 全部隔离,测试离线(桩 reasoner),不打真实 LLM、不依赖外网/密钥。
- thesis-contract 的所有不变量由既有校验强制(独立性 / 完整性批判 / track_record),编排层不重造。
- 真实 LLM provider 接入、信号选择、④ 标的生成、⑤ 校准留作后续 change(明确边界,留 stub/注释)。

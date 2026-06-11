## Why

③ 能产 confirmed thesis 了,但论点还不是你能直接看的"标的"。④ 标的生成是架构的**最后一层输出**:把 confirmed thesis 变成观察名单条目(logic/买点分离、状态机、催化剂、空仓出口),交人在环定夺。做完,整条 **信号 → 论点 → 标的 → 人在环名单** 的结构骨架就端到端齐了。

和 ③ 同套路:推理放可注入 seam 后,测试用桩;**真实 LLM provider、真实行情数据(算 priced_in)留作后续**。**保持 MVP**,不碰 ⑤ 校准、动态 Top-N 阈值。target-contract 的不变量(logic/买点分离、买点不利不得进买入区、催化剂+退出触发必填、必须链 confirmed thesis、空仓出口)早就定好了,④ 就是把它们编排起来真正生产名单,所有校验仍由既有 `ContractStore.add_target` 强制。

## What Changes

- 新增 `target-generation` 能力:
  - **TargetProposer 协议(可注入)**:confirmed thesis → 候选标的(`symbol` / `name` / `target_market` / `logic_score` / `buy_point` / `catalysts` / `exit_triggers`)。生产包真实 LLM,测试用桩;推理 I/O MUST 可注入以便离线测试。
  - **编排**:proposer 提议 → 装配进 `target-contract` → 链回 confirmed thesis → 设初始状态(`watch`)→ 走既有 `ContractStore.add_target`,复用 target-contract 全部校验,MUST NOT 绕过。
  - **priced_in**:`price_change_since_signal` 由**可注入价格查询**提供(真实行情源留后续);`buy_point` 状态为 proposer 判断。
  - **空仓出口**:无候选标的过 logic/买点/催化剂门槛时,产 `create_empty_recommendation`(带原因),MUST NOT 为产出而硬造名单。
- **本 change 不做**:真实 LLM provider 接入、真实行情数据源、动态 Top-N 阈值、⑤ 校准 —— 都留后续 change(留 stub/注释边界)。

## Capabilities

### New Capabilities

- `target-generation`:④ 标的层的 TargetProposer 协议、confirmed thesis → 观察名单条目的编排(复用 target-contract)、以及空仓出口。是论点 → 标的的实体编排层。

### Modified Capabilities

（无。）

## Impact

- confirmed thesis **首次**变成观察名单条目,打通"分析 → 标的 → 人在环输出"。
- 整条结构骨架(① → ② → ③ → ④ + ⑤ 接口)端到端齐,你第一次有一份(结构上)可审的名单。
- 推理与价格 I/O 全部隔离,测试离线(桩 proposer + 桩价格),不打真实 LLM/行情、不依赖外网/密钥。
- target-contract 所有不变量由既有校验强制(logic/买点分离、买点纪律、confirmed thesis 链接、空仓出口),编排层不重造。
- 真实 LLM provider、真实行情数据源、动态阈值、⑤ 校准留作后续 change。

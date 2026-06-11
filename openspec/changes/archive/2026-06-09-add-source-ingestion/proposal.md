## Why

三份契约已经锁定,但系统现在没有任何真实信号流入 —— `theses` 和 `targets` 全是空的。采集层(架构图的 ① + ①b)是让全球结构性信息真正进入流水线的第一道实体层。没有它,下游的分析、标的、反馈都无米下锅。

本 change 只搭采集层的**骨架与契约**,不碰下游 ②③④⑤ 的逻辑:一个统一的 Adapter 框架(每个源归一化成 `signal-contract`、增量、幂等、网络 I/O 可 mock),少量参考全球源 Adapter,以及反向进料(①b)骨架。**刻意保持 MVP**,加源 = 加一个 Adapter,符合契约则下游零改动;一次塞满所有源会重蹈上一个 change 19-delta 膨胀的覆辙。

## What Changes

- 新增 `source-ingestion` 能力:
  - **Adapter 协议**:`fetch(cursor) -> raw items`、`normalize(raw) -> signal-contract`,网络 I/O 必须隔离/可注入,使每个 Adapter 都能用 fixtures 离线测试。
  - **增量游标**:复用既有 `source_cursors` 表,每源只取 delta;重复运行幂等。
  - **写入路径**:Adapter 产出的 signal 必须过既有 `signal-contract` 校验 + 去重后才入 `signals` 表(复用 `ContractStore.add_signal`,不另起炉灶)。
  - **①b 反向进料骨架**:`market_move -> backtrace_news -> signal(signal_origin=market_move)` 的盘后扫描入口;市场异动数据源**可 stub / 注入**(实时行情源待定),但产出的 signal 必须带 `trigger_reason` 并过既有事件 hard gate。
- 实现 **2-3 个参考全球源 Adapter**(建议:通用 RSS/Atom、GDELT 全球事件;`last30days` adapter 已存在,纳入统一框架)。具体源由实现阶段定,但每个都必须满足上面的协议。
- 调度入口:一个能按源跑一轮采集的薄入口(为后续"每日/事件/周级"三层节奏留接口,本 change 不实现调度策略)。

## Capabilities

### New Capabilities

- `source-ingestion`:采集层的 Adapter 协议、增量游标语义、写入路径约束、参考 Adapter、以及 ①b 反向进料骨架。定义"信号如何合规地进入系统",是 ①/①b → ② 的实体入口。

### Modified Capabilities

（无 —— `signal-contract` 不改。采集层只是满足它,不修改契约本身。）

## Impact

- 让真实信号**首次**流入 SQLite 记忆底座,打通"输入"这条腿。
- 网络 I/O 全部隔离,测试用 fixtures,不打真实接口、不依赖外网。
- 加源可增量扩展:符合 Adapter 协议 + `signal-contract` 即可接入,下游不动。
- **本 change 不做**:三层调度策略(每日/事件/周级)、实时行情/反向进料的真实数据源、完整源覆盖、②③④⑤ 任何逻辑 —— 都留作后续 change。

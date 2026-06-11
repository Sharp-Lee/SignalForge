## ADDED Requirements

### Requirement: 信号出处完整性 (Provenance)

每条信号 MUST 携带来源标识、发布日期/时间戳、指向原文的链接、以及 `signal_origin`。缺失任一项的条目 MUST 被拒收,不得进入下游。这是"慢了就被定价"的前提:没有时间戳就无法判断新鲜度。

`signal_origin` MUST 为 `news` / `market_move` / `last30days_attention` 之一。`market_move` 表示来自反向进料/市场异动监控的信号,其流向是 `market_move -> backtrace_news -> signal`。该入口 MAY 触发事件级分析,但 MUST NOT 被解释为实时交易引擎。

结构完整性 MUST 由 `signal-contract` JSON Schema 校验;Python 校验器只负责 schema 难以表达的语义不变量(如近重复、轻量排除策略)。

#### Scenario: 缺失日期的条目被拒收
- **WHEN** 一个采集 Adapter 提交的信号没有发布日期或时间戳
- **THEN** 系统拒收该信号并记录拒收原因,不将其传给下游

#### Scenario: 完整出处的信号被接收
- **WHEN** 一个信号同时带有来源、日期、原文链接
- **THEN** 系统接收该信号并进入去重环节

#### Scenario: 市场异动信号被标记来源
- **WHEN** 反向进料模块从市场异动倒查到新闻并提交信号
- **THEN** 系统要求该信号带有 `signal_origin = market_move`

### Requirement: 近重复去重 (Deduplication)

系统 MUST 在近期有界窗口内对近重复信号去重(基于内容相似度,如 Jaccard 或 embedding)。当前实现用最近 500 条信号近似近期窗口;后续 MAY 在采集源时间语义稳定后升级为按 N 天滑动时间窗。重复项 MUST 被合并或丢弃,只保留一条规范记录。默认 Jaccard 阈值 MUST 为 `0.25`,并 MUST 做成可配置项;该默认值来自种子研究总结,尚未用真实样本校准。

#### Scenario: 重复报道被合并
- **WHEN** 多个来源在近期有界窗口内报道同一事件且内容相似度超过阈值
- **THEN** 系统将其合并为一条信号,并记录所有来源出处

### Requirement: 轻量类型标签 (Type Tag)

每条信号 MUST 被打上轻量类型标签(供需瓶颈 / 政策 / 天气气候 / 出口管制地缘 / 技术拐点 / 其他)。该标签仅用于路由与统计,MUST NOT 作为约束下游推理的硬规则。

#### Scenario: 信号被打类型标签用于路由
- **WHEN** 一条关于产能售罄的信号进入系统
- **THEN** 系统标记其类型为"供需瓶颈"并据此路由,但不据此预设结论

### Requirement: 轻量可交易性排除 (Lightweight Triage)

系统 MUST 用轻量规则对"明显不可交易"的信号做一次排除(对应研究总结的 5 大致命缺陷:时间模糊、内容模糊、影响模糊、高冗余、低信噪比),目的是控量(目标排除大多数噪音)。该排除 MUST 只用于降低体量,MUST NOT 作为推理约束强加给通过的信号。

轻量排除 MUST 策略化,当前默认策略标记为 `zh_cn_heuristic_v0`,且 MUST 可替换。`impact_vague` MUST 检测金额、百分比、数量、时间锚点、明确范围等可交易要素,不得只用"是否含数字"作为唯一判据。

#### Scenario: 明显模糊的新闻被排除
- **WHEN** 一条新闻只有"将出台有关文件"这类模糊措辞,无时间锚点、无量化、无明确范围
- **THEN** 系统将其排除并记录排除原因,不进入深度分析

#### Scenario: 排除策略被记录且可替换
- **WHEN** 系统用默认中文启发式排除一条信号
- **THEN** 系统记录 `triage.strategy = zh_cn_heuristic_v0`,并允许后续替换为其他语言或模型策略

#### Scenario: 通过排除的信号不带额外推理约束
- **WHEN** 一条信号通过了轻量排除
- **THEN** 系统将其原样传给分析环节,不附加任何"必须如何推理"的约束

### Requirement: 事件触发门禁 (Event Trigger Gate)

事件级深度分析 MUST 记录 `trigger_reason`,并 MUST 通过 hard gate:来源强、影响量化、跨市场传导清晰、或市场异动显著。系统 SHOULD 对事件触发使用预算/冷却机制,避免退化为追热点。

#### Scenario: 弱事件不得触发深度分析
- **WHEN** 一个信号没有强来源、量化影响、跨市场传导或显著异动
- **THEN** 系统不得将其标记为事件级深度分析触发器

#### Scenario: 强事件记录触发理由
- **WHEN** 一个市场异动信号满足事件 hard gate
- **THEN** 系统记录 `trigger_reason` 后才允许触发事件级分析

### Requirement: 原始载荷留存 (Raw Retention)

系统 MUST 在规范化前保留信号的原始载荷。当契约 schema 演进时,留存的原始数据 MUST 可被重新处理。

#### Scenario: schema 升级后可重跑
- **WHEN** `signal-contract` 的 schema 发生变更
- **THEN** 系统能基于留存的原始载荷重新规范化历史信号

# target-contract Specification

## Purpose
TBD - created by archiving change define-core-contracts. Update Purpose after archive.
## Requirements
### Requirement: 逻辑分与买点分强制分离 (Separation of Logic and Entry)

一个可投标的 MUST 把 `logic_score`(主题贴合度 / 生意质量)与 `buy_point`(估值 / 入场质量)作为**两个独立字段**,并 MUST 携带 `target_market` 承接上游 thesis 的跨市场推导结果。系统 MUST NOT 把二者合并成单一总分。当 `buy_point` 不利时,该标的 MUST NOT 被呈现为"现在买入"。这条直接防誉帆式错误:好公司被当成好买点。

结构完整性 MUST 由 `target-contract` JSON Schema 校验;Python 校验器只负责 schema 难以表达的语义不变量(如不得合并总分、买点不利不得进入买入区、必须链回 confirmed thesis)。

#### Scenario: 好公司贵价格不得标为现在买入
- **WHEN** 一个标的 `logic_score` 高但 `buy_point` 显示估值已透支
- **THEN** 系统将其呈现为"观察 / 等回调",而非"现在买入"

#### Scenario: 拒绝单一总分
- **WHEN** 创建一个可投标的
- **THEN** 系统要求分别给出 `logic_score` 与 `buy_point`,不接受单一合并评分

#### Scenario: 标的承接目标市场
- **WHEN** 一个标的由跨市场 thesis 推导生成
- **THEN** 系统要求该标的记录 `target_market`,并链回支撑它的 thesis

### Requirement: 观察名单状态机 (Watchlist State)

一个可投标的 MUST 携带观察名单状态(watch / review-required / buy-zone / hold / exit),并 MUST 至少绑定一个催化剂(日期或触发条件)与至少一个证伪 / 退出触发。这落实"知道了但不做,等触发再动"的纪律。

#### Scenario: 标的进观察名单需带催化剂与退出触发
- **WHEN** 一个标的被加入名单
- **THEN** 系统要求其至少包含一个催化剂与一个证伪/退出触发,否则不予保存

#### Scenario: 触发条件满足时改变状态
- **WHEN** 一个处于 watch 状态标的的催化剂条件被满足
- **THEN** 系统将其状态推进到 review-required(或保留 watch 并标记 `needs_review`),不得直接进入 buy-zone

### Requirement: 新鲜度与已定价 (Freshness / Priced-in)

一个可投标的 MUST 记录自其支撑信号以来标的的已涨幅,用于判断逻辑是否已被市场定价。

#### Scenario: 已大涨标的被标注已定价风险
- **WHEN** 一个标的自支撑信号发布以来已显著上涨
- **THEN** 系统标注"可能已被定价"并在呈现时提示该风险

### Requirement: 标的溯源 (Linkage to Thesis)

每个可投标的 MUST 链回支撑它的一条或多条论点(thesis)。无支撑论点的标的 MUST NOT 进入名单。

#### Scenario: 无支撑论点的标的被拒绝
- **WHEN** 一个标的没有任何已确认论点支撑
- **THEN** 系统拒绝将其加入观察名单

#### Scenario: 未确认论点不得支撑标的
- **WHEN** 一个标的只链回 draft 或 unconfirmed 论点
- **THEN** 系统拒绝将其加入观察名单

### Requirement: 空仓出口 (Empty Recommendation)

当没有标的满足逻辑、买点、催化剂、证伪与用户审阅门槛时,系统 MUST 允许输出"无推荐 + 原因",不得为了每日或每周产出而硬生成观察名单。

#### Scenario: 无够格机会时输出空推荐
- **WHEN** 本周没有任何标的通过门槛
- **THEN** 系统输出空推荐及原因,而不是生成低质量标的


# thesis-contract Specification

## Purpose
TBD - created by archiving change define-core-contracts. Update Purpose after archive.
## Requirements
### Requirement: 自由生成 (Free-form Generation)

一条论点(thesis)MAY 以自由叙事的形式生成。系统 MUST NOT 用固定字段模板去约束论点的**推理结构**或推导顺序。这是为了保护大模型的专家直觉与跨域顿悟 —— 把"怎么想"还给模型。

结构完整性 MUST 由 `thesis-contract` JSON Schema 校验;Python 校验器只负责 schema 难以表达的语义不变量(如对抗证伪独立性、confirmed 状态门禁、待核标记)。

#### Scenario: 自由叙事的论点被接受
- **WHEN** 模型以自由叙事给出一条跨域因果判断(如"厄尔尼诺内涝 → 城市排水管网")
- **THEN** 系统接受该论点的叙事形式,不因"未按固定字段填写"而拒绝它

#### Scenario: 系统不强加推理模板
- **WHEN** 创建一条新论点
- **THEN** 系统不要求模型先填写预设的推导字段序列

### Requirement: 完整性批判 (Completeness Critique)

分析层 MUST 在自由生成之后、对抗证伪之前执行一次完整性批判,用于追问"还有哪个二阶影响没想到"。完整性批判 MAY 产出候选追加 thesis,但 MUST NOT 强加固定推理模板,也 MUST NOT 修改原始自由 `body` 的推导顺序。

一条 thesis 在进入 confirmed 前 MUST 携带 `completeness_critique` 审计物,至少记录批判 note、候选追加 thesis ids,并确认原始 `body` 未被批判步骤改写。

#### Scenario: 完整性批判只产生候选追加论点
- **WHEN** 系统对一条自由论点执行完整性批判
- **THEN** 系统只记录候选追加 thesis 或 critique note,不要求原论点改写为固定字段模板

#### Scenario: 未经完整性批判不得确认
- **WHEN** 一条 thesis 缺少 `completeness_critique`
- **THEN** 系统不得将其标记为 confirmed

### Requirement: 可追溯 (Traceability)

一条论点中的每个实质性论断 MUST 能链回其来源信号(带日期)。无出处的实质性论断 MUST 被标记为待核。可追溯服务于审计与反馈,而非约束推理。

系统 MUST 使用两步溯源:第一步生成自由 `body`,第二步由独立 claim extractor 或人工审阅显式添加 `substantive_claims`。系统 MUST NOT 自动把整个 `body` 伪装成一条已溯源的实质性论断。只有显式添加且未带来源的子论断才进入待核列表。

#### Scenario: 无出处论断被标记
- **WHEN** 一条论点中包含一个没有任何来源信号支撑的实质性论断
- **THEN** 系统标记该论断为待核,并提示补充出处

#### Scenario: 自由 body 不自动变成已溯源论断
- **WHEN** 系统创建一条只有自由 `body` 与总体来源的论点
- **THEN** 系统不自动生成 `substantive_claims`;后续必须通过独立抽取步骤添加子论断出处

### Requirement: 跨市场传导 (Cross-market Transmission)

一条论点 MAY 通过两步抽取携带 `origin_market`、`target_market` 与 `transmission_path`,用于承载"全球结构信息 -> A股标的"的推导。系统 MUST NOT 要求自由生成时预先填写这些字段;这些字段 SHOULD 由独立 extractor 或人工审阅在自由 `body` 之后添加。

`transmission_path` MUST 是带出处的步骤数组,每一步包含传导描述与来源信号链接。无出处的传导步骤 MUST 被标记为待核,不得被当成已证实链条。

`transmission_map` 是积累式可信跨市场链接记忆,只能写入 confirmed thesis 的传导路径。draft / unconfirmed thesis MAY 保留自身 `transmission_path`,但 MUST NOT 写入 `transmission_map`。

#### Scenario: 自由论点不强制跨市场字段
- **WHEN** 系统创建自由叙事论点
- **THEN** 系统不得因缺少 `origin_market`、`target_market` 或 `transmission_path` 而拒绝它

#### Scenario: 跨市场传导链可审计
- **WHEN** 一条论点从全球信息反推 A股受益标的
- **THEN** 系统记录 `origin_market`、`target_market` 与带来源的 `transmission_path`

#### Scenario: 未确认传导不进入可信链接记忆
- **WHEN** 一条 draft thesis 携带 `transmission_path`
- **THEN** 系统不得将该路径写入 `transmission_map`

### Requirement: 对抗证伪 (Adversarial Falsification)

一条论点在被标记为"confirmed"之前 MUST 经过一次独立的对抗证伪(由独立评审实例执行)。证伪结果 MUST 附上最强反方论证与至少一个对冲变量。缺少对抗证伪的论点 MUST NOT 被标记为 confirmed。

对抗证伪 MUST 记录 `review_session` 元数据,至少包含 `thesis_author_id`、`reviewer_instance_id`、`reviewer_persona`、`review_run_id`。确认时 `reviewer_instance_id` MUST NOT 等于 `thesis_author_id`,且 `reviewer_persona` MUST 与作者 persona 不同。不同模型可选;高 stakes 情况 MAY 引入人工复核。

#### Scenario: 未经证伪的论点不得确认
- **WHEN** 一条论点尚未经过对抗证伪
- **THEN** 系统将其状态保持为"未确认",不允许其进入可投标的生成

#### Scenario: 证伪附带反方与对冲
- **WHEN** 一条论点通过对抗证伪
- **THEN** 系统在其上记录最强反方论证与至少一个对冲变量

#### Scenario: 自导自演证伪不得确认
- **WHEN** 一条论点的 `reviewer_instance_id` 与 `thesis_author_id` 相同
- **THEN** 系统拒绝将该论点标记为 confirmed

### Requirement: 战绩记录 (Track Record)

每条论点 MUST 落一条带时间戳的战绩记录,包含:方向判断(利多/利空)、一个可证伪的预期、以及验证时间窗。该记录 MUST 支持事后回填实际结果。本 change 只要求 outcome 回填与显式边界;完整校准统计 MUST 在后续 `feedback-calibration` change 中实现,当前 `calibrate()` MUST 明确标记为 not implemented。

反馈接口 MUST 区分 `outcome_raw` 与 `calibration_signal`。每日复盘只写入 `outcome_raw`;只有验证窗口到期、事件已发生、或结果置信足够时,成熟度过滤才 MAY 生成 `calibration_signal` 供周级深研读取。

#### Scenario: 论点落战绩记录
- **WHEN** 一条论点被确认
- **THEN** 系统记录其方向、可证伪预期、验证时间窗与时间戳

#### Scenario: 结果可回填并保留校准边界
- **WHEN** 验证时间窗到期
- **THEN** 系统支持回填实际结果,并明确完整校准尚未在本 change 实现

#### Scenario: 未成熟结果不得进入校准信号
- **WHEN** 一条回填结果尚未到验证窗口、事件未发生、且置信不足
- **THEN** 系统只保留 `outcome_raw`,不得生成 `calibration_signal`

#### Scenario: 成熟结果生成校准输入
- **WHEN** 一条回填结果满足成熟度过滤
- **THEN** 系统可生成 `calibration_signal` 作为后续周级深研输入

### Requirement: 人在环决策记录 (Human Decision Record)

系统 MUST 记录人在环裁定,且 MUST 与市场结果 `track_record` 分离。`human_decisions` 至少包含决策对象、decision(`accepted` / `rejected` / `overridden`)、理由、时间。该记录用于学习用户判断,不得直接混入市场 outcome calibration。

#### Scenario: 用户否决被记录
- **WHEN** 用户否决一个系统提议的标的或论点
- **THEN** 系统记录 decision、理由与时间,并保持其与市场 outcome 分离

### Requirement: 置信度与不确定性标注 (Confidence & Uncertainty)

每条论点 MUST 携带置信度,并对薄弱处显式打标签(无来源 / 单源 / 证据薄弱 / 时滞长)。系统 MUST NOT 将猜测呈现为事实陈述。

#### Scenario: 单源论点被标注
- **WHEN** 一条论点仅由单一来源支撑
- **THEN** 系统为其打上"单源"标签并相应下调置信度

#### Scenario: 零来源论点被标注
- **WHEN** 一条论点没有任何来源信号支撑
- **THEN** 系统为其打上"无来源"标签并将置信度压低


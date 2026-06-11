## MODIFIED Requirements

### Requirement: 近重复去重 (Deduplication)

系统 MUST 在近期有界窗口内对近重复信号去重(基于内容相似度,如 Jaccard 或 embedding)。当前实现用最近 500 条信号近似近期窗口;后续 MAY 在采集源时间语义稳定后升级为按 N 天滑动时间窗。重复项 MUST 被合并或丢弃,只保留一条规范记录。

近重复度量 MUST 只在相似度计算中做 dedup-only normalization: HTML entity unescape、strip HTML/XML tags、collapse whitespace。该 normalization MUST NOT 改写存储的 `body` 或 `raw_payload`。

当前默认近重复度量 MUST 为语言感知 Jaccard: CJK 占非空白字符比例达到 `0.20` 时使用字符 2-gram;否则使用小写 alphanumeric word 2-shingle。CJK 判断 MUST 至少覆盖 CJK Unified Ideographs `U+4E00`-`U+9FFF`。默认阈值 MUST 为 `0.14`,并 MUST 做成可配置项。

近重复去重 MUST 优先避免假阳性:不同文章被误并会销毁信号,比漏掉重度改写重复更不可恢复。该度量不承诺捕捉语义级或重度改写重复;这类能力 MUST 由后续 semantic / embedding dedup change 承担。

#### Scenario: 重复报道被合并
- **WHEN** 多个来源在近期有界窗口内报道同一事件且内容相似度超过阈值
- **THEN** 系统将其合并为一条信号,并记录所有来源出处

#### Scenario: 英文不同文章不被误杀
- **WHEN** 同一英文 RSS 源提交多条不同文章,且其相似度低于默认阈值
- **THEN** 系统不得将它们标记为 `near_duplicate`

#### Scenario: 英文真近重复被去重
- **WHEN** 英文报道描述同一具体事件且 word 2-shingle 相似度达到默认阈值
- **THEN** 系统将后到信号标记为 `near_duplicate`

#### Scenario: 中文不同文章不被误杀
- **WHEN** 中文同领域但不同事件的信号相似度低于默认阈值
- **THEN** 系统不得将它们标记为 `near_duplicate`

#### Scenario: 中文真近重复被去重
- **WHEN** 中文报道描述同一具体事件且 CJK char 2-gram 相似度达到默认阈值
- **THEN** 系统将后到信号标记为 `near_duplicate`

#### Scenario: 重度改写重复留给语义去重
- **WHEN** 英文报道是同一事件的重度改写,但 word 2-shingle 相似度低于默认阈值
- **THEN** 系统不得为抓住该重复而降低全局阈值或牺牲不同文章的保留率

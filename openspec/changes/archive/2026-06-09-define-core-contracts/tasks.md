## 1. 把契约落成机器可校验的 schema

- [x] 1.1 将 `signal-contract` 写成 JSON Schema(出处必填、去重 key、类型标签、轻量排除标志、原始载荷留存)
- [x] 1.2 将 `thesis-contract` 写成 JSON Schema(自由叙事 body + 出处链接 + 对抗证伪块 + 战绩记录 + 置信/不确定标签)
- [x] 1.3 将 `target-contract` 写成 JSON Schema(`logic_score` 与 `buy_point` 两个独立字段 + 状态机枚举 + 催化剂/退出触发 + 已涨幅 + thesis 链接)

## 2. 关键不变量校验器(只防"确定性错误",不卡推理)

- [x] 2.1 signal:缺 source 或 date 即拒收;近重复按相似度阈值去重
- [x] 2.2 thesis:未经对抗证伪不得置为 confirmed;无出处的实质论断打"待核"标
- [x] 2.3 target:拒绝单一合并总分;`buy_point` 不利时禁止标为"现在买入";无支撑论点拒入名单

## 3. 直觉优先的执行接口(轻结构)

- [x] 3.1 定义"自由生成"接口:论点 body 为自由文本,不绑定字段模板与推导顺序
- [x] 3.2 定义对抗证伪接口:独立评审实例(不同角度/persona),产出最强反方 + 至少一个对冲变量
- [x] 3.3 定义战绩记录接口:方向 + 可证伪预期 + 验证时间窗 + 结果回填钩子

## 4. 存储与最小骨架

- [x] 4.1 建 SQLite 表:`signals` / `theses` / `targets` / `track_record`,含每源增量游标与去重 hash
- [x] 4.2 写 `last30days` Adapter:把 `--agent` 输出映射到 `signal-contract`(定位为注意力源,不享高权重)
- [x] 4.3 写入前强制过 schema 校验 + 第 2 组不变量校验

## 5. 验收

- [x] 5.1 每份 spec 的每个 `#### Scenario:` 映射到一个校验测试用例
- [x] 5.2 `openspec validate define-core-contracts --strict` 通过

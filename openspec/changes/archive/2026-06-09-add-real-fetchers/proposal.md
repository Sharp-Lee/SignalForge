## Why

采集层骨架已经通了,但还没有任何真实数据流进来 —— 所有 fetcher 都是注入的 fixture。本 change 给既有 Adapter 框架补上**真实 fetcher**,让真实信号第一次进系统,并把"游标驱动增量"真正行使起来(现在只靠去重兜底)。

优先两个性价比最高的源:**last30days**(本机即可跑的真实源,接一个子进程 fetcher 就能立刻产出真实信号)和 **RSS/Atom**(全球新闻 HTTP 拉取)。GDELT、市场行情/①b 真实源留作后续。**保持 MVP**,加新真实源 = 再写一个 fetcher,框架不动。

## What Changes

- 给 `source-ingestion` 能力新增"真实 fetcher"相关要求与实现:
  - **last30days 真实 fetcher**:以子进程跑 `last30days.py --agent`,把输出喂给既有 `Last30DaysAdapter`。
  - **RSS/Atom HTTP fetcher**:真实拉取一个 feed,喂给既有 `RssAtomAdapter`。
  - **可注入 transport(关键约束)**:每个真实 fetcher 的底层 I/O(HTTP get / 子进程 spawn)MUST 做成可注入 seam;测试用录制/stub transport **离线**跑,MUST NOT 打外网、MUST NOT 真跑 last30days 子进程。
  - **游标驱动增量**:真实 fetcher MUST 用 cursor 只取新条目(RSS 按已见 guid 或时间戳;last30days 按上次运行时间),让游标真正行使,不再只靠下游去重兜底。
  - **fetch 级错误韧性**:runner / fetcher MUST 捕获 fetch 级失败(网络超时、坏 feed、子进程非零退出),记为 source 级 error 并继续下一个源,不得让一个源失败拖垮整轮采集。
- **本 change 不做**:GDELT、市场行情/①b 真实源、密钥/配置管理、三层调度策略 —— 留后续 change。

## Capabilities

### New Capabilities

（无 —— 不新增能力。）

### Modified Capabilities

- `source-ingestion`:为既有能力新增真实 fetcher 的要求 —— 可注入 transport、游标驱动增量拉取、fetch 级错误韧性。骨架阶段的协议/runner/adapter 不变,只是补上"真正能拉真实数据"这层,并把 cursor 从"已存储"升级为"真正驱动增量"。

## Impact

- 真实信号**首次**流入 SQLite 记忆底座(至少 last30days + 一个真实 RSS feed)。
- 整条"输入腿"端到端用真实数据验证过。
- 测试仍**全离线**(stub transport),不打外网、不真跑 last30days 子进程。
- runner 对真实世界失败(超时/坏数据/子进程错)有韧性,单源失败不影响其余源。
- 后续真实源(GDELT、市场行情)= 再写一个符合协议的 fetcher,框架与下游零改动。

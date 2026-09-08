# 知识维护

## 两层沉淀

### 个人智能体知识

长期事实唯一写入 `/Users/sgx/Documents/Notes/4-Agents/memory/facts.jsonl`；推断、冲突或来源不完整的候选写入同目录 `pending.jsonl`，更正和处理记录写入 `events.jsonl`。按 `BOOTSTRAP.md` 规定的 schema、来源定位和幂等规则维护；会话工作流及后台 recorder 不直接写这些账本，每日 08:00 任务负责提炼和回填 `AI_KB_LINKS`。

| 内容 | 位置 |
|---|---|
| 已确认/可复现事实 | `memory/facts.jsonl` |
| 待确认候选 | `memory/pending.jsonl` |
| 更正、撤回和同步事件 | `memory/events.jsonl` |
| 可复制模板 | `template/` |
| 可重复执行的工作流 | `skills/`（按 `dev/`、`tools/` 分类） |

`INDEX.md` 只承担导航；不要创建或引用旧的 `memory/knowledge/` 目录，也不要把 AI 会话快照当事实来源。

### 团队工程知识库

同时满足以下条件才写入工程：

- 结论由当前代码验证。
- 对其他播放开发者或 AI 可重复使用。
- 属于稳定架构、数据流、生命周期、边界或规范。
- 不是临时实验、一次性需求细节或排障日志。

路由：

| 知识范围 | 工程位置 |
|---|---|
| 跨播放业务公共规范 | `BBVideo/doc/` |
| Story | `Components/Suites/Story/doc/` |
| 详情页 Base | `VideoDetail/Base/doc/` |
| 详情页 Module | `VideoDetail/Module/doc/` |
| UGC 详情业务 | `Entrance/BBUGCVideoDetail/doc/` |
| 播放器 | `Components/Player/doc/` 或 `BBPlayerCore/doc/` |
| Resolver | `BBResolver/doc/` |

## 更新规则

- `README.md` 只做入口和导航，专题细节放 `spec/topics/`。
- 模板放 `spec/template/`。
- 优先更新已有文档，避免重复主题。
- 文档必须给出稳定代码锚点和维护边界。
- 新增或移动文档后同步更新最近一级 `README.md` 文档地图。
- 跨模块公共文档同步更新 `BBVideo/README.md`。
- 不自动提交工程文档；与代码一起交给用户确认。

# 知识维护

## 两层沉淀

### 个人智能体知识

知识写入 `/Users/sgx/Documents/Notes/4-Agents/memory/knowledge/`（协作纪律进 `knowledge/规则与纪律/`）；模板/技能写入 `/Users/sgx/Documents/Notes/4-Agents/plugins/sgx-skills`：

| 内容 | 目录 |
|---|---|
| 业务知识、具体 Bug、操作手册 | `memory/knowledge/`（按 业务模块/工程基建/排障经验/规则与纪律 归类） |
| 编程纪律、协作规则 | `memory/knowledge/规则与纪律/` |
| 可复制模板 | `template/` |
| 可重复执行的工作流 | `skill/` |

同步更新 `memory/knowledge/知识索引.md` 与 `4-Agents/plugins/sgx-skills/CLAUDE.md` 索引。

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

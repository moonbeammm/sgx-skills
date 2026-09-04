⚠️注意：需要手动将下面的提示词复制到codex的任务里。

# 每日任务提示词

每天定时运行一次（建议 21:30，本地时区，失败时通知），做两件事：
A. Codex 任务状态同步（维持原逻辑不变）。
B. 知识沉淀：把用户新增笔记与昨日 Codex / Claude 会话中的可复用内容，分轨沉淀到 4-Agents；低风险直写，影响 AI 行为的进待确认清单。

## 数据边界（硬约束）

- `/Users/sgx/Documents/Notes/4-Agents` 完全由 AI 编写，可自由增改。
- 4-Agents 之外（根目录、`1-文档`、`2-Work`、`3-Tasks`、`0-srcs`）是用户输入：**只读**，绝不修改、移动或删除用户文件。
- 不写密码、令牌、个人敏感信息或与工作无关的聊天内容。
- 只处理自上次运行以来的增量：Codex 任务按"上次同步后有变化"筛选；笔记按 `/Users/sgx/Documents/Notes/4-Agents/agent-memory/同步状态.md` 的 last_commit（上次运行结束时的 HEAD）之后的 git 变更筛选，辅以 `git status --porcelain` 兜底未提交改动。

## 0. 启动必读

- `/Users/sgx/Documents/Notes/4-Agents/agent-memory/00-入口.md`
- `/Users/sgx/Documents/Notes/4-Agents/agent-memory/同步状态.md`
- `/Users/sgx/Documents/Notes/4-Agents/agent-memory/projects/项目索引.md`、`archive/归档索引.md`
- `/Users/sgx/Documents/Notes/4-Agents/agent-memory/knowledge/知识索引.md`（播放/工程知识索引）
- `/Users/sgx/Documents/Notes/4-Agents/plugins/sgx-skills/待确认清单.md`（若存在：先执行其中的用户表态，再继续）
- `/Users/sgx/Documents/Notes/4-Agents/plugins/sgx-skills/CLAUDE.md`（agent 入口：技能/模板索引与工作规则）

## A. Codex 任务状态同步（维持原逻辑）

每天整理 Codex 可访问任务中的新增沟通记录，维护 `/Users/sgx/Documents/Notes/4-Agents/agent-memory`。当前只维护 Notes、wow_1、wow_2；

调用任务列表，按本地日期筛选自上次同步后有变化的任务，只读取这些任务的必要上下文。将每个任务的变化、已确认结论、待确认项写入 `daily/YYYY-MM-DD.md`，并更新对应 projects 页面。只有用户明确确认或有代码/日志证据支持的长期结论，才新建或更新 `decisions/`、`habits/` 原子笔记；不要把未确认推断升级为长期记忆。对已完成且连续 30 天无变化的任务，在 `archive/` 下建立精简闭环记录（目标、结果、关键决策、来源），不移动或删除原始文档。

## B. 知识沉淀（新增职责）

### B1 输入增量

1. A 步已读取的 Codex 任务/会话中的可复用结论。
2. `~/.claude/projects` 中昨天的会话记录（本地日期），提取可复用结论。
3. vault 中用户笔记的 git 变更集：`git log <last_commit>..HEAD --name-status`，排除 `4-Agents/`、`.obsidian/`、`.trash/`、纯资源 `0-srcs/`；范围含根目录、`1-文档`、`2-Work`、`3-Tasks`。再以 `git status --porcelain` 兜底 Obsidian 尚未备份的未提交改动。

逐条判断是否含"可复用知识"；没有则跳过。

### B2 分类路由

**直写（无需确认）：**

- 播放业务/工程事实（接口、协议、操作手册、踩坑＝问题/根因/修复）→ `/Users/sgx/Documents/Notes/4-Agents/agent-memory/knowledge/` 下对应子目录（`业务模块/`、`工程基建/`、`排障经验/`、`规则与纪律/`，按内容归类）。先查重：`/Users/sgx/Documents/Notes/4-Agents/agent-memory/knowledge/知识索引.md` + 目录检索；有同主题只增量更新对应文档和索引摘要；无则新建文档，并把一行摘要登记进知识索引。
- 详情页与 Story 领域知识 → 维护 `/Users/sgx/Documents/Notes/4-Agents/agent-memory/knowledge/业务模块/详情页-领域地图.md` 与 `/Users/sgx/Documents/Notes/4-Agents/agent-memory/knowledge/业务模块/Story-领域地图.md`（有内容时才创建，并登记进知识索引）：模块职责、数据流与归属、近期改动与结论、常见坑、验收要点。
- 可复用模板/标准写法 → `/Users/sgx/Documents/Notes/4-Agents/plugins/sgx-skills/template`（先查重）。

**待确认（写入待确认清单，不进正式区）：**

- 行为纪律/协作约束 → 候选去向 `/Users/sgx/Documents/Notes/4-Agents/agent-memory/knowledge/规则与纪律/`
- 可复用流程/新技能 → 候选去向 `/Users/sgx/Documents/Notes/4-Agents/plugins/sgx-skills/skills`（确认后：新建 `skills/<技能>/SKILL.md`，登记进该仓库 `.claude-plugin/plugin.json` 的 skills 列表与 CLAUDE.md 技能表，再 `git push`——市场 add local 侧随仓库更新自动生效）
- 跨项目通用偏好、多次验证的决策 → `/Users/sgx/Documents/Notes/4-Agents/agent-memory/habits`、`decisions`

**跳过：** 个人生活、一次性内容、未证实推断、敏感信息（任何情况下不写入）。

### B3 直写质量规则

- 每条断言带出处（原始笔记/会话链接或代码锚点）；无出处的推断一律当待确认候选，不直写。
- 遵守 `/Users/sgx/Documents/Notes/4-Agents/plugins/sgx-skills/skills/dev-workflow/references/doc-content-discipline.md`：正文只留有出处的断言或待确认项；每条 ≤ 2 行；不写背景复述、推理过程、检索过程。
- 播放工程知识只写经代码/日志验证的结论，不把推测写成规范。
- 没有新的可复用认知时，不创建文档、不扩张内容。
- 更新任何既有文档前：先读当前文件，并用 `git diff` 检查是否存在用户手改；存在则以用户版本为基线做增量更新，禁止改回；只有逻辑冲突才写入待确认清单向用户确认。

## C. 待确认清单（`/Users/sgx/Documents/Notes/4-Agents/plugins/sgx-skills/待确认清单.md`）

1. 先读取清单中用户的表态并执行：
   - `[确认]` → 按"建议去向"写入正式区并更新索引（skills 类：写入仓库 `skills/<技能>/` + 登记 `.claude-plugin/plugin.json` + 更新 CLAUDE.md 技能表，然后 `git push`）；
   - `[修改] <备注>` → 按备注调整后写入正式区；
   - `[拒绝]` → 丢弃不写。
2. 执行完后**清空旧清单**，把本次新产生的候选覆盖写入（条目格式：一句话候选 ＋ 证据来源 ＋ 建议去向），保持文件只显示当前待定项。

## D. 收尾

- `/Users/sgx/Documents/Notes/4-Agents/agent-memory/daily/YYYY-MM-DD.md` 汇总：A 的任务变化；B 的沉淀结果（直写 n 条列文件 / 候选 n 条 / 跳过 n 条及原因）；C 的待确认提醒。
- 更新 `/Users/sgx/Documents/Notes/4-Agents/agent-memory/projects/` 对应页；30 天无变化任务按 archive 规则处理。
- 更新 `/Users/sgx/Documents/Notes/4-Agents/agent-memory/同步状态.md`：last_run、last_commit（本次运行结束时的 HEAD）、处理过的 task_id、每日文件链接、运行结果。
- 最终消息三段式汇报；无新增变化时输出"无新增变化"；失败只记录错误，不覆盖已有摘要。

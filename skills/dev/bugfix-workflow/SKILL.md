---
name: bugfix-workflow
description: Use when 排查或修复 Bilibili 客户端播放、客诉或设备特定问题，且需要 mid、buvid、设备日志、Fawkes 或源代码证据时。
---

# bugfix-workflow

## 执行熔断（必须）

- 开始回复先列出目标、允许修改路径、明确不做项、完成条件和本阶段预算。默认预算为 20 分钟或 10 次工具调用，先到者触发；预计超出时先停下来分阶段说明。
- 只修改已列入白名单的路径。需要扩大范围、删除/迁移文件、改自动任务或调用外部系统时，先停并取得用户确认。
- 每 5 次工具调用或 10 分钟发送一次进度；预算耗尽立即停止并报告，不静默续跑。
- 网络、依赖或模型接口失败最多重试 1 次；仍失败就标记“未验证”，交付已有本地结果，不继续等待。
- 后台子 agent 最多 1 个，最长等待 5 分钟；主 agent 不等待其完成，也不允许递归派发。
- 达到完成条件后立即交付；历史回填、全量扫描、整包构建和端到端模型测试不自动追加。
- 最终报告必须分别列出已修改、未修改、已验证、未验证和下一步；“未验证”不得写成“完成”。

开始排查前先读取 `/Users/sgx/Documents/Notes/4-Agents/memory/BOOTSTRAP.md`，按问题关键词和 `project:bilibili-client` 调用 `/Users/sgx/Documents/Notes/4-Agents/memory/tools/lookup`，并在第一条回复回执检索状态。命中结论必须标注事实 ID、库内位置和来源；待确认内容不能用于归因。

每次排查还必须读取同级的 `../session-recording.md`（canonical：`/Users/sgx/Documents/Notes/4-Agents/plugins/sgx-skills/skills/dev/session-recording.md`）：在问题目标明确后确定唯一主文档和 `task_id`，复用用户提供的原始文档或在 Notes 根目录创建 `MMDD-问题.md`，并尽力启动后台 recorder。会话期间只维护时效性续接快照，不直接写长期事实账本。

## 会话记录硬门槛

1. 目标明确后先按 `session-recording.md` 选择唯一主文档；用户明确给出的原始 `.md` 优先，不能凭相似文件名另建平行日志。无原始文档时才在 Notes 根目录原子创建 `MMDD-问题.md`。
2. 确定 `task_id` 后尽力派发一个后台 recorder，主 agent 不等待；将证据、已确认结论、阻塞和下一步以精简增量发送给 recorder。recorder 只能写 `AI_SESSION_RECORD`，不得写知识库、代码、Git 或保护区。
3. 主 agent 每次写入前重读并保留 `背景`/`诉求`、`AGENT_PROGRESS` 和用户手改；会话期间不写 `facts.jsonl`、`pending.jsonl`、`events.jsonl`。最终回复前按协议等待、回退或报告真实状态。

## 原则

1、不靠猜测归因。用用户信息、Fawkes 日志、接口数据和代码链路证明根因。
2、修复必须添加开关，开关模板参考 `template/开关模版.md`

## 流程

1. 收集用户反馈基础信息：
   - `mid`
   - `buvid`
   - App 版本、平台、设备和发生时间
   - `avid/cid/epid/roomid` 等内容标识
   - 复现步骤和实际表现
2. **REQUIRED SUB-SKILL:** 使用 `fawkes:fawkes-laser` 或 `mcp-free-skills:fawkes-all` 查询日志。
3. 先查询用户是否已反馈日志；没有日志时再通过 `buvid` 发起拉取。
4. 根据日志时间线定位播放链路。
5. 对照当前版本代码确认职责归属和触发条件。
6. 输出证据、根因、影响范围和建议修复。
7. 落实到主文档：没有用户提供的原始文档时按 `../session-recording.md` 在 `/Users/sgx/Documents/Notes/` 根目录创建；有文档时原地增量更新，不另建平行日志。排障正文沿用 `template/文档模板.md`，不得改动用户保护区；关键状态变化同步给 recorder。

## 输出

- 用户与环境信息。
- 关键日志时间线。
- 代码链路。
- 已排除的可能性。
- 确认根因或仍缺少的证据。
- 修复建议、FF 止损和验证路径。

如果证据不足，明确需要补充什么日志，不把推测写成结论。最终回复先给排障/修复结果，再附主文档路径、最后 checkpoint、recorder 状态和未验证边界；事实提炼及 `memory` 引用回填由每日任务完成。

# 相关文档

| 主题     | 文档路劲              |
| ------ | ----------------- |
| 添加开关原则 | `template/开关模版.md` |

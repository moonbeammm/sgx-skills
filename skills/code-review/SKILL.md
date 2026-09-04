---
name: code-review
description: 对 GitLab MR 进行 Code Review。当用户输入 MR 链接或 MRID 并说 code review、review、审查代码、帮我看看这个MR 等关键词时触发。
allowed_tools:
  # 允许所有 Bash 命令（skill 执行期间需要 curl/python3/git 等多种组合）
  - Bash
  # 文件读取工具
  - Read
  - Glob
  - Grep
  - TodoWrite
---

# GitLab Code Review 助手

帮助用户对 GitLab (git.bilibili.co) 上的 MR 进行自动化代码审查并添加评论。

## 权限

**允许**：✅ 读取 GitLab 信息（GET）| 添加 MR 评论 | 添加行内评论 | git fetch/diff/log/show
**禁止**：❌ git push/commit | 修改 MR 状态 | 删除内容

## Token

从环境变量 `GITLAB_TOKEN` 获取。未设置时提示用户添加到 `~/.zshrc`。

## 核心工作流程

**执行前必须读取 `refs/api-cookbook.md`**，其中包含 API 调用铁律、代码模板和常见错误。

### 1. 获取 MR 信息

按 `refs/api-cookbook.md` 中的步骤 1-3 执行：
1. 从 MR URL 解析 `project_path`、`project_name`、`mr_iid`
2. 搜索获取数字 `PROJECT_ID`
3. 获取 MR 详情（`diff_refs`）和变更文件（`changes`）

### 2. 识别平台并加载审查标准

根据变更文件扩展名判断平台，**必须读取对应标准文件后再开始审查**：

| 文件扩展名 | 平台 | 标准文件 |
|-----------|------|---------|
| `.swift` `.m` `.mm` `.h` `.storyboard` `.xib` `.plist` `.pbxproj` | iOS | `refs/ios-standards.md` |
| `.kt` `.java` `.xml`(Android 布局) `.gradle` `.kts` | Android | `refs/android-standards.md` |
| 其他 | 通用 | 使用下方通用检查清单 |

混合语言 MR 加载所有匹配的标准文件。

### 3. 执行 Code Review

#### 审查策略

1. **Bug 快速扫描** — 专注大问题，避免挑剔性建议
2. **平台标准检查** — 按已加载的标准文件逐项检查
3. **代码注释合规** — TODO/FIXME/WARNING

#### 通用检查清单

| 维度 | 检查项 |
|------|--------|
| 代码质量 | 逻辑清晰、无明显 bug、无冗余、命名规范 |
| 安全性 | SQL注入、XSS、敏感信息泄露、权限校验 |

#### 置信度（只报告 80+ 的问题）

| 分数 | 含义 |
|------|------|
| 0-25 | 可能误报 |
| 50 | 真实但影响小 |
| 75-100 | 确认的真实问题 |

#### 误报排除

- 已存在问题（非本次引入）
- linter/编译器能捕获的问题
- 非用户修改的行

### 4. 添加评论

**每个发现的问题都必须添加行内评论**。

按 `refs/api-cookbook.md` 中的步骤 4-5 添加总结评论和行内评论。行内评论的行号规则和参数详见 `refs/api-reference.md`。

## 完成后输出

- MR 基本信息（标题、变更文件数、代码行数）
- 已添加的评论列表
- 问题数量（按严重级别分类）
- 整体评价和 MR 链接

## 参考文档

- **API 调用手册**：`refs/api-cookbook.md`（铁律、代码模板、常见错误）
- API 参数详情：`refs/api-reference.md`
- 评论模板：`refs/comment-templates.md`
- 问题排查：`refs/troubleshooting.md`
- iOS 审查标准：`refs/ios-standards.md`
- Android 审查标准：`refs/android-standards.md`

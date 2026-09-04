# GitLab Code Review Skill

一个 Claude Code 插件技能，用于自动化 GitLab Merge Request 代码审查。

## 功能特性

- 自动获取 MR 变更并进行多维度代码审查
- 在 MR 上添加总结评论
- 在问题代码行添加行内评论
- 智能误报过滤，只报告高置信度问题

## 前置要求

### 配置 GitLab Token

在 shell 配置文件（`~/.zshrc` 或 `~/.bashrc`）中添加：

```bash
export GITLAB_TOKEN="你的GitLab私有Token"
```

Token 获取方式：
1. 登录 [git.bilibili.co](https://git.bilibili.co)
2. 进入 Settings → Access Tokens
3. 创建 Token，勾选 `api` 和 `read_repository` 权限

## 使用方法

### 触发方式

在 Claude Code 中输入 MR 链接并使用以下关键词触发：

```
# 方式 1：MR 链接 + 关键词
https://git.bilibili.co/platform/go-ott/-/merge_requests/7170 帮我 review

# 方式 2：简写形式
review MR !7170

# 方式 3：中文关键词
审查代码 https://git.bilibili.co/platform/go-ott/-/merge_requests/7170
```

### 支持的触发关键词

| 关键词 | 示例 |
|--------|------|
| code review | `code review 这个 MR` |
| review | `review 一下` |
| 审查代码 | `帮我审查代码` |
| CR | `CR 一下` |
| 帮我看看 | `帮我看看这个 MR` |

## 审查维度

Skill 从以下 5 个维度进行代码审查：

1. **项目规范检查** - 检查是否符合 CLAUDE.md 中定义的编码规范
2. **Bug 扫描** - 识别明显的 bug 和错误
3. **Git 历史分析** - 结合代码历史上下文分析
4. **团队习惯** - 参考历史 MR 评论
5. **注释合规** - 检查 TODO/FIXME/WARNING

### 检查清单

| 维度 | 检查内容 |
|------|----------|
| 代码质量 | 逻辑清晰度、冗余代码、命名规范 |
| 安全性 | SQL 注入、XSS、敏感信息泄露 |

## 输出内容

Review 完成后，Skill 会：

1. **在 MR 上添加总结评论**
   - 整体评价（✅ 良好 / ⚠️ 需修复 / ❌ 严重问题）
   - 变更概述
   - 亮点
   - 问题列表

2. **在问题代码行添加行内评论**
   - 问题级别标识
   - 问题描述
   - 修改建议

3. **向用户报告**
   - MR 基本信息
   - 发现问题数量（按级别分类）
   - MR 链接

## 问题级别说明

| 级别 | 含义 | 处理建议 |
|------|------|----------|
| **[Critical]** | 安全漏洞、严重 bug | 必须修复 |
| **[Major]** | 潜在 bug、性能问题 | 建议修复 |
| **[Minor]** | 代码风格、命名问题 | 可选修复 |
| **[Suggestion]** | 优化建议 | 参考即可 |

## 文件结构

```
code-review/
├── SKILL.md              # 主技能定义文件
├── README.md             # 本文档
└── refs/
    ├── api-reference.md    # GitLab API 参考
    ├── comment-templates.md # 评论格式模板
    └── troubleshooting.md   # 问题排查指南
```

## 常见问题

### Token 未生效

确保设置环境变量后重新加载配置：
```bash
source ~/.zshrc
```

### 评论添加失败

检查 Token 权限是否包含 `api` scope。

### 行内评论报错 400

行号必须在 MR diff 的变更范围内，详见 `refs/troubleshooting.md`。

### 🔴 Review 了太多不相关的代码

**现象**：MR 只有几行变更，但 review 分析了上百个文件

**原因**：使用 `git merge-base` 获取 diff，而不是 GitLab API 的 versions 接口

**解决**：必须先调用 `/merge_requests/{iid}/versions` 获取 `base_commit_sha` 和 `head_commit_sha`，然后用这两个 SHA 做 diff

详见 `SKILL.md` 中的"常见错误案例"。

## 注意事项

- Skill 只会读取代码和添加评论，**不会**推送代码或修改 MR 状态
- 只报告高置信度（80+）的问题，避免误报干扰
- 不会评论已存在的问题（非本次 MR 引入）

## 反馈与改进

如有问题或建议，请联系 skill 维护者或提交 issue。
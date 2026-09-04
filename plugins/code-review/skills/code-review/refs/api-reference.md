# GitLab API 参考

## 常用 API 端点

| 操作 | 方法 | 端点 |
|------|------|------|
| 获取 MR 详情 | GET | `/projects/:id/merge_requests/:mr_iid` |
| 获取 MR 变更 | GET | `/projects/:id/merge_requests/:mr_iid/changes` |
| 获取 MR 版本 | GET | `/projects/:id/merge_requests/:mr_iid/versions` |
| 添加 MR 评论 | POST | `/projects/:id/merge_requests/:mr_iid/notes` |
| 添加行内评论 | POST | `/projects/:id/merge_requests/:mr_iid/discussions` |
| 获取文件内容 | GET | `/projects/:id/repository/files/:file_path/raw?ref=:branch` |

## 项目 ID 格式

- 数字 ID: `12345`
- URL 编码路径: `platform%2Fgo-ott`（`/` 编码为 `%2F`）

## API 调用示例

### 获取 MR 详情

```bash
curl -s -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "https://git.bilibili.co/api/v4/projects/${PROJECT_PATH_ENCODED}/merge_requests/${MR_IID}" | jq '{
    title: .title,
    author: .author.name,
    source_branch: .source_branch,
    target_branch: .target_branch,
    state: .state,
    web_url: .web_url
  }'
```

### 获取 MR 版本信息

```bash
curl -s -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "https://git.bilibili.co/api/v4/projects/${PROJECT_PATH_ENCODED}/merge_requests/${MR_IID}/versions" | jq '.[0]'

# 返回示例:
# {
#   "id": 15805087,
#   "head_commit_sha": "3fe057b0fb87c09891a5c2442696e64cd34fa11a",
#   "base_commit_sha": "91d2fa3bd0ed3d6befa76f48588cce074a66e04b",
#   "start_commit_sha": "00ca0c4888d4a389a3b8cecd2dc40e495ec57c93",
#   "created_at": "2026-03-17T14:12:33.308+08:00",
#   "merge_request_id": 1469650,
#   "state": "collected",
#   "real_size": "46"
# }
```

### 添加总结评论

```bash
curl -s -X POST \
  -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"body": "评论内容..."}' \
  "https://git.bilibili.co/api/v4/projects/${PROJECT_PATH_ENCODED}/merge_requests/${MR_IID}/notes"
```

### 添加行内评论

**⚠️ 重要：行号参数使用规则**

`old_line` 和 `new_line` 的使用取决于评论目标行在 diff 中的类型：

| 评论目标 | old_line | new_line | 说明 |
|---------|----------|----------|------|
| 新增的行（`+` 开头） | 不填 | 填 | 只指定 `new_line` |
| 删除的行（`-` 开头） | 填 | 不填 | 只指定 `old_line` |
| 未变更的上下文行 | 填 | 填 | **必须同时指定** |

**常见错误**：
- ❌ 对新增/删除行同时指定 `old_line` 和 `new_line` → 报错 `line_code can't be blank`
- ❌ 对上下文行只指定其中一个 → 报错
- ❌ 使用 `line_range` 参数 → 报错 `must be a valid json schema`

#### 示例：评论删除/修改的行

```bash
curl -s -X POST \
  -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "body": "评论内容...",
    "position": {
      "base_sha": "从MR详情的diff_refs.base_sha获取",
      "start_sha": "从MR详情的diff_refs.start_sha获取",
      "head_sha": "从MR详情的diff_refs.head_sha获取",
      "position_type": "text",
      "old_path": "path/to/file.go",
      "new_path": "path/to/file.go",
      "old_line": 79
    }
  }' \
  "https://git.bilibili.co/api/v4/projects/${PROJECT_ID}/merge_requests/${MR_IID}/discussions"
```

#### 示例：评论新增的行

```bash
curl -s -X POST \
  -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "body": "评论内容...",
    "position": {
      "base_sha": "xxx",
      "start_sha": "xxx",
      "head_sha": "xxx",
      "position_type": "text",
      "old_path": "path/to/file.go",
      "new_path": "path/to/file.go",
      "new_line": 596
    }
  }' \
  "https://git.bilibili.co/api/v4/projects/${PROJECT_ID}/merge_requests/${MR_IID}/discussions"
```

#### 示例：评论未变更的上下文行

```bash
curl -s -X POST \
  -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "body": "评论内容...",
    "position": {
      "base_sha": "xxx",
      "start_sha": "xxx",
      "head_sha": "xxx",
      "position_type": "text",
      "old_path": "path/to/file.go",
      "new_path": "path/to/file.go",
      "old_line": 75,
      "new_line": 75
    }
  }' \
  "https://git.bilibili.co/api/v4/projects/${PROJECT_ID}/merge_requests/${MR_IID}/discussions"
```

**行内评论关键参数**：
- `base_sha/start_sha/head_sha`: 优先从 MR 详情的 `diff_refs` 字段获取（一次请求）；若 `diff_refs` 为空（MR 刚创建），回退到 versions API 取 `.[0]`（注意字段名不同：`base_commit_sha`/`start_commit_sha`/`head_commit_sha`）
- `old_path/new_path`: 文件路径（相对于仓库根目录），文件未改名时相同
- `old_line`: 删除行/上下文行在**原文件**中的行号
- `new_line`: 新增行/上下文行在**新文件**中的行号

**如何确定行号**：
1. 使用 `git diff base_sha..head_sha -- path/to/file.go` 查看 diff
2. 找到 `@@ -76,8 +72,7 @@` 这样的 hunk header
3. `-76` 表示原文件从第 76 行开始，`+72` 表示新文件从第 72 行开始
4. 数着 diff 中的行来确定具体行号

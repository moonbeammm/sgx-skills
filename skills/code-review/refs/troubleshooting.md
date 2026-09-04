# 常见错误及解决方案

## 1. jq 解析数组返回对象错误

**错误**：`jq: error (at <stdin>:0): Cannot index object with number`

**原因**：GitLab API 返回了错误信息（对象）而不是预期的数组。

**解决**：
1. 先检查 API 返回的原始数据
2. 确认 token 有效且有访问权限
3. 确认 MR ID 和项目路径正确

## 2. 环境变量未设置

**错误**：token 为空或 API 返回 401 未授权

**解决**：
```bash
# 检查环境变量
echo $GITLAB_TOKEN

# 设置（在 ~/.zshrc 或 ~/.bashrc）
export GITLAB_TOKEN="your_token"
source ~/.zshrc
```

## 3. 本地 master 分支过期

**问题**：diff 包含其他人合并的代码

**解决**：
```bash
git fetch origin master:master
# 或使用 origin/master
git fetch origin master
```

## 4. 行内评论行号无效

**错误**：`400 Bad request - Note {:line_code=>["can't be blank", "must be a valid line code"]}`

**原因**：`old_line` 和 `new_line` 的组合方式取决于行的类型

### 核心规则：根据 diff 中行的类型决定参数

| 评论目标 | old_line | new_line | 说明 |
|---------|----------|----------|------|
| 新增行 (`+`) | 不填 | 填 | 只指定 `new_line` |
| 删除行 (`-`) | 填 | 不填 | 只指定 `old_line` |
| 上下文行（未变更） | 填 | 填 | **必须同时指定** |

### 错误示例

```json
// ❌ 错误：对新增行同时指定了 old_line 和 new_line
{
  "position": {
    "old_line": 79,
    "new_line": 74  // 新增行不要指定 old_line！
  }
}

// ❌ 错误：对上下文行只指定了一个
{
  "position": {
    "new_line": 596  // 上下文行必须同时指定 old_line！
  }
}
```

### 正确示例

```json
// ✅ 正确：评论删除的行，只用 old_line
{
  "position": {
    "old_path": "app/service/live.go",
    "new_path": "app/service/live.go",
    "old_line": 79
  }
}

// ✅ 正确：评论新增的行，只用 new_line
{
  "position": {
    "old_path": "app/service/live.go",
    "new_path": "app/service/live.go",
    "new_line": 596
  }
}

// ✅ 正确：评论未变更的上下文行，同时指定
{
  "position": {
    "old_path": "app/service/live.go",
    "new_path": "app/service/live.go",
    "old_line": 75,
    "new_line": 75
  }
}
```

### 如何确定使用哪个参数

1. 查看 diff：`git diff base_sha..head_sha -- path/to/file.go`
2. 找到目标行：
   - 如果行以 `-` 开头（被删除）→ 使用 `old_line`
   - 如果行以 `+` 开头（新增）→ 使用 `new_line`
   - 如果是修改（先 `-` 后 `+`）→ 使用 `old_line`（删除行的行号）

### 其他可能原因

1. 行号不在 diff 范围内
2. 使用了 `line_range` 参数（不支持）
3. SHA 值不正确（应从 MR 详情的 `diff_refs` 获取）

## 5. jq 偶发解析失败（返回 null）

**现象**：`curl ... | jq '.title'` 返回 `null`，但实际 API 响应是正常的 JSON。

**原因**：git.bilibili.co 偶尔返回的内容会导致 jq 解析异常（网络波动、响应截断等），python 的 `json.load` 则不受影响。

**解决**：用 python 作为 jq 的 fallback。

```bash
# ❌ 可能偶发失败
curl -s -H "PRIVATE-TOKEN: $GITLAB_TOKEN" "$URL" | jq '.title'

# ✅ 稳定方案：python fallback
curl -s -H "PRIVATE-TOKEN: $GITLAB_TOKEN" "$URL" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(json.dumps(d.get('diff_refs'), indent=2))
"
```

**建议**：解析 MR 详情、changes 等大响应时优先用 python；versions 等小响应用 jq 通常没问题。如果 jq 返回 null，先不要以为 API 有问题，换 python 重试一次。

## 6. JSON 转义问题

**解决**：
```bash
# 简单 JSON（单引号）
curl -d '{"body": "简单内容"}'

# 需要变量（双引号 + 转义）
curl -d "{\"body\": \"$VARIABLE\"}"
```

## 7. API 返回空值

**可能原因**：
1. Token 无效/过期
2. 无项目访问权限
3. MR 不存在
4. 项目路径编码错误

**诊断**：
```bash
# 查看完整返回
curl -s -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "https://git.bilibili.co/api/v4/projects/${PROJECT_PATH_ENCODED}/merge_requests/${MR_IID}"
```
# GitLab API 调用手册

## 铁律

1. **curl 结果先存到 shell 变量**，再 `echo "$VAR" | python3` 解析。直接 `curl | python3` 管道对大 JSON 不稳定
2. **所有 JSON 解析使用 `json.loads(sys.stdin.read(), strict=False)`**。`strict=False` 不可省略（git.bilibili.co 返回的 JSON 含控制字符）
3. **所有 API 使用数字项目 ID**，不要用 URL 编码路径

---

## 调用模板

```bash
VAR=$(curl -s -H "PRIVATE-TOKEN: $GITLAB_TOKEN" "https://git.bilibili.co/api/v4/...")
echo "$VAR" | python3 -c "import sys, json; d = json.loads(sys.stdin.read(), strict=False); ..."
```

---

## 步骤 1：获取项目 ID

从 MR URL `https://git.bilibili.co/{namespace}/{project}/-/merge_requests/{mr_iid}` 提取：
- `PROJECT_PATH` = `{namespace}/{project}`（如 `ios/loktar`）
- `PROJECT_NAME` = `{project}`（如 `loktar`）
- `MR_IID` = MR ID

```bash
SEARCH_RESULT=$(curl -s -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "https://git.bilibili.co/api/v4/projects?search=${PROJECT_NAME}&simple=true")
echo "$SEARCH_RESULT" | python3 -c "
import sys, json
for p in json.loads(sys.stdin.read(), strict=False):
    if p.get('path_with_namespace') == '${PROJECT_PATH}':
        print(p['id']); break
"
```

从输出中获取 `PROJECT_ID`，后续步骤直接写死项目 ID 使用。

---

## 步骤 2：获取 MR 详情 + diff_refs

```bash
MR_JSON=$(curl -s -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "https://git.bilibili.co/api/v4/projects/${PROJECT_ID}/merge_requests/${MR_IID}")
echo "$MR_JSON" | python3 -c "
import sys, json
d = json.loads(sys.stdin.read(), strict=False)
dr = d.get('diff_refs') or {}
print('TITLE:', d.get('title'))
print('AUTHOR:', d.get('author',{}).get('name'))
print('SOURCE:', d.get('source_branch'))
print('TARGET:', d.get('target_branch'))
print('STATE:', d.get('state'))
print('BASE_SHA:', dr.get('base_sha'))
print('HEAD_SHA:', dr.get('head_sha'))
print('START_SHA:', dr.get('start_sha'))
"
```

---

## 步骤 3：获取变更文件和 diff

```bash
CHANGES_JSON=$(curl -s -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "https://git.bilibili.co/api/v4/projects/${PROJECT_ID}/merge_requests/${MR_IID}/changes")
echo "$CHANGES_JSON" | python3 -c "
import sys, json
d = json.loads(sys.stdin.read(), strict=False)
changes = d.get('changes', [])
print(f'Total: {len(changes)} files')
for c in changes:
    print(f'  {c[\"new_path\"]}')
    print(c.get('diff', ''))
"
```

---

## 步骤 4：添加总结评论

```bash
curl -s -X POST -H "PRIVATE-TOKEN: $GITLAB_TOKEN" -H 'Content-Type: application/json' \
  -d '{"body": "## Code Review 总结\n..."}' \
  "https://git.bilibili.co/api/v4/projects/${PROJECT_ID}/merge_requests/${MR_IID}/notes"
```

---

## 步骤 5：添加行内评论

从步骤 2 获取的 `diff_refs` 中提取 `base_sha`/`start_sha`/`head_sha`。

行号规则（根据 diff 中行的类型）：

| 评论目标 | old_line | new_line |
|---------|----------|----------|
| 新增行（`+`） | 不填 | 填 |
| 删除行（`-`） | 填 | 不填 |
| 上下文行（未变更） | 填 | 填 |

```bash
curl -s -X POST -H "PRIVATE-TOKEN: $GITLAB_TOKEN" -H 'Content-Type: application/json' \
  -d '{
    "body": "评论内容",
    "position": {
      "base_sha": "xxx",
      "start_sha": "xxx",
      "head_sha": "xxx",
      "position_type": "text",
      "old_path": "path/to/file",
      "new_path": "path/to/file",
      "new_line": 45
    }
  }' \
  "https://git.bilibili.co/api/v4/projects/${PROJECT_ID}/merge_requests/${MR_IID}/discussions"
```

详细参数说明见 `refs/api-reference.md`。

---

## 禁止行为

1. ❌ `curl ... | python3 -c "..."` 直接管道 — 大 JSON 传递不稳定，必须先存变量
2. ❌ `git diff origin/master..mr-branch` — 包含 master 上其他人的变更
3. ❌ `git diff $(git merge-base ...)` — 同样包含其他已合并的 MR 变更
4. ❌ `json.load(sys.stdin)` 不带 strict=False — git.bilibili.co JSON 含控制字符会报错

---

## 常见错误

### merge-base 导致 diff 范围过大

**场景**：MR 只有 1 行变更，但 review 分析了 121 个文件

**原因**：`git merge-base` 返回了很早的 commit，diff 包含了已合并的其他 MR

**正确做法**：使用 `diff_refs` 中的 SHA
```bash
VERSIONS=$(curl -s -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "https://git.bilibili.co/api/v4/projects/${PROJECT_ID}/merge_requests/${MR_IID}/versions")
echo "$VERSIONS" | python3 -c "
import sys, json; v = json.loads(sys.stdin.read(), strict=False)[0]
print('base:', v['base_commit_sha'])
print('head:', v['head_commit_sha'])
"
git diff ${BASE_SHA}..${HEAD_SHA}
```

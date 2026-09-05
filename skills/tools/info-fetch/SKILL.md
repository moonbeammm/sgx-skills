---
name: info-fetch
description: 从 info.bilibili.co (Bilibili 内部 info) 读取和写入页面内容。当用户提及获取 info 页面、读取 wiki、写入 info、更新页面时使用。
---

# info 页面读写

## 认证配置

**环境变量**: `INFO_TOKEN`

在 `~/.zshrc` 或 `~/.bashrc` 中添加：

```bash
export INFO_TOKEN="your-info-token-here"
```

配置后重新加载：
```bash
source ~/.zshrc
```

**获取 Token**：
1. 登录 [info](https://info.bilibili.co)
2. 点击右上角头像 → 「设置」
3. 进入「个人访问令牌」
4. 创建新令牌

## 读取页面

### 使用脚本

```bash
# 获取 Markdown 格式（默认）
.claude/skills/info-fetch/info_read.sh {pageId}

# 获取原始 JSON
.claude/skills/info-fetch/info_read.sh {pageId} raw
```

### 手动调用

```bash
# 获取原始内容
curl -s -H "Authorization: Bearer $INFO_TOKEN" \
  "https://info.bilibili.co/rest/api/content/{pageId}?expand=body.storage,title,space,version"

# 转换为 Markdown
curl -s -H "Authorization: Bearer $INFO_TOKEN" \
  "https://info.bilibili.co/rest/api/content/{pageId}?expand=body.storage,title" | \
  python3 .claude/skills/info-fetch/info_to_markdown.py
```

## 更新页面

### 使用脚本

```bash
# 准备内容文件 (info HTML 格式)
echo "<p>页面内容</p>" > content.html

# 更新页面
.claude/skills/info-fetch/info_update.sh {pageId} "页面标题" content.html
```

### 手动调用

```bash
# 1. 获取当前版本号
VERSION=$(curl -s -H "Authorization: Bearer $INFO_TOKEN" \
  "https://info.bilibili.co/rest/api/content/{pageId}?expand=version" | \
  python3 -c "import sys,json; print(json.load(sys.stdin)['version']['number'])")

# 2. 更新页面
curl -s -X PUT \
  -H "Authorization: Bearer $INFO_TOKEN" \
  -H "Content-Type: application/json" \
  "https://info.bilibili.co/rest/api/content/{pageId}" \
  -d '{
    "id": "{pageId}",
    "type": "page",
    "title": "页面标题",
    "version": {"number": NEW_VERSION},
    "body": {
      "storage": {
        "value": "<p>HTML 内容</p>",
        "representation": "storage"
      }
    }
  }'
```

## 创建新页面

### 使用脚本

```bash
# 准备内容文件
echo "<p>新页面内容</p>" > content.html

# 创建页面（无父页面）
.claude/skills/info-fetch/info_create.sh SPACE_KEY "页面标题" content.html

# 创建页面（指定父页面）
.claude/skills/info-fetch/info_create.sh SPACE_KEY "页面标题" content.html {parentId}
```

### 手动调用

```bash
curl -s -X POST \
  -H "Authorization: Bearer $INFO_TOKEN" \
  -H "Content-Type: application/json" \
  "https://info.bilibili.co/rest/api/content" \
  -d '{
    "type": "page",
    "title": "新页面标题",
    "space": {"key": "SPACE_KEY"},
    "ancestors": [{"id": "父页面ID"}],
    "body": {
      "storage": {
        "value": "<p>页面内容</p>",
        "representation": "storage"
      }
    }
  }'
```

## Markdown 转 Info HTML

| Markdown | Info HTML |
|----------|-----------------|
| `# 标题` | `<h1>标题</h1>` |
| `**粗体**` | `<strong>粗体</strong>` |
| `- 列表` | `<ul><li>列表</li></ul>` |
| `` `代码` `` | `<code>代码</code>` |
| `[链接](https://example.com)` | `<a href="https://example.com">链接</a>` |

### 代码块格式

```html
<ac:structured-macro ac:name="code" ac:schema-version="1">
  <ac:parameter ac:name="language">go</ac:parameter>
  <ac:plain-text-body><![CDATA[代码内容]]></ac:plain-text-body>
</ac:structured-macro>
```

## 相关脚本

| 脚本 | 用途 |
|------|------|
| [info_read.sh](info_read.sh) | 读取页面 |
| [info_update.sh](info_update.sh) | 更新页面 |
| [info_create.sh](info_create.sh) | 创建页面 |
| [info_to_markdown.py](info_to_markdown.py) | HTML 转 Markdown |

## 错误处理

| 错误码 | 说明 | 处理 |
|--------|------|------|
| 401 | Token 无效/过期 | 提示用户更新 token |
| 403 | 无写入权限 | 检查页面权限设置 |
| 404 | 页面不存在 | 检查 pageId |
| 409 | 版本冲突 | 重新获取版本号后重试 |

## 使用示例

### 读取页面

```
用户: 获取 pageId 855215107 的内容
```

### 更新页面

```
用户: 把这段内容写入到 info 页面 855215107
```

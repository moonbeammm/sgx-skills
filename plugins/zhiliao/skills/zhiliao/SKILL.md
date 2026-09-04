---
name: zhiliao
description: 知了文档平台 (aistudio.bilibili.co) 工具。读取/打开/查看、上传/管理 Markdown 文档到知了云端，增量编辑文档，语义搜索知识库。Use when the user gives an aistudio.bilibili.co document link (e.g. .../space/doc/doc_xxx or .../share/doc_xxx), or mentions 打开/读取/查看知了文档、知了、aistudio.bilibili.co、文档提交、文档上传、增量编辑、知识库搜索、zhiliao。一旦出现知了文档链接或需要读取知了文档内容，用本 skill 的脚本，不要用网页抓取(WebFetch)。
homepage: https://aistudio.bilibili.co
metadata:
  {
    'clawdbot':
      {
        'emoji': '📝',
        'requires': { 'bins': ['node'], 'env': ['ZHILIAO_API_KEY'] },
        'primaryEnv': 'ZHILIAO_API_KEY',
      },
  }
version: 1.1.2
---

# 知了文档平台 (zhiliao)

将本地 Markdown 文档上传到知了内网云端文档平台，支持文档管理和知识库语义搜索。上传的文档内容会自动同步到知识库，可通过语义搜索检索。

> **修改已有文档的首选方式是「增量编辑」（block 级，见下文）**，而不是整篇 `update` 覆盖。
> 改某段、改某节、补一段、删一块、查找替换——一律优先用 `apply-document-edit`（配合 `get-document-outline` / `get-document-blocks` 定位）。
> 只有「整篇重写 / 内容几乎全换 / 从本地文件整体覆盖上传」这类场景才用 `update-document`。
> 默认走增量编辑能最大限度保留未改动部分、不重排格式、对协同更友好。

## 使用场景

- 将本地 .md 文档或 openclaw 龙虾生成的产物文档保存到知了云端平台
- 管理云端文档（创建、查看、更新、增量编辑）
- 通过知识库语义搜索自己或团队的文档
- 使用 aclTags 搜索团队共享文档（如同一标记的团队成员文档）

## API Key 管理

API Key 优先级：**`ZHILIAO_API_KEY` 环境变量 > `{baseDir}/data/config.json` 中的 `apiKey` 字段**。

环境变量为推荐方式（外层配置，更易维护），config.json 仅作为 fallback。

### 推荐配置（环境变量）

**首选方式**：在 `~/.claude/settings.json` 中加入 `env` 配置，所有 Claude Code 会话自动注入：

```json
{
  "env": {
    "ZHILIAO_API_KEY": "aist_xxxxxxxxxxxx"
  }
}
```

配置后**重启 Claude Code 会话**才会生效（settings.json 的 env 在会话启动时读入）。

**备选方式**：在 shell 配置（如 `~/.zshrc` / `~/.bashrc`）中加入 `export ZHILIAO_API_KEY="aist_xxxxxxxxxxxx"`，然后 `source ~/.zshrc` 或重开终端。

### Fallback 配置（config.json）

也可在 `{baseDir}/data/config.json` 中配置：

```json
{
  "apiKey": "aist_xxxxxxxxxxxx",
  "baseUrl": "https://aistudio.bilibili.co/api/v1/openapi",
  "defaultSpaceId": "sp_xxx",
  "defaultFolderId": "fd_xxx"
}
```

- `apiKey`：环境变量未设置时的 fallback。注意 `aist_` 是占位符，需替换为真实 key 才会生效
- `baseUrl`：默认 `https://aistudio.bilibili.co/api/v1/openapi`
- `defaultSpaceId` / `defaultFolderId`（可选）：用户显式指定的默认上传位置，设置后上传/创建文档可省略 `--space-id` 和 `--folder-id` 参数

API Key 格式为 `aist_` 开头的字符串，请联系 aistudio.bilibili.co 平台管理员申请。

### 使用前自检（IMPORTANT）

**首次执行任何脚本前**，如果脚本报错"未配置有效的知了 API Key"或返回 401：

1. **首选引导用户**在 `~/.claude/settings.json` 的 `env` 中添加 `ZHILIAO_API_KEY`，并提示用户**配置完后需重启 Claude Code 会话**才会生效
2. **不要替用户写入 key**，让用户自己粘贴真实值
3. config.json 中的 `aist_` 占位符不必清理——环境变量优先级更高，留着无副作用
4. 如果用户已在终端设置了环境变量但本会话仍报"未配置"，提示用户：Claude Code 会话需重启才能读到新增的环境变量

## 数据缓存

已同步的空间、文件夹和文档记录在 `{baseDir}/data/documents.json` 中：

```json
{
  "spaces": {
    "sp_001": { "name": "产品团队空间", "spaceType": "team" }
  },
  "folders": {
    "fd_001": { "name": "/", "spaceId": "sp_001", "parentId": "" },
    "fd_002": { "name": "技术方案", "spaceId": "sp_001", "parentId": "" }
  },
  "documents": [
    {
      "title": "文档标题",
      "documentId": "doc_123",
      "spaceId": "sp_001",
      "folderId": "fd_001"
    }
  ]
}
```

- `spaces`: 空间元数据缓存（ID → 名称、类型）
- `folders`: 文件夹元数据缓存（ID → 名称、所属空间、父级文件夹）
- `documents`: 文档列表（扁平数组，便于标题搜索），每个文档记录 spaceId 和 folderId

此缓存在 list-spaces、list-folders、create、upload、get 等操作时自动维护。

## 工作流程

### 推荐首次使用流程

```bash
# 1. 获取可用空间列表
node {baseDir}/scripts/list-spaces.mjs

# 2. 获取目标空间下的文件夹
node {baseDir}/scripts/list-folders.mjs sp_xxx

# 3. （可选）在 config.json 中设置 defaultSpaceId/defaultFolderId

# 4. 上传文档
node {baseDir}/scripts/upload-document.mjs /path/to/doc.md
```

### 获取空间列表

```bash
node {baseDir}/scripts/list-spaces.mjs
```

返回当前 Token 可访问的空间，并缓存到 documents.json。

### 获取文件夹列表

```bash
node {baseDir}/scripts/list-folders.mjs <spaceId>
node {baseDir}/scripts/list-folders.mjs --space-id sp_xxx
```

返回指定空间下的文件夹列表，标记根目录（name 为 `/`，parentId 为 `""`），并缓存。

### 创建文件夹

在指定空间下创建文件夹：

```bash
node {baseDir}/scripts/create-folder.mjs --name "文件夹名称" --space-id sp_xxx
node {baseDir}/scripts/create-folder.mjs --name "子文件夹" --space-id sp_xxx --parent-id fd_xxx
node {baseDir}/scripts/create-folder.mjs --name "文件夹" --introduction "文件夹简介"
```

- `--name` 为必填，最长 128 字符
- `--parent-id` 可选，不传则创建在根目录下
- `--introduction` 可选，文件夹简介，最长 2000 字符
- spaceId 解析优先级：位置参数/`--space-id` > config 默认值 > 缓存唯一空间

### 获取文件夹下文档列表

获取指定文件夹下的文档列表：

```bash
node {baseDir}/scripts/list-documents.mjs fd_xxx
node {baseDir}/scripts/list-documents.mjs --folder-id fd_xxx
```

返回文档的 id、title、owner，并缓存到 documents.json。

### 上传本地文档（主要功能）

将本地 .md 文件上传到知了平台，自动判断创建或更新：

```bash
node {baseDir}/scripts/upload-document.mjs /path/to/document.md
node {baseDir}/scripts/upload-document.mjs /path/to/document.md --title "自定义标题"
node {baseDir}/scripts/upload-document.mjs /path/to/document.md --space-id sp_xxx --folder-id fd_xxx
```

- 默认标题取文件名（去掉 .md 后缀）
- 如果 documents.json 中已有同名文档，自动执行更新
- 否则创建新文档（需要 spaceId 和 folderId）
- 创建/更新成功后输出会包含文档 URL（`https://aistudio.bilibili.co/share/{documentId}`），可直接告知用户

#### 未指定空间/文件夹时的引导流程（IMPORTANT）

当用户上传文档但**未明确指定 `--space-id` 和 `--folder-id`** 时，按以下决策树处理。**禁止默默使用缓存值**——文件夹列表必须始终从 API 拉取最新，因为用户可能在平台新建了目录，缓存无法感知。

1. **检查 config.json 的 default 配置**：如果用户在 `config.json` 中显式配置了 `defaultSpaceId` / `defaultFolderId`，直接使用（这是用户已确认的偏好）
2. **没有 default → 用 AskUserQuestion 询问用户**：
   - **空间选项**：先 Read 一下 `{baseDir}/data/documents.json` 缓存中的 `spaces`，把缓存里的空间名+ID 作为选项展示给用户，并附上一个"重新拉取空间列表"选项；缓存为空时直接调用 `list-spaces.mjs` 拉取后再问
   - **文件夹选项**：用户选完空间后，**始终调用 `list-folders.mjs <spaceId>` 拉最新**，把返回结果作为候选给用户选；接口失败时才退回缓存的 folders 兜底
3. **用户主动指明位置**：若用户在请求中明确说"上传到 XX 空间的 XX 文件夹"，跳过询问，直接传 `--space-id` / `--folder-id`

**示例对话（缓存为空）**：

```
用户：帮我把这份 md 上传到知了
助手：[Read documents.json 发现缓存为空]
助手：[Bash: node scripts/list-spaces.mjs]
助手：[AskUserQuestion: 上传到哪个空间？选项：空间A / 空间B / 重新拉取]
用户：空间A
助手：[Bash: node scripts/list-folders.mjs sp_a]
助手：[AskUserQuestion: 上传到哪个文件夹？选项：根目录 / 技术方案 / ...]
用户：技术方案
助手：[Bash: node scripts/upload-document.mjs xxx.md --space-id sp_a --folder-id fd_xxx]
助手：上传成功，URL: https://aistudio.bilibili.co/share/doc_xxx
```

**示例对话（缓存非空）**：

```
用户：帮我把这份 md 上传到知了
助手：[Read documents.json 拿到 spaces 缓存]
助手：[AskUserQuestion: 上传到哪个空间？选项：空间A（缓存）/ 空间B（缓存）/ 重新拉取空间列表]
用户：空间A
助手：[Bash: node scripts/list-folders.mjs sp_a，拉最新]
助手：[AskUserQuestion: 上传到哪个文件夹？选项：根目录 / 技术方案 / 新增的文件夹 / ...]
用户：新增的文件夹
助手：[Bash: node scripts/upload-document.mjs xxx.md --space-id sp_a --folder-id fd_xxx]
```

### 创建文档

```bash
node {baseDir}/scripts/create-document.mjs --title "文档标题" --content "# Markdown 内容"
node {baseDir}/scripts/create-document.mjs --title "标题" --space-id sp_xxx --folder-id fd_xxx
```

也可通过 stdin 管道传入内容：

```bash
cat document.md | node {baseDir}/scripts/create-document.mjs --title "文档标题"
```

spaceId 和 folderId 的解析优先级：`--space-id`/`--folder-id` 参数 > config.json 默认值 > 缓存中唯一空间的根目录。

### 获取文档

通过 documentId 或标题获取文档详情：

```bash
node {baseDir}/scripts/get-document.mjs doc_xxxxxxxxxx
node {baseDir}/scripts/get-document.mjs --title "文档标题"
```

使用 `--title` 时优先查 documents.json，找不到则自动通过知识库搜索匹配。获取到的文档会自动回填空间和文件夹信息到缓存。输出会包含文档 URL（`https://aistudio.bilibili.co/share/{documentId}`），可直接告知用户。

#### 从 URL 取 documentId（IMPORTANT）

用户给的往往是**网页链接**而不是裸 id。所有脚本的 documentId 参数都只认 `doc_xxx` 形式，**需要你先从 URL 里提取**。知了文档链接里 `doc_` 开头的那一段就是 documentId，两种常见形式：

- `https://aistudio.bilibili.co/space/doc/doc_UkOSGir6qt4h1Z48U7dT` （用户访问页）
- `https://aistudio.bilibili.co/share/doc_UkOSGir6qt4h1Z48U7dT` （分享/脚本输出）

两者的 `doc_UkOSGir6qt4h1Z48U7dT` 都直接作为 documentId 传给脚本即可：

```bash
node {baseDir}/scripts/get-document.mjs doc_UkOSGir6qt4h1Z48U7dT
```

**只要用户给出知了文档链接、或说「打开/读取/看一下这篇知了文档」，就用本 skill 的脚本读取（get-document / get-document-outline / get-document-blocks），不要用 WebFetch 抓网页**——知了文档是登录后客户端渲染的，WebFetch 拿不到正文，只会得到空壳页面。

### 更新文档（整篇覆盖，非首选）

> ⚠️ **改已有文档前先想清楚：是不是只改局部？** 是 → 用下面的「增量编辑文档」，不要用 update。
> `update-document` 会用新内容**整篇覆盖**，重排所有块、丢失未改动部分的稳定性，仅用于「整篇重写 / 内容几乎全换 / 从本地 .md 整体覆盖上传」。

```bash
node {baseDir}/scripts/update-document.mjs doc_xxxxxxxxxx --title "新标题" --content "# 新内容"
node {baseDir}/scripts/update-document.mjs --title "现有标题" --content "# 更新的内容"
```

也支持 stdin 传入 content。title 为必填参数。

### 增量编辑文档（block 级，修改已有文档的首选）

对已有文档做**局部修改**（改某段、重写某节、补一段、删一块、查找替换），保留其余内容不动。只能编辑自己创建的文档。**改已有文档默认走这里，而不是 update 整篇覆盖。**

**标准工作流（改已有文档前务必照做）：**

> 🔒 **铁律：每次 apply-document-edit 之前，必须先用 get-document-blocks 拉一次最新块清单拿到 index，不能凭记忆或猜测填 anchor.index。** 哪怕你上一轮刚拉过——只要中间对文档做过任何改动，所有 index 就已失效，必须重新拉。index 错了会改错块。文档大时先用 get-document-outline 看大纲、再按 range 拉目标区间。

1. **先看大纲**——了解结构和规模，定位要改哪里：

   ```bash
   node {baseDir}/scripts/get-document-outline.mjs doc_xxxxxxxxxx
   ```

   返回标题大纲（每个标题带 `[index]` 块序号）+ 总块数 + 总字数。文档大时靠大纲定位章节，不要一次拉全文。

2. **再拉目标块的 markdown**——看清要改的块内容：

   ```bash
   node {baseDir}/scripts/get-document-blocks.mjs doc_xxxxxxxxxx --range 5-8
   node {baseDir}/scripts/get-document-blocks.mjs doc_xxxxxxxxxx          # 不带 range 拉全部
   ```

   返回每块的 `index`（序号）、`type`（类型）、`markdown`（标准 markdown 内容）。`index` 用于下一步的 `anchor.index`。

3. **提交改动**——edits 数组走 stdin（JSON），documentId 走参数（身份由 API Key 决定，无需 username）：

   ```bash
   echo '[{"action":"editText","anchor":{"index":3},"find":"旧文案","replace":"新文案"}]' \
     | node {baseDir}/scripts/apply-document-edit.mjs doc_xxxxxxxxxx
   ```

**action 枚举（按用户语义选择）：**

| action           | 用途                       | 必填字段                          |
| ---------------- | -------------------------- | --------------------------------- |
| `editText`       | 块内查找替换（块内全替换） | `anchor` + `find` + `replace`     |
| `replaceBlock`   | 替换单个块（整块重写）     | `anchor` + `content`              |
| `replaceSection` | 替换标题所辖整段章节       | `anchor`（须为标题块）+ `content` |
| `deleteBlock`    | 删除单个块                 | `anchor`                          |
| `append`         | 追加到文档末尾             | `content`                         |
| `prepend`        | 插入到文档开头             | `content`                         |
| `insertAfter`    | 在某块之后插入新块         | `anchor` + `content`              |

- `anchor`：`{ "index": N }`（块序号，来自 get-document-blocks）或 `{ "text": "块内唯一文本片段" }`
- `content`：新内容，**标准 markdown**（标题 `#`、列表 `-`/`1.`、表格 `|`，与 blocks 返回格式一致）
- 一次可提交多条 edits（数组里多个对象），按顺序应用

**action 选择 + 避坑要点：**

- 「改措辞 / 把某词全替换」→ `editText`，块内查找替换、保留其余内容，最不易误伤。注意它是**块内 replace_all**（替换该块内所有匹配），要精确只改一处时 `find` 取足够唯一的片段
- 「整节重写」→ `replaceSection`（anchor 指向该节标题块）。它替换「该标题 + 直到下一个同级或更高级标题之前」的整段，`content` **只放这一节内容，别把相邻下一节也写进去**，否则会用两节内容替换掉一节
- 「表格 / 列表 / 整段换掉」→ `replaceBlock`；**表格、列表内部要改也走整块重写**，给整块新 markdown，不要试图定位到单元格或列表项
- **index 来自「本次提交前刚拉的」blocks 快照**：同一次提交的多条 edits，anchor.index 都基于这一份快照，服务端统一处理偏移、不用手动调整；但**两次提交之间文档已变，第二次提交前必须重新拉一次 blocks**，绝不能复用上一次的 index

### 删除文档

```bash
node {baseDir}/scripts/delete-document.mjs doc_xxxxxxxxxx
node {baseDir}/scripts/delete-document.mjs --title "文档标题"
```

删除成功后自动从 documents.json 中移除记录。只能删除自己创建的文档。

### 知识库搜索

#### 通用语义搜索

```bash
node {baseDir}/scripts/search-knowledge.mjs "搜索关键词"
node {baseDir}/scripts/search-knowledge.mjs "搜索内容" --limit 5
```

默认返回 20 条结果。搜索结果中的 sourceId 对应 documentId，可通过 get-document 或 get-knowledge-source 获取完整文档内容。

#### 搜索团队共享文档（aclTags）

aclTags 类似暗号，同一标记的团队成员可搜索到彼此的文档：

```bash
node {baseDir}/scripts/search-knowledge.mjs "搜索内容" --acl "team-tag"
node {baseDir}/scripts/search-knowledge.mjs "搜索内容" --acl "live-doc,生态质量部"
```

#### 搜索指定文档内容

通过 source 和 source-id 精确搜索特定文档的内容片段：

```bash
node {baseDir}/scripts/search-knowledge.mjs "搜索内容" --source doc --source-id doc_xxxxxxxxxx
```

#### 按标签过滤

```bash
node {baseDir}/scripts/search-knowledge.mjs "搜索内容" --tags "前端,React"
```

#### 按空间 / 项目过滤

```bash
node {baseDir}/scripts/search-knowledge.mjs "搜索内容" --space-id "sp_001,sp_002"
node {baseDir}/scripts/search-knowledge.mjs "搜索内容" --project-id "prj_xxx"
```

#### 按时间过滤

传入毫秒时间戳，按创建或更新时间过滤结果：

```bash
node {baseDir}/scripts/search-knowledge.mjs "搜索内容" --ctime-start 1704067200000 --ctime-end 1706745600000
node {baseDir}/scripts/search-knowledge.mjs "搜索内容" --mtime-start 1704067200000
```

### 获取知识库条目详情

搜索结果返回的是 chunk（文档片段），如需完整正文，可通过 get-knowledge-source.mjs 按 source + sourceId 获取：

```bash
node {baseDir}/scripts/get-knowledge-source.mjs --source doc --source-id doc_xxxxxxxxxx
node {baseDir}/scripts/get-knowledge-source.mjs doc doc_xxxxxxxxxx
```

- `source` 可选值：`doc`、`baike`、`info`、`codewiki`
- 对于 `source=doc` 类型的知了文档，也可直接使用 get-document.mjs（支持缓存回填）

## 注意事项

- 文档上传后知识库同步为异步处理（embedding 队列），搜索结果可能有几秒延迟
- 文档 URL 格式为 `https://aistudio.bilibili.co/share/{documentId}`，create / update / get / upload 脚本输出都会包含
- 脚本使用 Node 内置 fetch（要求 Node 18+）发送请求，markdown 内容通过 JSON.stringify 自动正确编码，无需担心换行/引号/反引号等特殊字符
- documents.json 在各操作时自动维护，缓存空间、文件夹和文档映射；但**缓存可能滞后于平台**（用户在网页新建的目录缓存不可见），上传引导时文件夹列表始终调 `list-folders.mjs` 拉最新
- 当 documents.json 中找不到目标文档时，get-document 和 update-document 会自动 fallback 到知识库搜索
- **修改已有文档优先用增量编辑（apply-document-edit），而非 update 整篇覆盖**；只有整篇重写/整体覆盖才用 update
- **增量编辑报「当前文档内容无法执行变更或变更操作无效」时**：这通常**不是**你的 anchor/操作写错，而是文档里含编辑器特有节点（任务列表 taskList/taskItem、@提及 mention、附件/视频/嵌入块等），服务端解析现有文档内容时不支持该节点类型而整体失败——与你提交什么操作、改哪个位置无关。判断依据：若**任何** action（包括最简单的 append）对该文档都失败、但对不含这类节点的新文档却成功，即属此类。此时增量编辑无法使用，可改用 `update-document` 整篇覆盖（但会重排格式、且可能丢失 taskList 等节点，需谨慎并提醒用户），或反馈给平台维护方修复服务端节点支持，不要反复重试不同 anchor
- 文档可见与编辑权限由文档自身的访问模式决定（公开可编辑 / 公开只读 / 白名单）；白名单文档需先有访问记录，只读文档不能编辑
- 创建文档必须指定 spaceId 和 folderId，如需在根目录创建，使用文件夹列表中 name 为 `/` 且 parentId 为空字符串的文件夹

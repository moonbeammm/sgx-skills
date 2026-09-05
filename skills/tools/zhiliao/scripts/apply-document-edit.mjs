import { apiRequest, findDocumentByTitle, parseArgs, getDocumentUrl } from './utils.mjs';

// 对已有文档做 block 级增量编辑：documentId 走参数，edits 数组走 stdin（JSON）。
// 身份由 API Key 对应用户决定（仅文档所有者可编辑），无需传 username。
//
// edits 每条 = { action, anchor?, content?, find?, replace? }
//   append          追加到文档末尾。需 content（markdown）
//   prepend         插入到文档开头。需 content
//   insertAfter     在某块之后插入。需 anchor + content
//   replaceBlock    替换单个块。需 anchor + content（整块新内容）
//   replaceSection  替换标题所辖整段章节。anchor 必须是标题块，需 content（只放该节内容）
//   editText        块内查找替换（块内 replace_all，保留其余内容）。需 anchor + find + replace
//   deleteBlock     删除单个块。需 anchor
// anchor: { index: 块序号 }（来自 get-document-blocks）或 { text: "块内唯一文本片段" }

const args = parseArgs(process.argv);
let documentId = args._[0];

if (!documentId && args.title) {
  const doc = findDocumentByTitle(args.title);
  if (doc) documentId = doc.documentId;
}

if (!documentId) {
  console.error('用法: echo \'[{"action":"editText","anchor":{"index":3},"find":"旧","replace":"新"}]\' \\');
  console.error('        | node apply-document-edit.mjs <documentId>');
  console.error('      （也可用 --title "标题" 代替 documentId）');
  console.error('\nedits 数组通过 stdin 以 JSON 传入；只能编辑自己创建的文档');
  process.exit(1);
}

if (process.stdin.isTTY) {
  console.error('错误: edits 需通过 stdin 传入 JSON 数组，例如：');
  console.error('  echo \'[{"action":"append","content":"# 新章节"}]\' | node apply-document-edit.mjs doc_xxx');
  process.exit(1);
}

const raw = await new Promise((resolve) => {
  let d = '';
  process.stdin.setEncoding('utf-8');
  process.stdin.on('data', (chunk) => (d += chunk));
  process.stdin.on('end', () => resolve(d));
});

let edits;
try {
  edits = JSON.parse(raw);
} catch (err) {
  console.error(`错误: edits 不是合法 JSON：${err.message}`);
  process.exit(1);
}

if (!Array.isArray(edits) || edits.length === 0) {
  console.error('错误: edits 必须是非空数组');
  process.exit(1);
}

await apiRequest('POST', `/document/${documentId}/apply-edit`, { edits });

console.log(`增量编辑成功，共应用 ${edits.length} 条改动`);
console.log(`文档ID: ${documentId}`);
console.log(`URL:    ${getDocumentUrl(documentId)}`);
console.log(`\n提示：可用 get-document-blocks ${documentId} 查看修改后的内容`);

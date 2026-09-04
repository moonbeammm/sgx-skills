import { apiRequest, findDocumentByTitle, parseArgs } from './utils.mjs';

// 获取文档大纲（标题层级 + 规模），用于增量编辑前先看结构、定位要改的章节。
// 大文档建议先跑这个，再用 get-document-blocks --range 拉目标区间。

const args = parseArgs(process.argv);
let documentId = args._[0];

if (!documentId && args.title) {
  const doc = findDocumentByTitle(args.title);
  if (doc) documentId = doc.documentId;
}

if (!documentId) {
  console.error('用法: node get-document-outline.mjs <documentId>');
  console.error('      node get-document-outline.mjs --title "标题"');
  console.error('\n返回文档大纲（标题 outline）+ 规模（块数 / markdown 全文字数）');
  process.exit(1);
}

const data = await apiRequest('GET', `/document/${documentId}/blocks-outline`);

console.log(`标题:    ${data.title}`);
console.log(`文档ID:  ${data.documentId}`);
console.log(`总块数:  ${data.totalBlocks}`);
console.log(`总字数:  ${data.totalChars}（markdown 全文长度，用于判断是否需要分段拉取）`);
console.log(`\n--- 大纲（index 为块序号，用于 get-document-blocks --range 或 apply-document-edit 的 anchor）---\n`);

if (!data.outline || data.outline.length === 0) {
  console.log('(无标题，文档可能是纯段落；用 get-document-blocks 查看全部块)');
} else {
  for (const h of data.outline) {
    const level = h.level || 1;
    console.log(`[${h.index}] ${'  '.repeat(level - 1)}${'#'.repeat(level)} ${h.text}`);
  }
}

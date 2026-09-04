import { apiRequest, findDocumentByTitle, parseArgs } from './utils.mjs';

// 获取文档块清单（每块 index/type/markdown），用于阅读具体内容并决定如何增量修改。
// 大文档建议先用 get-document-outline 看大纲，再用 --range 拉目标区间，避免一次拉太多。

const args = parseArgs(process.argv);
let documentId = args._[0];
const range = args.range; // 形如 "5-8"

if (!documentId && args.title) {
  const doc = findDocumentByTitle(args.title);
  if (doc) documentId = doc.documentId;
}

if (!documentId) {
  console.error('用法: node get-document-blocks.mjs <documentId> [--range 5-8]');
  console.error('      node get-document-blocks.mjs --title "标题" [--range 5-8]');
  console.error('\n返回块清单：每块的 index（序号）、type（类型）、markdown（标准 markdown 内容）');
  console.error('不带 --range 返回全部块；--range 5-8 只返回 index 5~8 的块');
  process.exit(1);
}

const path = range
  ? `/document/${documentId}/blocks?range=${encodeURIComponent(range)}`
  : `/document/${documentId}/blocks`;

const data = await apiRequest('GET', path);

console.log(`标题:    ${data.title}`);
console.log(`文档ID:  ${data.documentId}`);
console.log(`块数:    ${data.blocks.length}${range ? `（range=${range}）` : '（全部）'}`);
console.log(`\n--- 块清单（index 用于 apply-document-edit 的 anchor.index）---\n`);

for (const b of data.blocks) {
  const levelTag = b.level ? ` L${b.level}` : '';
  console.log(`### [${b.index}] ${b.type}${levelTag}`);
  console.log(b.markdown || '(空)');
  console.log('');
}

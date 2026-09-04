import { apiRequest, findDocumentByTitle, loadData, saveData, parseArgs } from './utils.mjs';

const args = parseArgs(process.argv);
let documentId = args._[0];

// 通过 title 查找 documentId
if (!documentId && args.title) {
  const doc = findDocumentByTitle(args.title);
  if (doc) {
    documentId = doc.documentId;
    console.log(`从 documents.json 找到: ${doc.title} -> ${doc.documentId}\n`);
  } else {
    console.error(`错误: 未在 documents.json 中找到 "${args.title}"`);
    process.exit(1);
  }
}

if (!documentId) {
  console.error('用法: node delete-document.mjs <documentId>');
  console.error('      node delete-document.mjs --title "文档标题"');
  process.exit(1);
}

await apiRequest('POST', '/document/delete', { documentId });

// 从 documents.json 中移除
const data = loadData();
data.documents = data.documents.filter(d => d.documentId !== documentId);
saveData(data);

console.log(`文档已删除: ${documentId}`);
console.log(`已从 documents.json 中移除`);

import { apiRequest, findDocumentByTitle, loadData, saveData, upsertDocument, parseArgs, getDocumentUrl } from './utils.mjs';

const args = parseArgs(process.argv);
let documentId = args._[0];
let title = args.title;

// 通过 title 查找 documentId
if (!documentId && title) {
  const doc = findDocumentByTitle(title);
  if (doc) {
    documentId = doc.documentId;
    console.log(`从 documents.json 找到: ${doc.title} -> ${doc.documentId}\n`);
    if (!title || title === doc.title) title = doc.title;
  } else {
    // fallback search
    console.log(`documents.json 中未找到 "${title}"，尝试知识库搜索...\n`);
    const searchResult = await apiRequest('POST', '/knowledge/search', {
      query: title,
      limit: 3,
      source: ['doc'],
    });
    if (searchResult?.results?.length > 0) {
      const match = searchResult.results[0];
      documentId = match.sourceId;
      console.log(`搜索匹配: "${match.title}" (score: ${match.score}) -> sourceId: ${match.sourceId}\n`);
    }
  }
}

if (!documentId || !title) {
  console.error('用法: node update-document.mjs <documentId> --title "标题" [--content "内容"]');
  console.error('      node update-document.mjs --title "标题" [--content "新内容"]');
  console.error('\ntitle 为必填参数');
  process.exit(1);
}

// content 优先参数，否则尝试 stdin
let content = args.content;
if (content === undefined && !process.stdin.isTTY) {
  content = await new Promise((resolve) => {
    let d = '';
    process.stdin.setEncoding('utf-8');
    process.stdin.on('data', (chunk) => d += chunk);
    process.stdin.on('end', () => resolve(d));
  });
}

const body = { documentId, title };
if (content !== undefined) body.content = content;

const result = await apiRequest('POST', '/document/update', body);

// 更新 documents.json，保留已有的 spaceId/folderId
const data = loadData();
const existing = data.documents.find(d => d.documentId === documentId);
upsertDocument(data, {
  title: result.title,
  documentId: result.id,
  spaceId: existing?.spaceId,
  folderId: existing?.folderId,
});
saveData(data);

console.log(`文档更新成功`);
console.log(`  ID:    ${result.id}`);
console.log(`  标题:  ${result.title}`);
console.log(`  更新:  ${result.mtime}`);
console.log(`  URL:   ${getDocumentUrl(result.id)}`);

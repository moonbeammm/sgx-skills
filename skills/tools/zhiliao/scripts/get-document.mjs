import { apiRequest, findDocumentByTitle, loadData, saveData, upsertDocument, upsertFolder, parseArgs, getDocumentUrl } from './utils.mjs';

const args = parseArgs(process.argv);
let documentId = args._[0];

if (!documentId && args.title) {
  const doc = findDocumentByTitle(args.title);
  if (doc) {
    documentId = doc.documentId;
    console.log(`从 documents.json 找到: ${doc.title} -> ${doc.documentId}\n`);
  } else {
    // fallback: 用 knowledge search 查找
    console.log(`documents.json 中未找到 "${args.title}"，尝试知识库搜索...\n`);
    const searchResult = await apiRequest('POST', '/knowledge/search', {
      query: args.title,
      limit: 3,
      source: ['doc'],
    });
    if (searchResult && searchResult.results && searchResult.results.length > 0) {
      const match = searchResult.results[0];
      documentId = match.sourceId;
      console.log(`搜索匹配: "${match.title}" (score: ${match.score}) -> sourceId: ${match.sourceId}\n`);
    } else {
      console.error('错误: 未找到匹配的文档');
      process.exit(1);
    }
  }
}

if (!documentId) {
  console.error('用法: node get-document.mjs <documentId>');
  console.error('      node get-document.mjs --title "标题"');
  process.exit(1);
}

const result = await apiRequest('GET', `/document/${documentId}`);

// 回填缓存：将 folder 信息更新到 documents.json
if (result.folder) {
  const data = loadData();
  upsertFolder(data, result.folder.folderId, {
    name: result.folder.name,
    spaceId: result.folder.spaceId,
    parentId: null,
  });
  upsertDocument(data, {
    title: result.title,
    documentId: result.id,
    spaceId: result.folder.spaceId,
    folderId: result.folder.folderId,
  });
  saveData(data);
}

console.log(`标题:    ${result.title}`);
console.log(`ID:      ${result.id}`);
console.log(`URL:     ${getDocumentUrl(result.id)}`);
console.log(`作者:    ${result.owner}`);
if (result.folder) {
  console.log(`空间:    ${result.folder.spaceId}`);
  console.log(`文件夹:  ${result.folder.name} (${result.folder.folderId})`);
}
console.log(`创建:    ${result.ctime}`);
console.log(`更新:    ${result.mtime}`);
console.log(`\n--- 正文 ---\n`);
console.log(result.markdown || result.content || '(空)');

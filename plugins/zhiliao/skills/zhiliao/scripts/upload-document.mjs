import { readFileSync } from 'fs';
import { basename } from 'path';
import { apiRequest, findDocumentByTitle, loadData, saveData, upsertDocument, resolveSpaceAndFolder, parseArgs, getDocumentUrl } from './utils.mjs';

const args = parseArgs(process.argv);
const filePath = args._[0];

if (!filePath) {
  console.error('用法: node upload-document.mjs <本地md文件路径> [--title "自定义标题"] [--space-id sp_xxx] [--folder-id fd_xxx]');
  process.exit(1);
}

let content;
try {
  content = readFileSync(filePath, 'utf-8');
} catch (err) {
  console.error(`读取文件失败: ${err.message}`);
  process.exit(1);
}

const title = args.title || basename(filePath).replace(/\.md$/i, '');
const existing = findDocumentByTitle(title);

if (existing) {
  // 更新已有文档
  console.log(`找到已有文档: ${existing.title} (${existing.documentId})，执行更新...\n`);
  const result = await apiRequest('POST', '/document/update', {
    documentId: existing.documentId,
    title,
    content,
  });

  const data = loadData();
  upsertDocument(data, {
    title: result.title,
    documentId: result.id,
    spaceId: existing.spaceId,
    folderId: existing.folderId,
  });
  saveData(data);

  console.log(`文档更新成功`);
  console.log(`  ID:    ${result.id}`);
  console.log(`  标题:  ${result.title}`);
  console.log(`  更新:  ${result.mtime}`);
  console.log(`  URL:   ${getDocumentUrl(result.id)}`);
} else {
  // 创建新文档
  console.log(`未找到同名文档，创建新文档...\n`);
  const { spaceId, folderId } = await resolveSpaceAndFolder(args);

  const result = await apiRequest('POST', '/document/create', {
    title,
    content,
    type: 'markdown',
    spaceId,
    folderId,
  });

  const data = loadData();
  upsertDocument(data, { title: result.title, documentId: result.id, spaceId, folderId });
  saveData(data);

  console.log(`文档创建成功`);
  console.log(`  ID:      ${result.id}`);
  console.log(`  标题:    ${result.title}`);
  console.log(`  作者:    ${result.owner}`);
  console.log(`  空间:    ${spaceId}`);
  console.log(`  文件夹:  ${folderId}`);
  console.log(`  创建:    ${result.ctime}`);
  console.log(`  URL:     ${getDocumentUrl(result.id)}`);
}

console.log(`\n知识库同步为异步处理，搜索结果可能有几秒延迟`);

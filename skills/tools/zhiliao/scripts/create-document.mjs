import { apiRequest, loadData, saveData, upsertDocument, resolveSpaceAndFolder, parseArgs, getDocumentUrl } from './utils.mjs';

const args = parseArgs(process.argv);
const title = args.title;

if (!title) {
  console.error('用法: node create-document.mjs --title "标题" [--content "内容"] [--space-id sp_xxx] [--folder-id fd_xxx]');
  console.error('也可通过 stdin 管道传入 content');
  process.exit(1);
}

// content 优先从参数取，否则尝试读 stdin
let content = args.content || '';
if (!content && !process.stdin.isTTY) {
  content = await new Promise((resolve) => {
    let data = '';
    process.stdin.setEncoding('utf-8');
    process.stdin.on('data', (chunk) => data += chunk);
    process.stdin.on('end', () => resolve(data));
  });
}

const { spaceId, folderId } = await resolveSpaceAndFolder(args);

const result = await apiRequest('POST', '/document/create', {
  title,
  content,
  type: 'markdown',
  spaceId,
  folderId,
});

// 保存到 documents.json
const data = loadData();
upsertDocument(data, { title: result.title, documentId: result.id, spaceId, folderId });
saveData(data);

console.log(`\n文档创建成功`);
console.log(`  ID:      ${result.id}`);
console.log(`  标题:    ${result.title}`);
console.log(`  作者:    ${result.owner}`);
console.log(`  空间:    ${spaceId}`);
console.log(`  文件夹:  ${folderId}`);
console.log(`  创建:    ${result.ctime}`);
console.log(`  URL:     ${getDocumentUrl(result.id)}`);
console.log(`\n已保存到 documents.json`);

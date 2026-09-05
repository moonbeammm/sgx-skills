import { apiRequest, loadData, saveData, upsertFolder, parseArgs } from './utils.mjs';

const args = parseArgs(process.argv);
const spaceId = args._[0] || args['space-id'];

if (!spaceId) {
  console.error('用法: node list-folders.mjs <spaceId>');
  console.error('      node list-folders.mjs --space-id <spaceId>');
  console.error('\n请先运行 list-spaces.mjs 获取可用空间 ID');
  process.exit(1);
}

const folders = await apiRequest('GET', `/space/${spaceId}/folders`);
const data = loadData();

for (const f of folders) {
  upsertFolder(data, f.id, { name: f.name, spaceId: f.spaceId, parentId: f.parentId });
}
saveData(data);

console.log(`空间 ${spaceId} 下共 ${folders.length} 个文件夹:\n`);
for (const f of folders) {
  const isRoot = f.name === '/' && (f.parentId === '' || f.parentId == null);
  const parent = f.parentId ? ` (parent: ${f.parentId})` : '';
  console.log(`  ${f.id}  ${f.name}${isRoot ? '  [根目录]' : ''}${parent}`);
}
console.log(`\n已缓存到 documents.json`);

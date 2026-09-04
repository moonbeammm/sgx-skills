import { apiRequest, loadData, saveData, upsertSpace, parseArgs } from './utils.mjs';

parseArgs(process.argv); // 暂无参数，保留扩展性

const spaces = await apiRequest('GET', '/spaces');
const data = loadData();

for (const s of spaces) {
  upsertSpace(data, s.id, { name: s.name, spaceType: s.spaceType });
}
saveData(data);

console.log(`共 ${spaces.length} 个可访问空间:\n`);
for (const s of spaces) {
  console.log(`  ${s.id}  ${s.name}  (${s.spaceType})`);
}
console.log(`\n已缓存到 documents.json`);

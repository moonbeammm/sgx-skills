import { apiRequest, loadConfig, loadData, saveData, upsertFolder, parseArgs } from './utils.mjs';

const args = parseArgs(process.argv);
const name = args.name;

if (!name) {
  console.error('用法: node create-folder.mjs --name "文件夹名称" [--space-id sp_xxx] [--parent-id fd_xxx] [--introduction "简介"]');
  process.exit(1);
}

// 解析 spaceId：参数 > config 默认值 > 缓存唯一空间
const config = loadConfig();
const data = loadData();
let spaceId = args._[0] || args['space-id'] || config.defaultSpaceId;

if (!spaceId) {
  const spaceIds = Object.keys(data.spaces);
  if (spaceIds.length === 1) {
    spaceId = spaceIds[0];
    console.log(`自动选择唯一空间: ${data.spaces[spaceId].name} (${spaceId})`);
  } else if (spaceIds.length > 1) {
    console.error('错误: 存在多个空间，请通过 --space-id 指定，或在 config.json 中设置 defaultSpaceId');
    console.error('可用空间:');
    for (const sid of spaceIds) {
      console.error(`  ${sid}: ${data.spaces[sid].name}`);
    }
    process.exit(1);
  } else {
    console.error('错误: 未找到可用空间。请先运行 list-spaces.mjs 获取空间列表，或通过 --space-id 指定');
    process.exit(1);
  }
}

const body = { name };
if (args['parent-id']) body.parentId = args['parent-id'];
if (args.introduction) body.introduction = args.introduction;

const result = await apiRequest('POST', `/space/${spaceId}/create-folder`, body);

upsertFolder(data, result.id, { name: result.name, spaceId: result.spaceId || spaceId, parentId: result.parentId });
saveData(data);

console.log(`\n文件夹创建成功`);
console.log(`  ID:      ${result.id}`);
console.log(`  名称:    ${result.name}`);
console.log(`  空间:    ${result.spaceId || spaceId}`);
if (result.parentId) console.log(`  父级:    ${result.parentId}`);
console.log(`\n已缓存到 documents.json`);

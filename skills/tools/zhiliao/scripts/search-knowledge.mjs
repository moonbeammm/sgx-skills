import { apiRequest, parseArgs } from './utils.mjs';

const args = parseArgs(process.argv);
const query = args._[0];

if (!query) {
  console.error('用法: node search-knowledge.mjs "搜索内容" [选项]');
  console.error('');
  console.error('选项:');
  console.error('  --limit N              返回结果数量上限 (默认 20)');
  console.error('  --acl "tag1,tag2"      权限标记，搜索团队共享文档');
  console.error('  --project-id id        按项目 ID 过滤');
  console.error('  --space-id "s1,s2"     按空间 ID 过滤');
  console.error('  --source "doc,baike"   按来源过滤');
  console.error('  --source-id "id1,id2"  按来源 ID 过滤');
  console.error('  --tags "t1,t2"         按业务标签过滤');
  console.error('  --ctime-start ms       创建时间起点（毫秒时间戳）');
  console.error('  --ctime-end ms         创建时间终点（毫秒时间戳）');
  console.error('  --mtime-start ms       更新时间起点（毫秒时间戳）');
  console.error('  --mtime-end ms         更新时间终点（毫秒时间戳）');
  process.exit(1);
}

const body = { query, limit: args.limit ? parseInt(args.limit, 10) : 20 };

if (args.acl) body.aclTags = args.acl.split(',').map(s => s.trim());
if (args['project-id']) body.projectId = args['project-id'];
if (args['space-id']) body.spaceId = args['space-id'].split(',').map(s => s.trim());
if (args.source) body.source = args.source.split(',').map(s => s.trim());
if (args['source-id']) body.sourceId = args['source-id'].split(',').map(s => s.trim());
if (args.tags) body.tags = args.tags.split(',').map(s => s.trim());
if (args['ctime-start']) body.ctimeStart = parseInt(args['ctime-start'], 10);
if (args['ctime-end']) body.ctimeEnd = parseInt(args['ctime-end'], 10);
if (args['mtime-start']) body.mtimeStart = parseInt(args['mtime-start'], 10);
if (args['mtime-end']) body.mtimeEnd = parseInt(args['mtime-end'], 10);

const data = await apiRequest('POST', '/knowledge/search', body);

console.log(`搜索: "${data.query}"\n匹配: ${data.total} 条结果\n`);

if (!data.results || data.results.length === 0) {
  console.log('未找到匹配的文档');
  process.exit(0);
}

for (const r of data.results) {
  console.log(`---`);
  console.log(`标题:    ${r.title}`);
  console.log(`ID:      ${r.id}`);
  console.log(`相关度:  ${r.score}`);
  console.log(`来源:    ${r.source} | sourceId: ${r.sourceId}${r.chunkIndex != null ? ` | chunkIndex: ${r.chunkIndex}` : ''}`);
  if (r.username) console.log(`作者:    ${r.username}`);
  if (r.spaceId) console.log(`空间:    ${r.spaceId}`);
  if (r.projectId) console.log(`项目:    ${r.projectId}`);
  if (r.tags?.length) console.log(`标签:    ${r.tags.join(', ')}`);
  if (r.ctime) console.log(`创建:    ${r.ctime}`);
  if (r.mtime) console.log(`更新:    ${r.mtime}`);
  if (r.url) console.log(`链接:    ${r.url}`);
  console.log(`片段:`);
  console.log(r.chunk || '');
  console.log('');
}

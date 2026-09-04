import { apiRequest, parseArgs } from './utils.mjs';

const args = parseArgs(process.argv);

const VALID_SOURCES = ['doc', 'baike', 'info', 'codewiki'];

let source = args.source;
let sourceId = args['source-id'] || args._[1];

if (!source && args._[0] && VALID_SOURCES.includes(args._[0])) {
  source = args._[0];
}

if (!source || !sourceId) {
  console.error('用法: node get-knowledge-source.mjs --source <source> --source-id <id>');
  console.error('      node get-knowledge-source.mjs <source> <sourceId>');
  console.error('');
  console.error(`source 可选值: ${VALID_SOURCES.join(', ')}`);
  process.exit(1);
}

if (!VALID_SOURCES.includes(source)) {
  console.error(`错误: source 必须是 ${VALID_SOURCES.join(', ')} 之一`);
  process.exit(1);
}

const data = await apiRequest('POST', '/knowledge/source', { source, sourceId });

console.log(`标题:    ${data.title}`);
console.log(`来源:    ${data.source} | sourceId: ${data.sourceId}`);
if (data.username) console.log(`作者:    ${data.username}`);
if (data.ctime) console.log(`创建:    ${data.ctime}`);
if (data.mtime) console.log(`更新:    ${data.mtime}`);
if (data.url) console.log(`链接:    ${data.url}`);
console.log(`\n--- 正文 ---\n`);
console.log(data.content || '(空)');

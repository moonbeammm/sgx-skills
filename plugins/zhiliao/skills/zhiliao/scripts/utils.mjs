import { readFileSync, writeFileSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
export const DATA_DIR = join(__dirname, '..', 'data');
export const CONFIG_PATH = join(DATA_DIR, 'config.json');
export const DOCUMENTS_PATH = join(DATA_DIR, 'documents.json');

const DEFAULT_BASE_URL = 'https://aistudio.bilibili.co/api/v1/openapi';
const WEB_BASE_URL = 'https://aistudio.bilibili.co';

const isPlaceholderKey = (k) =>
  !k || typeof k !== 'string' || k === 'aist_' || /^aist_x+$/i.test(k) || k.length < 12;

let configHintShown = false;

export function getDocumentUrl(documentId) {
  return `${WEB_BASE_URL}/share/${documentId}`;
}

export function loadConfig() {
  let config = {};
  try {
    config = JSON.parse(readFileSync(CONFIG_PATH, 'utf-8'));
  } catch {}

  const envKey = process.env.ZHILIAO_API_KEY;
  const fileKey = config.apiKey;
  let apiKey = null;
  let source = null;

  if (!isPlaceholderKey(envKey)) {
    apiKey = envKey;
    source = 'env';
  } else if (!isPlaceholderKey(fileKey)) {
    apiKey = fileKey;
    source = 'config';
  }

  if (!apiKey) {
    console.error(
      '错误: 未配置有效的知了 API Key（ZHILIAO_API_KEY 环境变量与 config.json 均缺失或为占位符）',
    );
    console.error('');
    console.error('请按以下任一方式配置（首选环境变量）：');
    console.error('');
    console.error(
      '【首选】在 ~/.claude/settings.json 中加入 env 配置（适用于所有 Claude Code 会话）：',
    );
    console.error('  {');
    console.error('    "env": {');
    console.error('      "ZHILIAO_API_KEY": "aist_xxxxxxxxxxxx"');
    console.error('    }');
    console.error('  }');
    console.error('  配置后需重启 Claude Code 会话才会生效');
    console.error('');
    console.error('【备选 1】在 shell 配置（如 ~/.zshrc / ~/.bashrc）中加入：');
    console.error('  export ZHILIAO_API_KEY="aist_xxxxxxxxxxxx"');
    console.error('  配置后执行 source ~/.zshrc 或重开终端');
    console.error('');
    console.error(`【备选 2】编辑 ${CONFIG_PATH}`);
    console.error('  把 apiKey 字段改为真实值（aist_ 开头的字符串）');
    console.error('');
    console.error('如何申请：联系 aistudio.bilibili.co 平台管理员获取 API Key');
    process.exit(1);
  }

  if (source === 'config' && !configHintShown) {
    console.error(
      '提示: 当前从 config.json 读取 API Key，建议改用环境变量 ZHILIAO_API_KEY 以方便跨项目管理（推荐写入 ~/.claude/settings.json 的 env）',
    );
    configHintShown = true;
  }

  return {
    apiKey,
    baseUrl: config.baseUrl || DEFAULT_BASE_URL,
    defaultSpaceId: config.defaultSpaceId || null,
    defaultFolderId: config.defaultFolderId || null,
  };
}

export async function apiRequest(method, path, body) {
  const config = loadConfig();
  const url = config.baseUrl + path;

  const init = {
    method,
    headers: {
      Authorization: `Bearer ${config.apiKey}`,
      'Content-Type': 'application/json; charset=utf-8',
    },
  };
  if (body && method !== 'GET') {
    init.body = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(url, init);
  } catch (err) {
    console.error(`网络错误: ${err.message}`);
    process.exit(1);
  }

  const raw = await response.text();
  let json;
  try {
    json = JSON.parse(raw);
  } catch {
    console.error(`响应解析失败 (HTTP ${response.status}): ${raw.slice(0, 500)}`);
    process.exit(1);
  }

  if (json.code === 401 || response.status === 401) {
    console.error('错误: API Key 无效或已过期');
    console.error(
      '请检查 ZHILIAO_API_KEY 环境变量（推荐在 ~/.claude/settings.json 的 env 中配置），或更新 data/config.json 中的 apiKey',
    );
    process.exit(1);
  }
  if (json.code === 403) {
    console.error(`错误: ${json.message || '无权限，请检查请求参数是否正确'} (${method} ${path})`);
    process.exit(1);
  }
  if (json.code === 404) {
    console.error(`错误: ${json.message || '资源不存在'} (${method} ${path})`);
    if (body) {
      const ids = ['spaceId', 'folderId', 'documentId']
        .filter((k) => body[k])
        .map((k) => `${k}=${body[k]}`)
        .join(', ');
      if (ids) console.error(`  请求中的 ID: ${ids}`);
    }
    console.error('可能原因: 空间/文件夹/文档已被删除或迁移；或当前 API Key 无权访问');
    process.exit(1);
  }
  if (json.code === 400) {
    console.error(`参数错误: ${json.message || '请检查请求参数'} (${method} ${path})`);
    if (body) {
      const ids = ['spaceId', 'folderId', 'documentId']
        .filter((k) => body[k])
        .map((k) => `${k}=${body[k]}`)
        .join(', ');
      if (ids) console.error(`  请求中的 ID: ${ids}`);
    }
    process.exit(1);
  }
  if (json.code !== 0) {
    console.error(
      `请求失败 (code=${json.code}, HTTP ${response.status}): ${json.message || '未知错误'}`,
    );
    process.exit(1);
  }

  return json.data;
}

export function loadData() {
  let raw;
  try {
    raw = JSON.parse(readFileSync(DOCUMENTS_PATH, 'utf-8'));
  } catch {
    raw = [];
  }
  if (Array.isArray(raw)) {
    const migrated = { spaces: {}, folders: {}, documents: raw };
    saveData(migrated);
    return migrated;
  }
  return {
    spaces: raw.spaces || {},
    folders: raw.folders || {},
    documents: raw.documents || [],
  };
}

export function saveData(data) {
  writeFileSync(DOCUMENTS_PATH, JSON.stringify(data, null, 2) + '\n', 'utf-8');
}

export function loadDocuments() {
  return loadData().documents;
}

export function saveDocuments(docs) {
  const data = loadData();
  data.documents = docs;
  saveData(data);
}

export function findDocumentByTitle(title) {
  const docs = loadDocuments();
  const exact = docs.find((d) => d.title === title);
  if (exact) return exact;
  const lower = title.toLowerCase();
  return docs.find((d) => d.title.toLowerCase().includes(lower)) || null;
}

export function upsertSpace(data, id, info) {
  data.spaces[id] = { ...data.spaces[id], ...info };
}

export function upsertFolder(data, id, info) {
  data.folders[id] = { ...data.folders[id], ...info };
}

export function upsertDocument(data, doc) {
  const idx = data.documents.findIndex((d) => d.documentId === doc.documentId);
  if (idx >= 0) {
    data.documents[idx] = { ...data.documents[idx], ...doc };
  } else {
    data.documents.push(doc);
  }
}

export function findRootFolder(data, spaceId) {
  for (const [id, folder] of Object.entries(data.folders)) {
    if (
      folder.spaceId === spaceId &&
      folder.name === '/' &&
      (folder.parentId === '' || folder.parentId == null)
    ) {
      return { id, ...folder };
    }
  }
  return null;
}

/**
 * 解析 spaceId 和 folderId：命令行参数 > config 默认值 > 缓存自动选取
 * 如果 folderId 仍未确定，自动查找根目录（先查缓存，缓存没有则调 API 获取）
 */
export async function resolveSpaceAndFolder(args) {
  const config = loadConfig();
  const data = loadData();

  let spaceId = args['space-id'] || config.defaultSpaceId;
  let folderId = args['folder-id'] || config.defaultFolderId;

  if (!spaceId) {
    const spaceIds = Object.keys(data.spaces);
    if (spaceIds.length === 1) {
      spaceId = spaceIds[0];
      console.log(`自动选择唯一空间: ${data.spaces[spaceId].name} (${spaceId})`);
    } else if (spaceIds.length > 1) {
      console.error(
        '错误: 存在多个空间，请通过 --space-id 指定，或在 config.json 中设置 defaultSpaceId',
      );
      console.error('可用空间:');
      for (const sid of spaceIds) {
        console.error(`  ${sid}: ${data.spaces[sid].name}`);
      }
      process.exit(1);
    } else {
      console.error(
        '错误: 未找到可用空间。请先运行 list-spaces.mjs 获取空间列表，或通过 --space-id 指定',
      );
      process.exit(1);
    }
  }

  if (!folderId) {
    let root = findRootFolder(data, spaceId);
    if (!root) {
      console.log(`缓存中未找到根目录，从 API 获取文件夹列表...`);
      const folders = await apiRequest('GET', `/space/${spaceId}/folders`);
      for (const f of folders) {
        upsertFolder(data, f.id, {
          name: f.name,
          spaceId: f.spaceId,
          parentId: f.parentId,
        });
      }
      saveData(data);
      root = findRootFolder(data, spaceId);
    }
    if (root) {
      folderId = root.id;
      console.log(`自动选择根目录: ${root.name} (${folderId})`);
    } else {
      console.error('错误: 未找到根目录文件夹。请通过 --folder-id 指定目标文件夹');
      process.exit(1);
    }
  }

  return { spaceId, folderId };
}

export function parseArgs(argv) {
  const args = argv.slice(2);
  const result = { _: [] };
  for (let i = 0; i < args.length; i++) {
    if (args[i].startsWith('--')) {
      const key = args[i].slice(2);
      const next = args[i + 1];
      if (next && !next.startsWith('--')) {
        result[key] = next;
        i++;
      } else {
        result[key] = true;
      }
    } else {
      result._.push(args[i]);
    }
  }
  return result;
}

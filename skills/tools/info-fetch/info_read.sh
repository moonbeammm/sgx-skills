#!/bin/bash
#
# info 页面读取脚本
#
# 用法:
#   ./info_read.sh <pageId> [raw|markdown]
#
# 示例:
#   ./info_read.sh 855215107           # 获取 Markdown 格式
#   ./info_read.sh 855215107 raw       # 获取原始 JSON
#   ./info_read.sh 855215107 markdown  # 获取 Markdown 格式

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOKEN_FILE="${SCRIPT_DIR}/../../settings/info-token.txt"

if [ -z "$INFO_TOKEN" ]; then
    if [ ! -f "$TOKEN_FILE" ]; then
        echo "错误: INFO_TOKEN 环境变量未设置，且 Token 文件不存在: $TOKEN_FILE"
        echo "请设置 INFO_TOKEN 环境变量或创建文件并写入 Info Token"
        exit 1
    fi
    export INFO_TOKEN=$(cat "$TOKEN_FILE")
fi

if [ -z "$1" ]; then
    echo "用法: $0 <pageId> [raw|markdown]"
    exit 1
fi

PAGE_ID="$1"
FORMAT="${2:-markdown}"

if [ ! -f "$TOKEN_FILE" ]; then
    echo "错误: Token 文件不存在: $TOKEN_FILE"
    echo "请创建文件并写入 Info Token"
    exit 1
fi

TOKEN=$(cat "$TOKEN_FILE")

case "$FORMAT" in
    raw)
        curl -s -H "Authorization: Bearer $TOKEN" \
            "https://info.bilibili.co/rest/api/content/${PAGE_ID}?expand=body.storage,title,space,version"
        ;;
    markdown)
        curl -s -H "Authorization: Bearer $TOKEN" \
            "https://info.bilibili.co/rest/api/content/${PAGE_ID}?expand=body.storage,title" | \
            python3 "${SCRIPT_DIR}/info_to_markdown.py"
        ;;
    *)
        echo "错误: 未知格式 '$FORMAT'，支持 'raw' 或 'markdown'"
        exit 1
        ;;
esac
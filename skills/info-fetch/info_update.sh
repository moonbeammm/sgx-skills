#!/bin/bash
#
# Info 页面更新脚本
#
# 用法:
#   ./info_update.sh <pageId> <title> <content_file>
#
# 示例:
#   ./info_update.sh 855215107 "新标题" content.html
#
# content_file 应该包含 Info storage 格式的 HTML 内容

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOKEN_FILE="${SCRIPT_DIR}/../../settings/info-token.txt"

if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then
    echo "用法: $0 <pageId> <title> <content_file>"
    exit 1
fi

PAGE_ID="$1"
TITLE="$2"
CONTENT_FILE="$3"

if [ ! -f "$TOKEN_FILE" ]; then
    echo "错误: Token 文件不存在: $TOKEN_FILE"
    exit 1
fi

if [ ! -f "$CONTENT_FILE" ]; then
    echo "错误: 内容文件不存在: $CONTENT_FILE"
    exit 1
fi

TOKEN=$(cat "$TOKEN_FILE")

# 获取当前版本号
VERSION=$(curl -s -H "Authorization: Bearer $TOKEN" \
    "https://info.bilibili.co/rest/api/content/${PAGE_ID}?expand=version" | \
    python3 -c "import sys,json; print(json.load(sys.stdin)['version']['number'])")

NEW_VERSION=$((VERSION + 1))

# 读取内容并转义 JSON
CONTENT=$(cat "$CONTENT_FILE" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')

# 更新页面
curl -s -X PUT \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    "https://info.bilibili.co/rest/api/content/${PAGE_ID}" \
    -d "{
        \"id\": \"${PAGE_ID}\",
        \"type\": \"page\",
        \"title\": \"${TITLE}\",
        \"version\": {
            \"number\": ${NEW_VERSION}
        },
        \"body\": {
            \"storage\": {
                \"value\": ${CONTENT},
                \"representation\": \"storage\"
            }
        }
    }"

echo ""
echo "页面已更新: https://info.bilibili.co/pages/viewpage.action?pageId=${PAGE_ID}"

#!/bin/bash
#
# info 页面创建脚本
#
# 用法:
#   ./info_create.sh <space_key> <title> <content_file> [parent_id]
#
# 示例:
#   ./info_create.sh OTT "新页面标题" content.html
#   ./info_create.sh OTT "新页面标题" content.html 855215107
#
# content_file 应该包含 info storage 格式的 HTML 内容

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOKEN_FILE="${SCRIPT_DIR}/../../settings/info-token.txt"

if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then
    echo "用法: $0 <space_key> <title> <content_file> [parent_id]"
    exit 1
fi

SPACE_KEY="$1"
TITLE="$2"
CONTENT_FILE="$3"
PARENT_ID="$4"

if [ ! -f "$TOKEN_FILE" ]; then
    echo "错误: Token 文件不存在: $TOKEN_FILE"
    exit 1
fi

if [ ! -f "$CONTENT_FILE" ]; then
    echo "错误: 内容文件不存在: $CONTENT_FILE"
    exit 1
fi

TOKEN=$(cat "$TOKEN_FILE")

# 读取内容并转义 JSON
CONTENT=$(cat "$CONTENT_FILE" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')

# 构建 ancestors 部分
ANCESTORS=""
if [ -n "$PARENT_ID" ]; then
    ANCESTORS="\"ancestors\": [{\"id\": \"${PARENT_ID}\"}],"
fi

# 创建页面
RESULT=$(curl -s -X POST \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    "https://info.bilibili.co/rest/api/content" \
    -d "{
        \"type\": \"page\",
        \"title\": \"${TITLE}\",
        \"space\": {
            \"key\": \"${SPACE_KEY}\"
        },
        ${ANCESTORS}
        \"body\": {
            \"storage\": {
                \"value\": ${CONTENT},
                \"representation\": \"storage\"
            }
        }
    }")

# 解析并显示结果
PAGE_ID=$(echo "$RESULT" | python3 -c "import sys,json; data=json.load(sys.stdin); print(data.get('id', 'ERROR'))" 2>/dev/null || echo "ERROR")

if [ "$PAGE_ID" = "ERROR" ]; then
    echo "创建失败:"
    echo "$RESULT" | python3 -m json.tool 2>/dev/null || echo "$RESULT"
    exit 1
fi

echo "页面创建成功!"
echo "Page ID: $PAGE_ID"
echo "URL: https://info.bilibili.co/pages/viewpage.action?pageId=${PAGE_ID}"

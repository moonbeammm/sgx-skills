#!/usr/bin/env python3
"""
Info HTML to Markdown 转换脚本

用法:
    curl -s -H "Authorization: Bearer $TOKEN" \
      "https://info.bilibili.co/rest/api/content/{pageId}?expand=body.storage,title" | \
      python3 info_to_markdown.py
"""

import sys
import json
import html
import re


def convert_to_markdown(data):
    """将 Info API 响应转换为 Markdown"""
    title = data.get('title', 'Unknown')
    content = data.get('body', {}).get('storage', {}).get('value', '')

    # 清理 HTML
    content = re.sub(r'<ac:structured-macro[^>]*>.*?</ac:structured-macro>', '', content, flags=re.DOTALL)
    content = re.sub(r'<span[^>]*>', '', content)
    content = re.sub(r'</span>', '', content)
    content = re.sub(r'<p[^>]*>', '\n', content)
    content = re.sub(r'</p>', '', content)
    content = re.sub(r'<br\s*/?>', '\n', content)
    content = re.sub(r'<h([1-6])[^>]*>', lambda m: '\n' + '#' * int(m.group(1)) + ' ', content)
    content = re.sub(r'</h[1-6]>', '\n', content)
    content = re.sub(r'<strong>', '**', content)
    content = re.sub(r'</strong>', '**', content)
    content = re.sub(r'<pre[^>]*>', '\n```\n', content)
    content = re.sub(r'</pre>', '\n```\n', content)
    content = re.sub(r'<code[^>]*>', '`', content)
    content = re.sub(r'</code>', '`', content)
    content = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>', r'[\2](\1)', content)
    content = re.sub(r'<li[^>]*>', '\n- ', content)
    content = re.sub(r'</li>', '', content)
    content = re.sub(r'<[^>]+>', '', content)
    content = html.unescape(content)
    content = re.sub(r'\n{3,}', '\n\n', content)

    print(f'# {title}\n')
    print(content.strip())


if __name__ == '__main__':
    data = json.load(sys.stdin)
    convert_to_markdown(data)

# -*- coding: utf-8 -*-
"""修复索引中的双重编码（mojibake）：UTF-8 字节被当作 Latin-1 读入后变成乱码字符。
修复方法：尝试 latin-1 -> utf-8 还原，能成功且结果不同的字段就替换。"""
import json, base64, urllib.request, urllib.parse, time

TOKEN = 'YOUR_GH_TOKEN_HERE'
REPO = 'Tystarry/aty-tools'
HDRS = {'Authorization': 'Bearer ' + TOKEN, 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}


def repair(s):
    if not isinstance(s, str):
        return s
    try:
        fixed = s.encode('latin-1').decode('utf-8')
        return fixed if fixed != s else s
    except Exception:
        return s


# 经 API 读索引（内容为 base64，避免 raw CDN 缓存）
enc = urllib.parse.quote('assets_index.json', safe='')
req = urllib.request.Request('https://api.github.com/repos/%s/contents/%s' % (REPO, enc), headers=HDRS)
with urllib.request.urlopen(req, timeout=30) as r:
    meta = json.loads(r.read())
idx = json.loads(base64.b64decode(meta['content']).decode('utf-8'))

fixed_count = 0
for a in idx.get('assets', []):
    for key in ('name', 'thumbnail', 'subcat', 'category', 'source', 'description'):
        if key in a:
            old = a[key]
            new = repair(old)
            if new != old:
                a[key] = new
                fixed_count += 1
    a['downloads'] = [repair(d) for d in (a.get('downloads') or [])]
    a['files'] = [repair(f) for f in (a.get('files') or [])]

print('fixed fields:', fixed_count)
idx['updated'] = time.strftime('%Y-%m-%dT%H:%M:%S')

content = base64.b64encode(json.dumps(idx, ensure_ascii=False).encode('utf-8')).decode('ascii')
req = urllib.request.Request(
    'https://api.github.com/repos/%s/contents/%s' % (REPO, enc),
    data=json.dumps({'message': 'Repair mojibake paths', 'content': content, 'sha': meta.get('sha', '')}).encode('utf-8'),
    method='PUT', headers=dict(HDRS, **{'Content-Type': 'application/json'})
)
with urllib.request.urlopen(req, timeout=30) as r:
    json.loads(r.read())
print('index repaired')

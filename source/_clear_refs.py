# -*- coding: utf-8 -*-
"""清空网站上的参考图素材：删除 GitHub 上的参考图文件 + 从索引中移除参考图条目"""
import json, urllib.request, urllib.parse

TOKEN = 'YOUR_GH_TOKEN_HERE'
REPO = 'Tystarry/aty-tools'
HDRS = {'Authorization': f'Bearer {TOKEN}', 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}

# 1. 删除旧参考图文件
PATHS = [
    'assets/参考图/OIP_C.zip',
    'assets/参考图/OIP_C.png',
    'assets/参考图/main_参考图.zip',
]
for p in PATHS:
    enc = urllib.parse.quote(p, safe='')
    try:
        req = urllib.request.Request(f'https://api.github.com/repos/{REPO}/contents/{enc}', headers=HDRS)
        with urllib.request.urlopen(req) as r:
            sha = json.loads(r.read()).get('sha', '')
        if not sha:
            print(f'NOT FOUND: {p}')
            continue
        req = urllib.request.Request(
            f'https://api.github.com/repos/{REPO}/contents/{enc}',
            data=json.dumps({'message': f'Remove {p}', 'sha': sha}).encode('utf-8'), method='DELETE',
            headers=dict(HDRS, **{'Content-Type': 'application/json'})
        )
        with urllib.request.urlopen(req) as r:
            json.loads(r.read())
        print(f'DELETED: {p}')
    except Exception as e:
        print(f'FAIL: {p}: {e}')

# 2. 索引中移除参考图条目
try:
    with urllib.request.urlopen(
        'https://raw.githubusercontent.com/Tystarry/aty-tools/main/assets_index.json?t=clear', timeout=15
    ) as r:
        idx = json.loads(r.read())
    before = len(idx.get('assets', []))
    idx['assets'] = [a for a in idx.get('assets', []) if a.get('category') != '参考图' and a.get('kind') != 'ref']
    after = len(idx['assets'])
    if before != after:
        import base64
        enc = urllib.parse.quote('assets_index.json', safe='')
        req = urllib.request.Request(f'https://api.github.com/repos/{REPO}/contents/{enc}', headers=HDRS)
        with urllib.request.urlopen(req) as r:
            sha = json.loads(r.read()).get('sha', '')
        content = base64.b64encode(json.dumps(idx, ensure_ascii=False).encode('utf-8')).decode('ascii')
        req = urllib.request.Request(
            f'https://api.github.com/repos/{REPO}/contents/{enc}',
            data=json.dumps({'message': 'Clear refs from index', 'content': content, 'sha': sha}).encode('utf-8'),
            method='PUT', headers=dict(HDRS, **{'Content-Type': 'application/json'})
        )
        with urllib.request.urlopen(req) as r:
            json.loads(r.read())
        print(f'INDEX updated: {before} -> {after} entries (removed {before - after} refs)')
    else:
        print(f'INDEX: no ref entries ({before} total)')
except Exception as e:
    print(f'INDEX FAIL: {e}')

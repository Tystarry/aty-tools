# -*- coding: utf-8 -*-
"""把所有参考图文件统一改名为 img_NNNN.ext（纯字母+数字，最不易出错），并更新索引"""
import json, base64, time, urllib.parse, urllib.request

urllib.request.install_opener(urllib.request.build_opener(urllib.request.ProxyHandler({})))

TOKEN = 'YOUR_GH_TOKEN_HERE'
REPO = 'Tystarry/aty-tools'
HDRS = {'Authorization': 'Bearer ' + TOKEN, 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}


def api(method, path, body=None):
    enc = urllib.parse.quote(path, safe='')
    req = urllib.request.Request(
        'https://api.github.com/repos/%s/contents/%s' % (REPO, enc),
        data=json.dumps(body).encode('utf-8') if body else None, method=method,
        headers=dict(HDRS, **({'Content-Type': 'application/json'} if body else {}))
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


# 列出所有 refs 图片文件（排除目录条目）
req = urllib.request.Request('https://api.github.com/repos/%s/git/trees/main?recursive=1' % REPO, headers=HDRS)
with urllib.request.urlopen(req, timeout=60) as r:
    tree = json.loads(r.read()).get('tree', [])
files = sorted(t['path'] for t in tree if t['path'].startswith('assets/refs/') and not t['path'].endswith('/') and t.get('type') == 'blob')
print('files:', len(files))

import re
existing = []
for p in files:
    m = re.search(r'img_(\d{4})\.', p)
    if m:
        existing.append(int(m.group(1)))
next_i = (max(existing) + 1) if existing else 1

renamed = {}
for p in files:
    if re.search(r'img_\d{4}\.', p):
        continue  # 已经是安全名
    ext = p.rsplit('.', 1)[-1].lower()
    new_p = '/'.join(p.split('/')[:-1] + ['img_%04d.%s' % (next_i, ext)])
    next_i += 1
    if new_p == p:
        continue
    meta = api('GET', p)
    content = meta.get('content', '')
    if not content:
        # 大文件（>1MB）API 不带 content，改从 raw 下载再转 base64
        try:
            url = 'https://raw.githubusercontent.com/%s/main/' % REPO + urllib.parse.quote(p, safe='/')
            with urllib.request.urlopen(url, timeout=120) as r:
                content = base64.b64encode(r.read()).decode('ascii')
            print('  (downloaded via raw)')
        except Exception as e:
            print('NO CONTENT, raw failed:', p, str(e)[:80])
            continue
    api('PUT', new_p, {'message': 'Rename to safe name', 'content': content})
    api('DELETE', p, {'message': 'Rename to safe name', 'sha': meta.get('sha', '')})
    renamed[p] = new_p
    print('RENAMED:', p, '->', new_p)

if renamed:
    idx_meta = api('GET', 'assets_index.json')
    idx = json.loads(base64.b64decode(idx_meta['content']).decode('utf-8'))
    for a in idx['assets']:
        if a.get('thumbnail') in renamed:
            a['thumbnail'] = renamed[a['thumbnail']]
        a['downloads'] = [renamed.get(d, d) for d in (a.get('downloads') or [])]
        if a.get('thumbnail') and a.get('thumbnail').startswith('assets/refs/'):
            fname = a['thumbnail'].rsplit('/', 1)[-1]
            a['files'] = [fname]
            a['name'] = fname.rsplit('.', 1)[0]
    idx['updated'] = time.strftime('%Y-%m-%dT%H:%M:%S')
    api('PUT', 'assets_index.json', {
        'message': 'Update index after safe rename',
        'content': base64.b64encode(json.dumps(idx, ensure_ascii=False).encode('utf-8')).decode('ascii'),
        'sha': idx_meta.get('sha', ''),
    })
    print('index updated')

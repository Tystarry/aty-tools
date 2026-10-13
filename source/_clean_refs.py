# -*- coding: utf-8 -*-
"""清理参考图坏条目：缩略图指向目录的垃圾条目 + 下划线开头无法在 Pages 显示的残留文件"""
import json, base64, urllib.parse, urllib.request, time

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


# 删除下划线开头的残留文件
for p in ['assets/refs/摄影/__(5).png']:
    try:
        meta = api('GET', p)
        api('DELETE', p, {'message': 'Remove leftover', 'sha': meta.get('sha', '')})
        print('DELETED', p)
    except Exception as e:
        print('DEL FAIL', p, str(e)[:80])

# 清理索引：去掉缩略图指向目录的条目 + 下划线开头文件的条目
meta = api('GET', 'assets_index.json')
idx = json.loads(base64.b64decode(meta['content']).decode('utf-8'))
before = len(idx['assets'])
idx['assets'] = [a for a in idx['assets'] if not (
    (a.get('kind') == 'ref' and (a.get('thumbnail') or '').endswith('/')) or
    '/' + (a.get('files') or [''])[0] in ['/' + p.split('/')[-1] for p in ['assets/refs/摄影/__(5).png']] or
    '__' in (a.get('name') or '')
)]
idx['updated'] = time.strftime('%Y-%m-%dT%H:%M:%S')
api('PUT', 'assets_index.json', {
    'message': 'Clean broken ref entries',
    'content': base64.b64encode(json.dumps(idx, ensure_ascii=False).encode('utf-8')).decode('ascii'),
    'sha': meta.get('sha', ''),
})
print('index entries:', before, '->', len(idx['assets']))

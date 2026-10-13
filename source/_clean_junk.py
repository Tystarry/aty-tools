# -*- coding: utf-8 -*-
"""清理索引中缩略图不是图片文件的参考图垃圾条目"""
import json, base64, urllib.parse, urllib.request, time

TOKEN = 'YOUR_GH_TOKEN_HERE'
REPO = 'Tystarry/aty-tools'
HDRS = {'Authorization': 'Bearer ' + TOKEN, 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
IMG_EXT = ('png', 'jpg', 'jpeg', 'webp', 'gif', 'bmp')


def api(method, path, body=None):
    enc = urllib.parse.quote(path, safe='')
    req = urllib.request.Request(
        'https://api.github.com/repos/%s/contents/%s' % (REPO, enc),
        data=json.dumps(body).encode('utf-8') if body else None, method=method,
        headers=dict(HDRS, **({'Content-Type': 'application/json'} if body else {}))
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


meta = api('GET', 'assets_index.json')
idx = json.loads(base64.b64decode(meta['content']).decode('utf-8'))
before = len(idx['assets'])
idx['assets'] = [a for a in idx['assets'] if not (
    a.get('kind') == 'ref' and
    (a.get('thumbnail') or '').rsplit('.', 1)[-1].lower() not in IMG_EXT
)]
idx['updated'] = time.strftime('%Y-%m-%dT%H:%M:%S')
api('PUT', 'assets_index.json', {
    'message': 'Clean junk ref entry',
    'content': base64.b64encode(json.dumps(idx, ensure_ascii=False).encode('utf-8')).decode('ascii'),
    'sha': meta.get('sha', ''),
})
print('entries:', before, '->', len(idx['assets']))
for a in idx['assets']:
    if a.get('kind') == 'ref':
        print('ref:', a.get('name'), '|', a.get('thumbnail'))

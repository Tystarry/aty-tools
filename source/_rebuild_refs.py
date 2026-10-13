# -*- coding: utf-8 -*-
"""根据仓库实际文件重建参考图索引条目（上传竞态导致条目丢失/路径过期）"""
import json, base64, time, urllib.parse, urllib.request

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


# 仓库里所有 refs 文件
req = urllib.request.Request('https://api.github.com/repos/%s/git/trees/main?recursive=1' % REPO, headers=HDRS)
with urllib.request.urlopen(req, timeout=60) as r:
    tree = json.loads(r.read()).get('tree', [])
ref_files = sorted(
    t['path'] for t in tree
    if t['path'].startswith('assets/refs/') and not t['path'].endswith('/')
)
print('ref files:', len(ref_files))

# 取现有索引（保留素材部分），重建 refs 部分
with urllib.request.urlopen(
    'https://raw.githubusercontent.com/%s/main/assets_index.json?t=%d' % (REPO, int(time.time())), timeout=30
) as r:
    idx = json.loads(r.read())
old_refs = [a for a in idx.get('assets', []) if a.get('kind') == 'ref']
# 旧条目里的标签尽量保留（按 name 匹配）
old_by_name = {}
for a in old_refs:
    old_by_name.setdefault(a.get('name'), a)
idx['assets'] = [a for a in idx.get('assets', []) if a.get('kind') != 'ref']

new_entries = []
for p in ref_files:
    segs = p.split('/')
    subcat = segs[2]
    fname = segs[-1]
    stem = fname.rsplit('.', 1)[0]
    old = old_by_name.get(stem) or {}
    new_entries.append({
        'kind': 'ref', 'category': '参考图', 'subcat': subcat,
        'name': stem,
        'description': old.get('description', ''),
        'thumbnail': p, 'downloads': [p],
        'files': [fname], 'size': 0, 'date': time.strftime('%Y-%m-%d'),
        'tags': old.get('tags', {}), 'source': old.get('source', ''),
    })
idx['assets'] = new_entries + idx['assets']
idx['updated'] = time.strftime('%Y-%m-%dT%H:%M:%S')

meta = api('GET', 'assets_index.json')
api('PUT', 'assets_index.json', {
    'message': 'Rebuild ref entries',
    'content': base64.b64encode(json.dumps(idx, ensure_ascii=False).encode('utf-8')).decode('ascii'),
    'sha': meta.get('sha', ''),
})
print('rebuilt', len(new_entries), 'ref entries')
